# Audit Report

## 1. Critical Issues (Blocking)

### 1.1 Test Failures
- `backend/tests/test_meta_sync.py` fails with mock configuration issues.
- `backend/tests/test_external_services.py` fails when mocks are not properly configured as awaitable (Fixed during audit preparation).

### 1.2 Link Creation Slug Uniqueness
- **File:** `backend/routes/links.py`
- **Issue:** The slug generation uses `uuid.uuid4()[:4]`. This has a small but real collision probability (16^4 = 65,536). If a collision occurs, the insert will fail (assuming DB unique constraint) or `slug already exists` check catches it. The check `existing.data` is good, but if it fails, it raises 400. It doesn't retry.
- **Impact:** User might get a random "Slug exists" error.
- **Fix:** Add retry logic or use longer ID.

### 1.3 `links.py` Error Handling
- **File:** `backend/routes/links.py`
- **Issue:** `create_link` catches generic `Exception` and returns 500 with `detail=str(e)`. This can expose database schema details to the client.
- **Fix:** Log the error and return a generic "Internal Server Error" or "Database Error".

### 1.4 `tracker.py` Security
- **File:** `backend/routes/tracker.py`
- **Issue:** `_parse_device` relies on `ua_parser`.
- **Issue:** `redirect_url` construction for `funnel_type == "capture"` uses `PROXY_BASE_URL`. Ensure `PROXY_BASE_URL` is set correctly in prod.
- **Issue:** `proxy_capture_page` fetches external URLs. This is a Server-Side Request Forgery (SSRF) vector if `capture_url` isn't validated to be a safe/allowed domain or if the user can input internal network IPs (e.g. `http://localhost:8000`).
- **Fix:** Validate `capture_url` against a blocklist (no localhost, no private IPs).

### 1.5 `leads.py` PII & Security
- **File:** `backend/routes/leads.py`
- **Status:** Uses `encrypt_cpf`. Good.
- **Issue:** `submit_lead` returns `whatsapp_link` constructed from `client_whats`. If `client_whats` is missing, it sends to `https://wa.me/?text=...` which is broken UX.
- **Issue:** `LeadSubmit` model has `consent_given: bool = False`. The code checks `if not payload.consent_given: raise HTTPException(400)`. Good.

## 2. Code Quality & Architecture

### 2.1 Code Duplication
- **Issue:** `_parse_device` is defined in `tracker.py` AND `leads.py` (slightly different implementation).
- **Fix:** Move to `backend/utils/device.py`.

### 2.2 Hardcoded URLs
- **File:** `backend/routes/tracker.py`
- **Issue:** Fallback URLs `https://app.funila.com.br...` are hardcoded defaults if env vars missing.
- **Fix:** Ensure these are consistently loaded from config.

### 2.3 Type Safety
- **Issue:** Many Supabase calls return dynamic dicts. Pydantic models are used for Input, but Output is often raw dicts.
- **Fix:** Use Pydantic models for response serialization to ensure no sensitive fields leak.

## 3. Frontend / E2E

### 3.1 Kanban Responsiveness
- **Status:** Fixed in previous task.

### 3.2 Error Handling
- **Status:** Improved in `master` panel. Needs verification in `form` app.

## 4. Plan
1. Fix Tests.
2. Refactor `_parse_device` to shared util.
3. Add SSRF protection to `tracker.py`.
4. Improve Error Hiding in `links.py`.
5. Verify `form` frontend submission.
