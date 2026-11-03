# Week 3: patch suggestions and fix verification (Member 3)

Status: built and unit-tested with fake providers. **Not yet run on a real model.**

## Patch suggestions (`vision/patches.py`, `run_patches.py`)
For each finding marked `detected`, the model is shown the screenshot and the problem and asked for the
smallest CSS change. The reply is JSON, validated field by field:

```json
{"patches": [{"selector": ".banner", "css_before": "width: 1200px",
              "css_after": "max-width: 100%; overflow-x: auto",
              "rationale": "The banner is wider than the screen, so limit its width.",
              "confidence": 0.9}],
 "cannot_determine": false}
```

Each accepted patch becomes a `PatchSuggestion` with `scan_id`, `viewport`, `issue_type`, `element`,
`file_path`, `selector`, `css_before`, `css_after`, `rationale`, `confidence`.

Safety rules (all enforced in code and covered by tests):
- Nothing the model writes is executed or applied. Output is data for a human-approved step.
- `file_path` is **not** chosen by the model. It comes from the scan (`source_file`) or `--source-file`,
  must be relative, contain no `..`, and end in `.css`, `.html` or `.htm`.
- `css_after` must be plain `property: value` declarations. Braces, `<`, backslashes, comments,
  `url(`, `@import`, `expression(` and `javascript:` are rejected. Selectors have similar limits.
- A rejected patch is dropped and recorded in `rejected` with the reason. At most 2 patches are kept.
- A reply with the wrong shape is `invalid_output` and is retried once.
- Page text and HTML are treated as untrusted in the prompt.

For Member 2: `file_path` can be `null` when no source file is known. The patch applier must refuse
those and must apply only to a local copy.

## Fix verification (`verify_fix`, `combine_verdicts`, `run_verify.py`)
BEFORE and AFTER screenshots are joined side by side into one image (the provider interface takes one
image) and the model says `fixed`, `not_fixed` or `inconclusive`, plus any new problem it sees.

The model's answer is one signal. `combine_verdicts` gives the final verdict:
- `fixed` only when the model **and** a metrics rescan (Member 4/Member 2) both say fixed
- `not_fixed` when a signal shows the problem remains and none says fixed
- everything else, including a model-only "fixed", is `inconclusive`

## Limitations
- Not tested on a real model yet. Expect the same run-to-run variation seen in the Week 2 audit.
- The model cannot see source code, so selectors are guesses from the screenshot (and the HTML snippet
  if `relevant_html` is supplied). A suggested selector may not match the real page.
- Suggestions are not checked by applying them. Applying and re-scanning is Member 2's step.
