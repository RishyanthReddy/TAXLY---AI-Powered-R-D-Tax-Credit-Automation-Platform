# Quick Reference: Tasks 129 & 130

## Status: ✓✓✓ PRODUCTION READY

---

## Run Tests

```bash
# Quick test (30 seconds)
python rd_tax_agent/test_youcom_all_endpoints.py

# Full E2E test (70 seconds)
python rd_tax_agent/test_tasks_129_130_e2e.py
```

---

## You.com API Endpoints

| API | URL | Auth |
|-----|-----|------|
| Search | `GET https://api.ydc-index.io/v1/search` | X-API-Key |
| Contents | `POST https://api.ydc-index.io/v1/contents` | X-API-Key |
| Express Agent | `POST https://api.you.com/v1/agents/runs` | Bearer |

---

## Task 129: Qualification

**Endpoint**: `POST /api/qualify`

**Input**:
```json
{
  "time_entries": [...],
  "costs": [...],
  "tax_year": 2024
}
```

**Output**:
```json
{
  "success": true,
  "qualified_projects": [...],
  "estimated_credit": 3000.00,
  "average_confidence": 0.85
}
```

**Performance**: ~10 seconds

---

## Task 130: Report Generation

**Endpoint**: `POST /api/generate-report`

**Input**:
```json
{
  "qualified_projects": [...],
  "tax_year": 2024,
  "company_name": "Acme Corp"
}
```

**Output**:
```json
{
  "success": true,
  "report_id": "report_20240115_123456",
  "pdf_path": "reports/report_20240115_123456.pdf"
}
```

**Performance**: ~55 seconds

---

## Test Results

| Test | Status | Time |
|------|--------|------|
| Search API | ✓ PASSED | 2s |
| Contents API | ✓ PASSED | 1s |
| Express Agent API | ✓ PASSED | 11s |
| Task 129 E2E | ✓ PASSED | 11s |
| Task 130 E2E | ✓ PASSED | 55s |

**Overall**: 100% success rate (7/7 API calls)

---

## Files

- **Tests**: `test_youcom_all_endpoints.py`, `test_tasks_129_130_e2e.py`
- **Docs**: `TASKS_129_130_VERIFICATION.md`, `TASKS_129_130_E2E_TEST_RESULTS.md`
- **Summary**: `FINAL_VERIFICATION_SUMMARY.md`
- **This file**: `QUICK_REFERENCE.md`

---

## What Was Fixed

1. ✓ Contents API base URL: `api.you.com` → `api.ydc-index.io`
2. ✓ Contents API payload: `{"url": "..."}` → `{"urls": ["..."]}`
3. ✓ Contents API response: Handle array format
4. ✓ Search API parameter: `num_web_results` → `count`

---

## Ready for Production ✓

All tests passed. All endpoints working. Documentation complete.
