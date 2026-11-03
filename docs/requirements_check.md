# Requirements check: Week 3, Week 4 and the final review (Member 3)

Status key: **Built** = code exists and is unit-tested with fake providers. **Real run pending** = not yet
run on the real model. **Not done** = no code yet. **Other member** = depends on a teammate's module.

## Week 3: self-healing loop (AI and automation)
The plan: apply the AI's CSS to the local DOM, take a new screenshot, ask the VLM whether the bug is fixed.

| Requirement | Status | Where |
|---|---|---|
| Agentic loop: Plan, Execute, Evaluate, retry if the fix fails | Built, real run pending | `vision/heal.py`: up to 3 attempts, failed attempts are fed back to the model |
| The model generates the CSS fix | Built, real run pending | `vision/patches.py`: validated JSON, unsafe CSS dropped |
| Apply the CSS to the local DOM | Other member | The loop calls `apply_and_rescan(css)`. The browser side is not written: inject the CSS into a local copy of the page (for example `page.add_style_tag(content=css)` in Playwright) |
| Take a new screenshot | Other member | Returned by the same `apply_and_rescan` function |
| Ask the VLM whether the bug is fixed | Built, real run pending | `verify_fix` and `combine_verdicts`: "fixed" needs the model and a metrics rescan to agree |

Open question for the mentor: the plan names LangChain or AutoGen for the orchestrator. The loop is plain Python.

## Week 3: GitHub integration (pipeline)
| Requirement | Status | Notes |
|---|---|---|
| PyGithub: create a branch, commit the fix, open a pull request | Not done | The loop result has what a PR needs: target file, final CSS, attempts and evidence. Screenshots and crops can serve as visual proof. Needs a GitHub token and an agreed owner. |

## Week 4: optimization (AI and automation)
| Requirement | Status | Where |
|---|---|---|
| Cropping to focus the VLM on the anomalous component | Built, real run pending | `vision/crop.py`, `run_crop.py` |
| Chunking | Algorithm built, not wired in | `vision/chunk.py`: overlapping tiles for tall pages and a way to map a tile region back to the page. The pipeline still shrinks tall pages. |
| Saves tokens and reduces latency | Measurement built, numbers not collected | `run_savings.py` reports pixels and bytes without a model, and seconds with `--time`. No saving is claimed until it is run. |

Note: the close-up check is an extra call after the first look. The saving is real only where follow-up calls
(verification, patch suggestions) use the crop instead of the full image. That wiring is not done.

## Week 4: dashboard (pipeline)
| Requirement | Status | Notes |
|---|---|---|
| React dashboard to approve or reject the AI's pull requests | Other member | Frontend report: dashboard layout and scan form done, real data and fix review remaining. Approve/reject needs the pull-request step above. |

## Final review: a fully autonomous, self-healing QA pipeline
| Link in the chain | Status |
|---|---|
| CI/CD webhook receiver | Other member: the backend report lists `/api/scan`, no webhook endpoint |
| Scan at two viewports with screenshots and metrics | Built (backend report) |
| Click through a checkout flow (Week 1 plan) | Not in the backend report: ask |
| Vision analysis of screenshots | Built, audited (4 of 5 seeded bugs found in every run on synthetic pages) |
| Fix suggestion, apply, rescan, verify, retry | Loop built; apply and rescan missing |
| Pull request with visual proof | Not done |
| Human approval in the dashboard | In progress |
| One complete run, start to finish | Not yet run |

The plan's use case also says the fix is Tailwind CSS. The current fixes are plain CSS declarations.

## Next steps, in order
1. Write `apply_and_rescan` with Members 2 and 4, then run `heal` on the overflow and off-screen-button pages.
2. Build the PyGithub step and agree who owns it.
3. Run `run_savings.py --time` and record the numbers.
4. Run the whole chain once and record what breaks.
