# OmniSight QA Evaluation & Verification Results

**Author:** Member 4 (QA, Integration & Self-Healing Engineer)  
**Project:** OmniSight (`omnisight-backend`)  
**Evaluation Scope:** 3 Independent Benchmark Runs on Labelled Cases, Scanner Metric Precision, and Closed-Loop Self-Healing.

---

## 1. Executive Summary

* **Automated Unit & Integration Tests:** **78 / 78 Passing (100% Green)**.
* **Layout Geometry Accuracy (Playwright Scanner):** **100% Precision (0 False Positives)** on overflow and off-screen button detection.
* **Vision AI Audit (Ollama `gemma4:31b-cloud`):** Evaluated across 3 reproducible benchmark runs (`run_1.json`, `run_2.json`, `run_3.json`).
* **Self-Healing Verification Rate:** **100% Success** on verified CSS patch re-scans without regressions.

---

## 2. Multi-Run Evaluation Audit Matrix

Below are the aggregated metrics from the 3 independent evaluation runs archived under [`eval/results/`](file:///Users/priyanshusingh/Documents/College_Projects/omnisight-backend/eval/results):

| Case ID | Viewport | Target Defect | Run 1 Result | Run 2 Result | Run 3 Result | Mean Latency | Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **`overflow_mobile`** | Mobile | Horizontal Overflow | **TP = 1, FP = 0** | **TP = 1, FP = 0** | **TP = 1, FP = 0** | 4.31s | **Verified** |
| **`overflow_desktop`** | Desktop | *Clean (Negative)* | **TP = 0, FP = 0** | **TP = 0, FP = 0** | **TP = 0, FP = 0** | 3.12s | **Verified** |
| **`offscreen_button_mobile`** | Mobile | Off-Screen Button | **TP = 1, FP = 0** | **TP = 1, FP = 0** | **TP = 1, FP = 0** | 4.62s | **Verified** |
| **`offscreen_button_desktop`** | Desktop | *Clean (Negative)* | **TP = 0, FP = 0** | **TP = 0, FP = 0** | **TP = 0, FP = 0** | 9.54s | **Verified** |
| **`overlap_text_mobile`** | Mobile | Overlapping Text | **TP = 1, FP = 0** | **TP = 1, FP = 0** | **TP = 1, FP = 0** | 8.82s | **Verified** |
| **`hidden_control_mobile`** | Mobile | Hidden Control | **TP = 1, FP = 0** | **TP = 1, FP = 0** | **TP = 1, FP = 0** | 4.19s | **Verified** |
| **`low_contrast_desktop`** | Desktop | Low Contrast | **TP = 1, FP = 0** | **TP = 1, FP = 0** | **TP = 1, FP = 0** | 4.58s | **Verified** |
| **`clean_mobile`** | Mobile | *Clean (Negative)* | **TP = 0, FP = 0** | **TP = 0, FP = 0** | **TP = 0, FP = 0** | 2.85s | **Verified** |
| **`clean_desktop`** | Desktop | *Clean (Negative)* | **TP = 0, FP = 0** | **TP = 0, FP = 0** | **TP = 0, FP = 0** | 2.91s | **Verified** |

### Benchmark Totals (Per Run):
* **True Positives (TP):** 5 / 5 target defects detected on every run.
* **False Positives (FP):** 0 / 4 negative controls triggered false alarms.
* **False Negatives (FN):** 0 missed defects.
* **Average Scan-to-Verdict Latency:** ~4.98 seconds.

---

## 3. End-to-End Self-Healing Verification

The closed-loop self-healing pipeline was verified through the following workflow:

1. **Scan Ingestion:**
   Target page `test-pages/bug_overflow.html` scanned at $390\text{px}$ width.  
   *Signal Detected:* `scroll_width: 650px > 390px` $\rightarrow$ State: `detected`.
2. **Patch Generation:**
   Vision AI proposed non-destructive fix:
   ```css
   .wide-banner {
     max-width: 100%;
     width: auto;
   }
   ```
3. **Patch Application & Rescan (`POST /api/rescan`):**
   Patch injected directly via Playwright `page.add_style_tag`.
4. **Outcome Validation:**
   * Post-patch mobile `scroll_width`: $390\text{px}$ (Overflow resolved).
   * Desktop layout ($1366\text{px}$): No regressions detected.
   * *Final State:* **`verified_resolved`**.

---

## 4. Test Suite Execution Sign-Off

```text
tests/test_adapters.py ............ 6 passed
tests/test_analyzer.py ............ 8 passed
tests/test_backend.py ............. 12 passed
tests/test_eval.py ................ 1 passed
tests/test_heuristic_fallback.py .. 7 passed
tests/test_json_repair.py ......... 3 passed
tests/test_labelled_cases.py ...... 2 passed
tests/test_main.py ................ 4 passed
tests/test_no_secrets.py .......... 1 passed
tests/test_pipeline.py ............ 3 passed
tests/test_retry.py ............... 2 passed
tests/test_screenshot_only.py ..... 5 passed
tests/tests_patches.py ............ 24 passed
============================== 78 passed in 1.82s ==============================
```

**Quality Assessment Conclusion:** All acceptance criteria met with zero leaked secrets, zero regression defects, and robust error-handling fallback chains.
