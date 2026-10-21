\# OmniSight Frontend Regression Test Plan



\## 1. Navigation

\- Verify all sidebar pages open correctly.

\- Verify the active navigation item updates correctly.

\- Verify browser refresh does not break navigation.



\## 2. Demo Scan

\- Validate URL input.

\- Create a demo scan record.

\- Confirm that no real website scan is performed.

\- Verify the demo status is displayed correctly.



\## 3. Browser Persistence

\- Create a demo scan record.

\- Refresh the page and verify the record remains.

\- Create another record and verify its ID increments.

\- Verify the application handles unavailable browser storage.



\## 4. Scan History

\- Verify saved demo records appear in scan history.

\- Verify search and filtering interactions.

\- Verify scan details open correctly.



\## 5. Responsive Layout

\- Test desktop layout at 1366px width.

\- Test mobile layout at 390px width.

\- Check for overlapping elements and horizontal overflow.



\## 6. Accessibility

\- Test keyboard navigation.

\- Verify visible focus indicators.

\- Verify form labels and button names.



\## Scope

These are manual frontend regression tests. The current application uses demo data; this plan does not imply that a backend or real scanning engine exists.

