"""Frozen data contract for the vision module (share with Members 1, 2, 4)."""
from typing import Literal, Optional
from pydantic import BaseModel, Field

Viewport = Literal["desktop", "mobile"]
IssueType = Literal[
    "horizontal_overflow", "offscreen_button", "overlapping_text",
    "hidden_control", "low_contrast", "other",
]
Severity = Literal["low", "medium", "high"]
# Subset of the shared status vocabulary this module may emit.
FindingStatus = Literal["detected", "inconclusive"]


class BoundingBox(BaseModel):
    """Approximate region on the screenshot, as fractions (0-1) of its size."""
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)
    width: float = Field(..., gt=0.0, le=1.0)
    height: float = Field(..., gt=0.0, le=1.0)


class ModelFinding(BaseModel):
    """What the model is asked to return (no scan context; we add that)."""
    issue_type: IssueType
    element: Optional[str] = Field(None, description="CSS selector or description")
    severity: Severity
    evidence: str = Field(..., min_length=1)
    impact: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    status: FindingStatus = "detected"
    suggested_fix: Optional[str] = None
    summary: Optional[str] = Field(None, description="One plain-language sentence for the dashboard")
    bbox: Optional[BoundingBox] = None


class ModelOutput(BaseModel):
    findings: list[ModelFinding] = []
    cannot_determine: bool = False
    notes: Optional[str] = None


class Finding(ModelFinding):
    scan_id: str
    viewport: Viewport
    id: Optional[str] = None       # stable id, e.g. "scan-001:mobile:1"


Outcome = Literal["ok", "no_credentials", "provider_error", "invalid_output", "input_error"]


class AnalysisResult(BaseModel):
    scan_id: str
    viewport: Viewport
    provider: str
    outcome: Outcome
    findings: list[Finding] = []
    cannot_determine: bool = False
    error: Optional[str] = None
    json_repaired: bool = False    # True if the model's JSON needed trailing commas removed


class PatchProposal(BaseModel):
    """Reviewable only. Never executed by this module."""
    scan_id: str
    finding_id: Optional[str] = None
    file_path: str
    selector: str
    diff: str                      # unified diff text
    css_rule: Optional[str] = None  # the rule alone, for injection into a COPY of the page
    rationale: str
    expected_outcome: str
    verification_check: Optional[dict] = None   # machine-checkable, see vision/verify.py
    source: Literal["template", "model"] = "template"
    status: Literal["fix_proposed"] = "fix_proposed"
