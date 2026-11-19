"""Check whether a fix worked, from a BEFORE and an AFTER screenshot.

Usage: python run_verify.py before.png after.png --issue horizontal_overflow
           [--element "wide banner"] [--viewport mobile] [--metrics-fixed yes|no]
           [--provider ollama] [--timeout 120]

The model's answer is one signal. Pass --metrics-fixed yes|no from a metrics rescan
(for example scroll_width no longer exceeds the viewport) to get the final verdict.
Without it, a model-only "fixed" is reported as inconclusive.
"""
import argparse
from pathlib import Path

from vision.factory import get_provider
from vision.patches import ISSUE_TYPES, combine_verdicts, verify_fix


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--issue", required=True, choices=ISSUE_TYPES)
    ap.add_argument("--element", default="")
    ap.add_argument("--viewport", default="")
    ap.add_argument("--metrics-fixed", choices=("yes", "no"), default=None)
    ap.add_argument("--provider", default=None)
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args()

    res = verify_fix(get_provider(args.provider), Path(args.before).read_bytes(),
                     Path(args.after).read_bytes(), issue_type=args.issue,
                     element=args.element, viewport=args.viewport, timeout=args.timeout)
    print(f"outcome={res.outcome} model_verdict={res.verdict} confidence={res.confidence:.2f}"
          + (f" error={res.error}" if res.error else ""))
    if res.outcome != "ok":
        return
    print(f"evidence: {res.evidence}")
    print(f"new problems: {res.new_problems}")
    metrics = None if args.metrics_fixed is None else args.metrics_fixed == "yes"
    final, reason = combine_verdicts(res.verdict, metrics, res.new_problems)
    print(f"FINAL: {final} ({reason})")


if __name__ == "__main__":
    main()
