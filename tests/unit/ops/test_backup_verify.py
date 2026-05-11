"""Backup-set verifier tests."""

import hashlib
import importlib.util
import tarfile
from pathlib import Path
from types import ModuleType


def test_verify_backup_set_accepts_complete_fixture(tmp_path) -> None:  # type: ignore[no-untyped-def]
    module = _load_module()
    backup_root = _make_backup_fixture(tmp_path)

    report = module.verify_backup_set(backup_root)

    assert report["passed"] is True
    assert report["summary"]["failed"] == 0
    checks = {check["check_id"]: check for check in report["checks"]}
    assert checks["required_files"]["status"] == "passed"
    assert checks["sha256sums"]["status"] == "passed"
    assert checks["artifact_tar"]["status"] == "passed"


def test_verify_backup_set_fails_missing_files(tmp_path) -> None:  # type: ignore[no-untyped-def]
    module = _load_module()
    backup_root = tmp_path / "backup"
    backup_root.mkdir()

    report = module.verify_backup_set(backup_root)

    assert report["passed"] is False
    checks = {check["check_id"]: check for check in report["checks"]}
    assert checks["required_files"]["status"] == "failed"
    assert checks["neo4j_dump"]["status"] == "failed"


def test_verify_backup_set_fails_hash_mismatch(tmp_path) -> None:  # type: ignore[no-untyped-def]
    module = _load_module()
    backup_root = _make_backup_fixture(tmp_path)
    (backup_root / "postgres.dump").write_text("changed", encoding="utf-8")

    report = module.verify_backup_set(backup_root)

    checks = {check["check_id"]: check for check in report["checks"]}
    assert checks["sha256sums"]["status"] == "failed"
    assert "hash_mismatch:postgres.dump" in checks["sha256sums"]["evidence"]


def _make_backup_fixture(tmp_path: Path) -> Path:
    backup_root = tmp_path / "backup"
    backup_root.mkdir()
    (backup_root / "postgres.dump").write_text("postgres", encoding="utf-8")
    (backup_root / "qdrant_snapshot.json").write_text('{"name":"snapshot"}', encoding="utf-8")
    (backup_root / "env.example").write_text("REQ_TRACKER_ENV=production\n", encoding="utf-8")
    (backup_root / "git_commit.txt").write_text("abcdef1234567890\n", encoding="utf-8")
    (backup_root / "neo4j.dump").write_text("neo4j", encoding="utf-8")
    artifact_file = tmp_path / "artifact.json"
    artifact_file.write_text('{"ok":true}', encoding="utf-8")
    with tarfile.open(backup_root / "artifacts.tar.gz", "w:gz") as archive:
        archive.add(artifact_file, arcname="artifacts/artifact.json")
    _write_sha256sums(backup_root)
    return backup_root


def _write_sha256sums(backup_root: Path) -> None:
    lines = []
    for path in sorted(item for item in backup_root.iterdir() if item.name != "SHA256SUMS"):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.name}")
    (backup_root / "SHA256SUMS").write_text("\n".join(lines), encoding="utf-8")


def _load_module() -> ModuleType:
    module_path = Path("ops/backup/verify_backup_set.py")
    spec = importlib.util.spec_from_file_location("verify_backup_set", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
