OmniSight QA Test Matrix

Role: Member 4 — QA, Integration & Self-Healing Engineer

1. Objective

Define reproducible UI defects, expected signals, and pass/fail criteria for testing the OmniSight project. Verify that defects are correctly detected and that fixes resolve them without introducing new issues.

2. Test Cases

Test ID	Viewport	Expected Defect	Expected Signal	Pass Criteria
TC01	Desktop	Horizontal overflow	Content exceeds the viewport width	Horizontal scrolling is detected
TC02	Mobile	Off-screen button	A button is outside the visible viewport	The button’s position is detected as outside the viewport
TC03	Desktop	Overlapping text	Two or more text elements overlap	The overlapping elements are identified
TC04	Mobile	Hidden control	A required control is not visible	The missing or hidden control is detected
TC05	Desktop	Low contrast (optional)	Text contrast is below the selected threshold	The contrast issue is reported

3. Test Environment

* Operating system: macOS
* Code editor: Visual Studio Code
* Project: OmniSight
* Test viewports: Desktop and mobile
* Evidence: Screenshots and test observations

Record the actual browser, viewport dimensions, and test date when testing is performed.

4. Test Execution

For each test case:

1. Open the test page.
2. Set the required desktop or mobile viewport.
3. Reproduce the expected UI defect.
4. Run the OmniSight scanning workflow.
5. Check whether the defect is detected correctly.
6. Record the actual result and pass/fail status.
7. Save a screenshot as evidence.

5. Test Results

Record the results using the following format.

Test ID	Actual Result	Status	Evidence	Notes
TC01	Pending	Not Run	Not Available	Awaiting execution
TC02	Pending	Not Run	Not Available	Awaiting execution
TC03	Pending	Not Run	Not Available	Awaiting execution
TC04	Pending	Not Run	Not Available	Awaiting execution
TC05	Pending	Not Run	Not Available	Optional test

Note: Update the actual result, status, and evidence after executing each test. Do not mark a test as passed until it has been verified.

6. Fix Verification

After a UI defect is fixed:

1. Open the same test page again.
2. Use the same viewport dimensions.
3. Run the scan again.
4. Check whether the original defect is resolved.
5. Confirm that the fix has not introduced another visible issue.
6. Capture an after-fix screenshot.
7. Record the final verification result.

7. Pass/Fail Criteria

* PASS: The expected defect is detected, and the result matches the defined criteria.
* FAIL: The defect is not detected, the result is incorrect, or the required behavior is not verified.
* NOT RUN: The test has not yet been executed.
* BLOCKED: The test cannot be performed because a required page, tool, or dependency is unavailable.

For fix verification, mark the fix as successful only when the original defect is no longer present and the relevant checks pass.

8. Responsibilities

As Member 4 — QA, Integration & Self-Healing Engineer:

* Create reproducible UI defect scenarios.
* Prepare and maintain the test matrix.
* Test desktop and mobile layouts.
* Verify defect detection and proposed fixes.
* Rerun tests after fixes.
* Capture screenshots and document evidence.
* Report failed tests and integration issues to the team.

9. Expected Outcome

A clear and repeatable QA process that helps the OmniSight team detect UI defects, verify fixes, and demonstrate the results with recorded test evidence.