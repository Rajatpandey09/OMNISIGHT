import json

SYSTEM_PROMPT = """You are a visual QA assistant reviewing a web page screenshot.
Rules:
- Ground every finding in what is visible in the screenshot or in the metrics given.
- If you cannot determine whether a defect exists, set cannot_determine=true
  or give status "inconclusive" with low confidence. Do not guess.
- bbox is optional: an approximate region as fractions (0-1) of the screenshot; omit it if unsure.
- Be cautious: suggest the smallest CSS change; never output code to execute.
- Reply with ONLY a JSON object matching this shape:
{"findings":[{"issue_type":"horizontal_overflow|offscreen_button|overlapping_text|hidden_control|low_contrast|other",
"element":"selector or description","severity":"low|medium|high",
"evidence":"what you see/measure","impact":"effect on user",
"confidence":0.0-1.0,"status":"detected|inconclusive","suggested_fix":"cautious CSS idea",
"summary":"one plain-language sentence a non-technical person can read",
"bbox":{"x":0.0,"y":0.0,"width":0.0,"height":0.0}}],
"cannot_determine":false,"notes":"optional"}"""


def build_user_prompt(viewport: str, width: int, height: int, metrics: dict) -> str:
    # Only pass compact, relevant metrics; no source code.
    keep = {k: metrics[k] for k in
            ("scroll_width", "scroll_height", "buttons", "hidden_controls")
            if k in metrics}
    return (f"Viewport: {viewport} ({width}x{height}).\n"
            f"Metrics: {json.dumps(keep)}\nAnalyze the screenshot.")
