"""Usage: python run_analysis.py path/to/scan_result.json [--provider ollama] [--timeout 180] [--screenshot-only] [--out analysis.json]"""
import argparse
from vision.factory import get_provider
from vision.pipeline import analyze_scan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scan_json")
    ap.add_argument("--provider", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--timeout", type=float, default=30.0,
                    help="seconds per call; local models (ollama) often need 120-300")
    ap.add_argument("--screenshot-only", action="store_true",
                    help="send only the image (no metrics, no HTML): the vision audit mode")
    args = ap.parse_args()
    if args.screenshot_only and "heuristic" in (args.provider or ""):
        print("note: the heuristic provider reads metrics only, so it cannot work in screenshot-only mode")
    result = analyze_scan(get_provider(args.provider), args.scan_json, args.out,
                          args.timeout, args.screenshot_only)
    print(f"mode: {result['mode']}")
    for a in result["analyses"]:
        print(f"{a['viewport']:8} outcome={a['outcome']:15} findings={len(a['findings'])}"
              + (f" error={a['error']}" if a["error"] else ""))


if __name__ == "__main__":
    main()
