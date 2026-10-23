OmniSight QA Test Results

Objective

Record the actual results of each UI defect test and determine whether it passes or fails.

Test Environment

* Operating system: macOS
* Code editor: Visual Studio Code
* Project: OmniSight
* Viewports: Desktop and mobile

Test Results

Test ID	Defect	Actual Result	Status	Evidence
| TC01 | Horizontal overflow reproduced on mobile (390 × 844); document width was 920 px | Fail | eval/cases_data/horizontal_overflow/screenshot.png | Confirmed horizontal overflow; scanner and vision results still pending |
TC02	Off-screen button	Pending testing	Not Run	Pending
TC03	Overlapping text	Pending testing	Not Run	Pending
TC04	Hidden control	Pending testing	Not Run	Pending
TC05	Low contrast (optional)	Pending testing	Not Run	Pending

Notes

Record the browser, viewport dimensions, observations, and screenshot evidence when each test is performed.

Summary

Testing has not yet been performed. Results will be updated after executing the test cases.
QA Documentation Update

* Test matrix documented in test_matrix.md.
* Test results checklist documented in test_results.md.
* Manual horizontal scrolling check completed for OS-105. other test cases and backend verification remain pending.g
* Screenshots will be recorded after testing.
QA Documentation Update

### OS-105: Horizontal Scrolling at Mobile Viewport

- Viewport: 393 × 852 px
- Expected: No horizontal scrolling
- Actual: Page stayed fixed when dragged sideways
- Status: Pass — no horizontal scrolling observed
- Evidence: Mobile viewport screenshot
- Note: Backend verification remains inconclusive.
Follow-up Verification Checklist

* [ ]	Reproduce the original issue before applying a fix.
* [ ]	Record the browser and viewport dimensions.
* [ ]	Inspect the proposed CSS change.
* [ ]	Repeat the test after the fix.
* [ ]	Attach screenshot evidence.
* [ ]	Record the final result as Pass, Fail, or Inconclusive.QA Evidence Recording

For each executed test, record:

* Test case ID
* Browser and viewport size
* Expected result
* Actual result
* Pass, Fail, or Inconclusive status
* Screenshot or evidence reference
* Tester observations
Horizontal Overflow — Mobile Test

* Viewport: 393 × 852
* Expected defect: Horizontal overflow
* Test page: test-pages/bug_overflow.html
* Evidence: eval/evidence/horizontal-overflow-mobile.png
* Status: Observed — horizontal overflow visible in the test page.
* Note: This is an intentional test defect, not a production bug.
Off-Screen Button Test

Test page: bug_offscreen_button.html

Test objective: Verify whether the button stays inside the visible browser viewport.

Test	Expected result	Actual result
Broken page (left: 1200px)	FAIL — button outside viewport	FAIL
Fixed page	PASS — button inside viewport	PASS

Evidence: PASS and FAIL screenshots saved in eval/evidence/.

Status: Test performed; evidence captured.
| hidden_control | Hidden control | Submit button is not visible | Reproduced |
Horizontal Overflow — REPRODUCED

* Test page: eval/test-pages/bug_overflow.html
* Expected defect: Horizontal scrolling on a narrow viewport.
* Viewport width: 390 px
* Document scroll width: 920 px
* Horizontal overflow: true
* Excess width: 530 px
* Evidence: Safari Developer Tools Console output.
* Status: REPRODUCED
* Notes: The page width exceeds the viewport width, confirming horizontal overflow at the tested mobile width.