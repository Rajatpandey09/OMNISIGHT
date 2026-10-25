\# OmniSight API Contract



\*\*Status:\*\* Proposed — not implemented.



\## 1. Create a Scan



\*\*Endpoint:\*\* `POST /api/scans`



Request:



```json

{

&#x20; "url": "https://example.com",

&#x20; "viewports": \["desktop", "mobile"]

}

```



Response:



```json

{

&#x20; "id": "scan-001",

&#x20; "status": "queued"

}

```



\## 2. List Scan History



\*\*Endpoint:\*\* `GET /api/scans`



Returns the available scan history.



\## 3. Get Scan Details



\*\*Endpoint:\*\* `GET /api/scans/{scanId}`



Returns details for a specific scan.



\## 4. Get Scan Issues



\*\*Endpoint:\*\* `GET /api/scans/{scanId}/issues`



Returns the detected issues for a specific scan.



\## Implementation Notes



\- These endpoints are proposed and are not currently implemented.

\- The existing frontend uses demo data.

\- The future backend must validate submitted URLs.

\- The backend must protect against server-side request forgery (SSRF).

\- API responses should use consistent error formats and HTTP status codes.

\- Authentication and authorization requirements must be defined before production integration.

