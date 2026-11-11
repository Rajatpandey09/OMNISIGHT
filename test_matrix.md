# OmniSight Test Matrix & Evaluation Criteria

**Author:** Member 4 (QA, Integration & Self-Healing Engineer)  
**Project:** OmniSight (`omnisight-backend`)  
**Scope:** Cross-viewport visual defect verification, scanner metric accuracy, and multimodal VLM triage validation.

---

## 1. Test Matrix Overview

The test matrix defines reproducible visual defect testbeds, expected signals across viewports, primary detection mechanisms, and unambiguous pass/fail criteria.

| Case ID | Test Page | Viewport | Expected Defect | Expected Signal | Primary Detector | Pass/Fail Criteria |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`overflow_mobile`** | `bug_overflow.html` | Mobile ($390\times844$) | Horizontal Overflow | `scrollWidth > clientWidth` ($650\text{px} > 390\text{px}$) | DOM Metric Scanner | **Pass:** Flagged as `has_horizontal_overflow: true`.<br>**Fail:** Overflow undetected. |
| **`overflow_desktop`** | `bug_overflow.html` | Desktop ($1366\times768$) | *None (Clean)* | Content fits within $1366\text{px}$ width | Negative Control | **Pass:** `has_horizontal_overflow: false`.<br>**Fail:** False alarm raised on desktop. |
| **`offscreen_button_mobile`** | `bug_offscreen_button.html` | Mobile ($390\times844$) | Off-Screen Button | `boundingClientRect.right > innerWidth` ($550\text{px} > 390\text{px}$) | DOM Metric Scanner | **Pass:** Button flagged with `is_off_screen: true`.<br>**Fail:** Button recorded as visible. |
| **`offscreen_button_desktop`** | `bug_offscreen_button.html` | Desktop ($1366\times768$) | *None (Clean)* | Button at $x=450\text{px}$ is fully visible inside $1366\text{px}$ | Negative Control | **Pass:** `is_off_screen: false`.<br>**Fail:** False positive reported. |
| **`overlap_text_mobile`** | `bug_overlapping_text.html` | Mobile ($390\times844$) | Overlapping Text | Visual glyph collision between heading and paragraph | Vision AI (VLM) | **Pass:** VLM identifies `overlapping_text` in JSON.<br>**Fail:** Collision ignored. |
| **`hidden_control_mobile`** | `bug_hidden_control.html` | Mobile ($390\times844$) | Hidden Control | Interactive element with `display: none` / `[hidden]` | DOM Metric Scanner | **Pass:** Identified in `hidden_controls` metric list.<br>**Fail:** Control missed. |
| **`low_contrast_desktop`** | `bug_contrast.html` | Desktop ($1366\times768$) | Low Contrast | Text contrast ratio $< 4.5:1$ against white background | Vision AI (VLM) | **Pass:** VLM detects `low_contrast` on body text.<br>**Fail:** Unflagged. |
| **`clean_mobile`** | `clean.html` | Mobile ($390\times844$) | *None (Clean)* | Zero layout or visual defects | Negative Control | **Pass:** Zero issues reported (`tp=0, fp=0`).<br>**Fail:** Any false positive reported. |
| **`clean_desktop`** | `clean.html` | Desktop ($1366\times768$) | *None (Clean)* | Zero layout or visual defects | Negative Control | **Pass:** Zero issues reported (`tp=0, fp=0`).<br>**Fail:** Any false positive reported. |

---

## 2. Shared Status Vocabulary & Lifecycle

Every evaluated defect transitions through a strict state machine:

$$\text{detected} \longrightarrow \text{fix\_proposed} \longrightarrow \text{awaiting\_approval} \longrightarrow \text{applied} \longrightarrow \text{verified\_resolved} \text{ / } \text{verification\_failed}$$

* **`detected`:** The bug was captured by Playwright DOM metrics or diagnosed by Vision AI.
* **`fix_proposed`:** A safe, non-destructive CSS patch has been generated.
* **`awaiting_approval`:** The patch is pending human sign-off in the React QA dashboard.
* **`applied`:** The patch is injected into the live browser session (`/api/rescan`).
* **`verified_resolved`:** A follow-up scan confirms `scrollWidth <= clientWidth` and `is_off_screen == false`.
* **`verification_failed`:** The post-fix scan still shows the defect.
* **`inconclusive`:** The model or scanner cannot definitively confirm resolution.

---

## 3. Ground-Truth Data Contract

All test cases are mirrored in machine-readable JSON format at [`eval/labelled_cases.json`](file:///Users/priyanshusingh/Documents/College_Projects/omnisight-backend/eval/labelled_cases.json) and automated via `run_eval.py`.
