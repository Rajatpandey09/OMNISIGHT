# Prompt design notes (Week 1)

Prompts live in vision/prompts.py. Design rules taken from the work guide:

1. Evidence first: every finding must cite what is visible or measured.
2. Name the viewport and element/location for each finding.
3. Explicit uncertainty: model may set cannot_determine=true or status "inconclusive".
4. Cautious fix: smallest CSS change; never code to execute.
5. Strict JSON only, validated against vision/schema.py before use.
6. Compact input: screenshot + viewport size + only scroll_width, scroll_height,
   buttons, hidden_controls (no unrelated source code).

## Open questions for teammates
- Member 2: final metrics JSON key names and shape of `buttons`.
- Member 4: exact bug page names and expected signals for eval/labelled_cases.json.
- Member 1: do you want `bbox` and `summary` in the issue cards?

## Prompt revision log
| Version | Change | Result on labelled cases |
|---|---|---|
| v1 | Initial system prompt | not yet tested |
| v2 | Page text and HTML treated as untrusted; optional cleaned HTML; screenshot-only mode | not yet tested |
