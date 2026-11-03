"""Week 3: the self-healing loop. Plan, Execute, Evaluate, retry.

For one finding the loop does this, up to max_attempts times:
  PLAN      ask the model for a small CSS fix (earlier failed attempts are passed back as feedback)
  EXECUTE   apply that CSS to a LOCAL COPY of the page and take a new screenshot
  EVALUATE  ask the model to compare BEFORE and AFTER, and combine that with a metrics rescan

The loop stops when the fix is verified, when the verdict is inconclusive (a human decides),
when the model cannot suggest a safe fix, or when attempts run out.

Two safety rules, enforced by the structure:
- This module never touches a page. Applying the CSS is done by the caller-supplied
  apply_and_rescan(css), which must start from the ORIGINAL page each call and work on a local copy.
- Nothing is merged or published. A "fixed" result is a suggestion with evidence for a human to
  approve (for example as a pull request).

"fixed" needs the model AND the metrics rescan to agree (see vision.patches.combine_verdicts).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .patches import ISSUE_TYPES, _as_dict, combine_verdicts, suggest_patches, verify_fix

MAX_ATTEMPTS_LIMIT = 5


def build_css(patches) -> str:
    """CSS text from validated patches. Selector and declarations were already checked."""
    return "\n".join(f"{p.selector} {{ {p.css_after} }}" for p in patches)


@dataclass
class Rescan:
    """What apply_and_rescan returns: the new screenshot, and the metrics verdict if known."""
    after_png: bytes
    metrics_fixed: bool | None = None  # True / False from a metrics rescan; None = not measured


@dataclass
class Attempt:
    number: int
    css: str
    model_verdict: str
    verdict: str          # the final verdict for this attempt
    reason: str
    evidence: str = ""
    new_problems: str = "none"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HealResult:
    scan_id: str
    viewport: str
    status: str           # fixed | not_fixed | inconclusive | no_patch | error
    message: str
    attempts: list = field(default_factory=list)
    final_css: str | None = None
    source_file: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def heal(provider, finding, before_png: bytes, *, scan_id: str, viewport: str, width: int,
         height: int, apply_and_rescan, source_file: str | None = None, html: str | None = None,
         max_attempts: int = 3, timeout: float = 60.0) -> HealResult:
    """Run the Plan, Execute, Evaluate loop for one finding. Never raises."""
    attempts: list = []

    def done(status, message, css=None):
        return HealResult(scan_id=scan_id, viewport=viewport, status=status, message=message,
                          attempts=attempts, final_css=css, source_file=source_file)

    try:
        f = _as_dict(finding)
    except TypeError as e:
        return done("error", str(e))
    issue = f.get("issue_type") if f.get("issue_type") in ISSUE_TYPES else "other"
    try:
        limit = max(1, min(int(max_attempts), MAX_ATTEMPTS_LIMIT))
    except (TypeError, ValueError):
        limit = 1

    feedback = None
    for number in range(1, limit + 1):
        # PLAN
        plan = suggest_patches(provider, f, before_png, scan_id=scan_id, viewport=viewport,
                               width=width, height=height, source_file=source_file, html=html,
                               timeout=timeout, feedback=feedback)
        if plan.outcome != "ok":
            return done("error", f"patch step failed: {plan.outcome} {plan.error or ''}".strip())
        if not plan.patches:
            return done("no_patch", "the model could not suggest a safe fix" if plan.cannot_determine
                        else "no usable patch came back")
        css = build_css(plan.patches)

        # EXECUTE (on a local copy, by the caller)
        try:
            rescan = apply_and_rescan(css)
            if not isinstance(rescan, Rescan) or not rescan.after_png:
                raise TypeError("apply_and_rescan must return a Rescan with a screenshot")
        except Exception as e:  # defensive: a failed rescan must not crash the pipeline
            return done("error", f"apply and rescan failed: {type(e).__name__}: {str(e)[:120]}")

        # EVALUATE
        check = verify_fix(provider, before_png, rescan.after_png, issue_type=issue,
                           element=str(f.get("element") or ""), scan_id=scan_id,
                           viewport=viewport, timeout=timeout)
        model_verdict = check.verdict if check.outcome == "ok" else "inconclusive"
        problems = check.new_problems if check.outcome == "ok" else "none"
        final, reason = combine_verdicts(model_verdict, rescan.metrics_fixed, problems)
        attempts.append(Attempt(number=number, css=css, model_verdict=model_verdict,
                                verdict=final, reason=reason,
                                evidence=check.evidence if check.outcome == "ok" else "",
                                new_problems=problems))
        if final == "fixed":
            return done("fixed", reason, css)
        if final == "inconclusive":
            return done("inconclusive", f"{reason}; a human needs to decide")
        note = f"attempt {number}: `{css}` did not fix it ({check.evidence or reason})"
        feedback = f"{feedback} | {note}" if feedback else note

    return done("not_fixed", f"not fixed after {limit} attempt{'s' if limit != 1 else ''}")
