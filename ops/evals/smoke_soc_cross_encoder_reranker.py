"""Smoke check for the optional local SoC cross-encoder reranker."""

import argparse
import json
from typing import Any

from req_tracker.config.settings import Settings
from req_tracker.query.reranking import CrossEncoderSocReranker


def main() -> int:
    """CLI entrypoint."""
    args = _parse_args()
    settings = Settings()
    model_name = args.model_name or settings.soc_cross_encoder_model_name
    if args.dry_run or not args.live:
        _emit(
            {
                "status": "skipped",
                "mode": "dry_run",
                "reason": "pass --live to load and score with the cross-encoder",
                "model_name": model_name,
            },
            args.format,
        )
        return 0

    reranker = CrossEncoderSocReranker(model_name=model_name)
    try:
        scores = reranker.warmup()
    except Exception as exc:
        _emit(
            {
                "status": "failed",
                "mode": "live",
                "model_name": model_name,
                "error": str(exc),
            },
            args.format,
        )
        return 1
    _emit(
        {
            "status": "passed" if scores else "failed",
            "mode": "live",
            "model_name": model_name,
            "score_count": len(scores),
            "scores": scores,
        },
        args.format,
    )
    return 0 if scores else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Do not load the model.")
    parser.add_argument("--live", action="store_true", help="Load and score with the model.")
    parser.add_argument("--model-name", default="", help="Override the reranker model name.")
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
