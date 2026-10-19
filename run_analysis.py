"""Usage: python run_analysis.py path/to/scan_result.json [--provider ollama] [--timeout 180] [--out analysis.json]"""
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
    args = ap.parse_args()
    result = analyze_scan(get_provider(args.provider), args.scan_json, args.out, args.timeout)
    for a in result["analyses"]:
        print(f"{a['viewport']:8} outcome={a['outcome']:15} findings={len(a['findings'])}"
              + (f" error={a['error']}" if a["error"] else ""))


if __name__ == "__main__":
    main()
