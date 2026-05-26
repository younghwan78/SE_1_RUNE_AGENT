"""Smoke check for the optional local SoC embedding model."""

import argparse
import json
from typing import Any

from req_tracker.config.settings import Settings
from req_tracker.vector.local_embedding import LocalSentenceTransformerEmbedder


def main() -> int:
    """CLI entrypoint."""
    args = _parse_args()
    settings = Settings()
    model_name = args.model_name or settings.soc_embedding_model_name
    expected_dimensions = args.expected_dimensions or settings.soc_embedding_dimensions
    if args.dry_run or not args.live:
        _emit(
            {
                "status": "skipped",
                "mode": "dry_run",
                "reason": "pass --live to load and score with the embedding model",
                "model_name": model_name,
                "expected_dimensions": expected_dimensions,
            },
            args.format,
        )
        return 0

    embedder = LocalSentenceTransformerEmbedder(
        model_name=model_name,
        expected_dimensions=expected_dimensions,
    )
    try:
        vector = embedder.warmup()
    except Exception as exc:
        _emit(
            {
                "status": "failed",
                "mode": "live",
                "model_name": model_name,
                "expected_dimensions": expected_dimensions,
                "error": str(exc),
            },
            args.format,
        )
        return 1
    status = "passed" if len(vector) == expected_dimensions else "failed"
    _emit(
        {
            "status": status,
            "mode": "live",
            "model_name": model_name,
            "expected_dimensions": expected_dimensions,
            "dimensions": len(vector),
        },
        args.format,
    )
    return 0 if status == "passed" else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Do not load the model.")
    parser.add_argument("--live", action="store_true", help="Load and score with the model.")
    parser.add_argument("--model-name", default="", help="Override the embedding model name.")
    parser.add_argument(
        "--expected-dimensions",
        type=int,
        default=0,
        help="Override the expected embedding size.",
    )
    parser.add_argument("--format", choices=["json", "text"], default="text")
    return parser.parse_args()


def _emit(payload: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    raise SystemExit(main())
