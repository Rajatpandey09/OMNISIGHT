# Week 4: close-up check and evaluation (Member 3)

## What was added
- `vision/crop.py`: crops a screenshot to the area where a finding says the problem is, enlarges small
  crops so text stays readable, and asks the model whether the problem is visible in the close-up
  (`second_look`). `run_crop.py` runs it over `analysis.json`; `--check` adds the model call.
- `eval/summarize_runs.py`: turns repeated audit runs (`run_1.json`, `run_2.json`, ...) into one table of
  counts, so results are reported the same way every time.
- 21 unit tests (`tests/test_crop.py`, `tests/test_summarize_runs.py`) using fake providers.

## How the close-up works
1. A finding may carry a `bbox`: x, y, width and height as fractions (0 to 1) of the screenshot.
2. If the scanner gives a measured box (page pixels), `box_from_page_pixels` converts it and it is used
   instead of the model's estimate. A measurement beats a guess.
3. The crop adds a 4% margin, is at least 200 px on each side where the image allows, and is enlarged
   (up to 3x) when under 600 px so small text is readable.
4. No usable region, or a region covering almost the whole image: no crop is made and the finding keeps its
   single full-image look. Nothing is guessed.
5. The model sees only the crop and the reported problem, and answers `confirmed`, `not_confirmed` or
   `inconclusive`.
6. Labels: `confirmed` (close-up shows it), `needs_review` (close-up does not show it, so a human decides;
   the finding is never dropped), `single_look` (no usable close-up, or it could not tell).

Nothing the model writes is executed.

## Evaluation results (screenshot-only audit)
Setup: nine synthetic pages (five with a seeded bug, four clean), image only, gemma4:31b-cloud, prompt v4,
one automatic retry on a malformed reply, three runs. Regenerate with
`python eval/summarize_runs.py eval/results`.

| Case | Expected | Found in |
|---|---|---|
| overflow_mobile | horizontal overflow | 3/3 runs |
| offscreen_button_mobile | off-screen button | 3/3 runs |
| overlap_text_mobile | overlapping text | 3/3 runs |
| low_contrast_desktop | low contrast | 3/3 runs |
| hidden_control_mobile | hidden control | 0/3 runs |
| overflow_desktop, offscreen_button_desktop, clean_mobile, clean_desktop | no defect | no false alarms in any run |

Each run: 4 true positives, 0 false positives, 1 false negative, 0 inconclusive, 0 failed cases.

## Limitations
- The nine pages are drawn mock-ups, not real browser captures. Results on real pages may differ.
- Small set, three runs: these are counts, not accuracy.
- The prompt rules were written after seeing these same pages fail, so the results are on tuned cases.
  Unseen pages have not been tested.
- The hidden control is missed every time because a control that is not drawn is not in the screenshot. It
  needs the scanner's metrics.
- The close-up check and the patch/verification work are unit-tested with fake providers only. They have not
  been run on the real model yet.
- The model runs in Ollama's cloud, so screenshots leave the laptop.


## Real-model runs (added after the first runs)
Setup: a small scan of two synthetic pages (a low-contrast desktop page and an overflow mobile page), plus
the clean mobile and desktop pages as controls, gemma4:31b-cloud. These runs supersede the limitation above
for patch suggestions and the close-up check. The before/after verification and the self-healing loop have
still not been run on the real model.

- Analysis: both viewports returned `ok` with one finding each.
- Patch suggestions: one patch per finding, none rejected, none applied or verified. The model cannot see
  source code and the pages are drawn images, so the selectors are guesses.
- Close-up check, first prompt: it confirmed an overflow bug on the clean page in both control runs, so it was
  not reliable.
- Close-up check, neutral prompt (earlier step may be wrong, specific evidence required, earlier evidence
  not repeated): buggy pages confirmed in 6 of 6 runs. Clean pages were never confirmed in 9 completed runs
  (8 not_confirmed, 1 inconclusive); one further run was lost to a file-lock error. The prompt was reworded
  after seeing the failed control, so this is tuned on seen pages.
- Cropping savings: the crop sent 66% (desktop) and 89% (mobile) fewer pixels, and 49% and 93% fewer bytes.
  Median seconds over five runs: mobile 3.62 to 2.89 (about 20% faster, all five runs), desktop 3.04 to 2.85
  (about 6% faster, four of five runs). One page each, so a small saving, not a benchmark.
- Not yet tested: whether a suggested fix works on a real page, and pages the prompts have not seen.
