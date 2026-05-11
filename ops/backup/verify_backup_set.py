"""Verify the shape and checksums of a RUNE backup set.

This verifier is intentionally read-only. It validates that a backup directory
contains the expected production recovery artifacts before a restore rehearsal.
It prints filenames and hash status only, not DSNs, tokens, or file contents.
"""

import argparse
import hashlib
import json
import tarfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

CheckStatus = Literal["passed", "failed", "warning"]


@dataclass(frozen=True)
class BackupCheck:
    """One backup verification check."""

    check_id: str
    status: CheckStatus
    summary: str
    evidence: list[str]


REQUIRED_FILES = (
    "postgres.dump",
    "artifacts.tar.gz",
    "qdrant_snapshot.json",
    "env.example",
    "git_commit.txt",
    "SHA256SUMS",
)


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup-root", type=Path, required=True)
    args = parser.parse_args()
    report = verify_backup_set(args.backup_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


def verify_backup_set(backup_root: Path) -> dict[str, Any]:
    """Verify a backup directory and return a structured report."""
    checks = [
        _check_root(backup_root),
        _check_required_files(backup_root),
        _check_neo4j_dump(backup_root),
        _check_tar(backup_root / "artifacts.tar.gz"),
        _check_json(backup_root / "qdrant_snapshot.json"),
        _check_git_commit(backup_root / "git_commit.txt"),
        _check_sha256sums(backup_root),
    ]
    summary = _summary(checks)
    return {
        "passed": summary["failed"] == 0,
        "summary": summary,
        "checks": [asdict(check) for check in checks],
        "schema_version": "v1",
    }


def _check_root(backup_root: Path) -> BackupCheck:
    if backup_root.is_dir():
        return BackupCheck(
            check_id="backup_root",
            status="passed",
            summary="Backup root exists.",
            evidence=[backup_root.name],
        )
    return BackupCheck(
        check_id="backup_root",
        status="failed",
        summary="Backup root is missing or is not a directory.",
        evidence=[backup_root.name],
    )


def _check_required_files(backup_root: Path) -> BackupCheck:
    missing = [name for name in REQUIRED_FILES if not (backup_root / name).is_file()]
    if not missing:
        return BackupCheck(
            check_id="required_files",
            status="passed",
            summary="All required backup files are present.",
            evidence=list(REQUIRED_FILES),
        )
    return BackupCheck(
        check_id="required_files",
        status="failed",
        summary="Required backup files are missing.",
        evidence=[f"missing:{name}" for name in missing],
    )


def _check_neo4j_dump(backup_root: Path) -> BackupCheck:
    dump_files = sorted(
        path.name
        for path in backup_root.iterdir()
        if path.is_file() and path.suffix in {".dump", ".backup"} and "neo4j" in path.name
    ) if backup_root.is_dir() else []
    if dump_files:
        return BackupCheck(
            check_id="neo4j_dump",
            status="passed",
            summary="Neo4j dump file is present.",
            evidence=dump_files,
        )
    return BackupCheck(
        check_id="neo4j_dump",
        status="failed",
        summary="Neo4j dump file is missing.",
        evidence=["expected:*neo4j*.dump or *neo4j*.backup"],
    )


def _check_tar(path: Path) -> BackupCheck:
    if not path.is_file():
        return BackupCheck(
            check_id="artifact_tar",
            status="failed",
            summary="Artifact tarball is missing.",
            evidence=[path.name],
        )
    try:
        with tarfile.open(path, "r:gz") as archive:
            members = archive.getnames()
    except tarfile.TarError as exc:
        return BackupCheck(
            check_id="artifact_tar",
            status="failed",
            summary="Artifact tarball is not readable.",
            evidence=[exc.__class__.__name__],
        )
    if not members:
        return BackupCheck(
            check_id="artifact_tar",
            status="warning",
            summary="Artifact tarball is readable but empty.",
            evidence=[path.name],
        )
    return BackupCheck(
        check_id="artifact_tar",
        status="passed",
        summary="Artifact tarball is readable.",
        evidence=[f"members:{len(members)}"],
    )


def _check_json(path: Path) -> BackupCheck:
    if not path.is_file():
        return BackupCheck(
            check_id="qdrant_snapshot_json",
            status="failed",
            summary="Qdrant snapshot JSON is missing.",
            evidence=[path.name],
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return BackupCheck(
            check_id="qdrant_snapshot_json",
            status="failed",
            summary="Qdrant snapshot JSON is not readable.",
            evidence=[exc.__class__.__name__],
        )
    return BackupCheck(
        check_id="qdrant_snapshot_json",
        status="passed" if isinstance(payload, dict | list) else "warning",
        summary="Qdrant snapshot JSON is parseable.",
        evidence=[type(payload).__name__],
    )


def _check_git_commit(path: Path) -> BackupCheck:
    if not path.is_file():
        return BackupCheck(
            check_id="git_commit",
            status="failed",
            summary="Git commit marker is missing.",
            evidence=[path.name],
        )
    commit = path.read_text(encoding="utf-8").strip()
    if len(commit) >= 7 and all(char in "0123456789abcdef" for char in commit.lower()):
        return BackupCheck(
            check_id="git_commit",
            status="passed",
            summary="Git commit marker looks valid.",
            evidence=[f"length:{len(commit)}"],
        )
    return BackupCheck(
        check_id="git_commit",
        status="failed",
        summary="Git commit marker is not a hex commit id.",
        evidence=[f"length:{len(commit)}"],
    )


def _check_sha256sums(backup_root: Path) -> BackupCheck:
    manifest = backup_root / "SHA256SUMS"
    if not manifest.is_file():
        return BackupCheck(
            check_id="sha256sums",
            status="failed",
            summary="SHA256SUMS file is missing.",
            evidence=[manifest.name],
        )
    failures: list[str] = []
    checked: list[str] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        parsed = _parse_sha256_line(line)
        if parsed is None:
            continue
        expected_hash, filename = parsed
        target = backup_root / filename
        if not target.is_file():
            failures.append(f"missing:{filename}")
            continue
        actual_hash = _sha256_file(target)
        if actual_hash != expected_hash:
            failures.append(f"hash_mismatch:{filename}")
            continue
        checked.append(filename)
    if failures:
        return BackupCheck(
            check_id="sha256sums",
            status="failed",
            summary="One or more SHA256 entries failed verification.",
            evidence=failures,
        )
    if not checked:
        return BackupCheck(
            check_id="sha256sums",
            status="failed",
            summary="No SHA256 entries were verified.",
            evidence=["checked:0"],
        )
    return BackupCheck(
        check_id="sha256sums",
        status="passed",
        summary="SHA256 entries verified.",
        evidence=[f"checked:{len(checked)}"],
    )


def _parse_sha256_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped:
        return None
    parts = stripped.split(maxsplit=1)
    if len(parts) != 2:
        return None
    expected_hash = parts[0].lower()
    filename = parts[1].lstrip("*").strip()
    if len(expected_hash) != 64 or not all(char in "0123456789abcdef" for char in expected_hash):
        return None
    return expected_hash, Path(filename).name


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _summary(checks: list[BackupCheck]) -> dict[str, int]:
    summary = {"passed": 0, "failed": 0, "warning": 0}
    for check in checks:
        summary[check.status] += 1
    return summary


if __name__ == "__main__":
    raise SystemExit(main())
