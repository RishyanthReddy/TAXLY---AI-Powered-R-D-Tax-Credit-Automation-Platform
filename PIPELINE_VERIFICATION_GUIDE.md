# Pipeline Verification Guide

## Overview

This guide provides comprehensive instructions for verifying that the R&D Tax Credit Automation backend pipeline is working correctly. It covers expected PDF characteristics, verification test procedures, result interpretation, and troubleshooting common issues.

**Target Audience:** Developers, QA Engineers, System Administrators

**Last Updated:** October 30, 2025

---

## Table of Contents

1. [Quick Verification Checklist](#quick-verification-checklist)
2. [Expected PDF Characteristics](#expected-pdf-characteristics)
3. [Running Verification Tests](#running-verification-tests)
4. [Interpreting Test Results](#interpreting-test-results)
5. [Common Issues and Fixes](#common-issues-and-fixes)
6. [Performance Benchmarks](#performance-benchmarks)
7. [API Health Verification](#api-health-verification)
8. [Data Flow Verification](#data-flow-verification)

---

## Quick Verification Checklist

Use this checklist for rapid pipeline health assessment:

### ✅ Pre-Flight Checks

- [ ] All API keys configured in `.env` file
- [ ] Virtual environment activated
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Knowledge base indexed (ChromaDB populated)
- [ ] Test fixtures present in `tests/fixtures/`

### ✅ Pipeline Health Checks

- [ ] All unit tests pass (`pytest tests/unit/ -v`)
- [ ] All integration tests pass (`pytest tests/integration/ -v`)
- [ ] End-to-end test generates complete PDF
- [ ] PDF file size: 15-20KB (for 5 projects)
- [ ] PDF page count: 9-12 pages (for 5 projects)
- [ ] All 7 PDF sections present

### ✅ API Connectivity Checks

- [ ] You.com Agent API responding
- [ ] You.com Express Agent API responding
- [ ] GLM 4.5 Air (OpenRouter) responding
- [ ] Clockify API responding (if used)
- [ ] Unified.to API responding (if used)

---

## Expected PDF Characteristics


### PDF Size and Page Count

Complete PDFs should meet these specifications based on project count:

| Project Count | Expected File Size | Expected Page Count | Generation Time |
|---------------|-------------------|---------------------|-----------------|
| 1 project     | 8-12 KB          | 5-7 pages          | < 20 seconds    |
| 3 projects    | 12-16 KB         | 7-9 pages          | < 30 seconds    |
| 5 projects    | 15-20 KB         | 9-12 pages         | < 45 seconds    |
| 10 projects   | 20-30 KB         | 12-18 pages        | < 60 seconds    |
| 20 projects   | 35-50 KB         | 20-30 pages        | < 90 seconds    |

**Warning Signs:**
- PDF < 8 KB: Likely missing sections
- PDF < 5 pages: Incomplete report
- Generation time > 2x expected: API issues or performance degradation

### Required PDF Sections

Every complete PDF must contain these 7 sections:

1. **Cover Page**
   - Report title: "R&D Tax Credit Analysis Report"
   - Tax year
   - Generation date
   - Company name (if provided)
   - Report ID

2. **Table of Contents**
   - All major sections listed
   - Page numbers accurate
   - Proper formatting

3. **Executive Summary**
   - Total qualified hours
   - Total qualified cost
   - Estimated R&D credit (= total cost × 0.20)
   - Average confidence score
   - Total project count
   - Flagged project count
   - Risk assessment summary

4. **Project Breakdown Table**
   - One row per project
   - Columns: Project Name, Hours, Cost, Confidence, Qualification %
   - Totals row at bottom
   - Professional formatting with alternating row colors

5. **Individual Project Sections**
   - One section per project
   - Project details (hours, cost, confidence)
   - Qualification reasoning
   - IRS citations (source + supporting citation)
   - Technical narrative (>500 characters)
   - Compliance review status

6. **Technical Narratives Section**
   - Dedicated section for all narratives
   - One subsection per project
   - Full narrative text (>500 characters each)
   - Proper formatting and spacing

7. **IRS Citations Section**
   - All regulatory references
   - One subsection per project
   - IRS source reference
   - Supporting citation text
   - Professional citation formatting

### Data Accuracy Requirements


All calculations must be accurate within 0.01%:

- **Total Qualified Hours** = Sum of all project qualified hours
- **Total Qualified Cost** = Sum of all project qualified costs
- **Estimated Credit** = Total Qualified Cost × 0.20
- **Average Confidence** = Mean of all project confidence scores
- **Flagged Count** = Count of projects with confidence < 0.70

### Narrative Quality Standards

Each technical narrative must meet these criteria:

- **Minimum Length:** 500 characters
- **Content Requirements:**
  - Addresses the four-part test (Permitted Purpose, Technological in Nature, Elimination of Uncertainty, Process of Experimentation)
  - Includes specific technical details
  - References project activities and outcomes
  - Uses professional technical language
- **Compliance Status:** Reviewed by You.com Express Agent API
- **Format:** Proper paragraphs with clear structure

---

## Running Verification Tests

### Complete Test Suite

Run all verification tests to ensure pipeline health:

```bash
# Activate virtual environment
cd rd_tax_agent
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run complete test suite
pytest tests/ -v --tb=short

# Run with coverage report
pytest tests/ -v --cov=. --cov-report=html
```

### Targeted Test Categories

#### 1. Unit Tests (Fast, No API Calls)

```bash
# Test data models and validation
pytest tests/test_audit_report_fields.py -v
pytest tests/test_tax_models.py -v
pytest tests/test_financial_models.py -v

# Test utility functions
pytest tests/test_validators.py -v
pytest tests/test_pandas_processor.py -v
pytest tests/test_file_ops.py -v
```

#### 2. Integration Tests (Real API Calls)

```bash
# Test narrative generation
pytest tests/test_narrative_generation_integration.py -v

# Test compliance review
pytest tests/test_compliance_review_verification.py -v

# Test PDF generator
pytest tests/test_pdf_generator.py -v
pytest tests/test_pdf_sections.py -v
```

#### 3. End-to-End Tests (Complete Pipeline)

```bash
# Test complete pipeline with 5 projects
pytest tests/test_complete_pipeline.py -v

# Test PDF completeness
pytest tests/test_pdf_completeness.py -v

# Test calculation accuracy
pytest tests/test_calculations.py -v

# Test with varying project counts
pytest tests/test_complete_pipeline.py::test_pipeline_with_1_project -v
pytest tests/test_complete_pipeline.py::test_pipeline_with_3_projects -v
pytest tests/test_complete_pipeline.py::test_pipeline_with_10_projects -v
```

#### 4. Diagnostic Tests

```bash
# Run comprehensive diagnostic
pytest tests/test_pipeline_diagnostic.py -v

# Test logging and data flow
pytest tests/test_audit_trail_logging.py -v
pytest tests/test_pdf_generator_logging.py -v
```

### Manual Verification Script


Use the provided verification script for manual testing:

```bash
# Run PDF verification script
python verify_pdf_reports.py

# This script will:
# - Generate test PDFs with varying project counts
# - Analyze file size, page count, sections
# - Verify calculations
# - Generate detailed report
```

### Quick Smoke Test

For rapid verification during development:

```bash
# Run only critical tests (< 2 minutes)
pytest tests/test_complete_pipeline.py::test_pipeline_with_5_projects -v
pytest tests/test_pdf_completeness.py::test_all_sections_present -v
pytest tests/test_calculations.py::test_calculation_accuracy -v
```

---

## Interpreting Test Results

### Successful Test Output

A successful test run should look like this:

```
tests/test_complete_pipeline.py::test_pipeline_with_5_projects PASSED [100%]

✓ Pipeline completed in 42.3 seconds
✓ PDF generated: outputs/test_report_2024_20251030_143022.pdf
✓ File size: 17,234 bytes (within 15-20KB range)
✓ Page count: 11 pages (within 9-12 page range)
✓ All 7 sections present
✓ All calculations accurate (within 0.01%)
✓ All narratives >500 characters
```

### Test Failure Patterns

#### Pattern 1: Missing Narratives

```
FAILED tests/test_pdf_completeness.py::test_narratives_present
AssertionError: Expected 5 narratives, found 0
```

**Diagnosis:** AuditReport not passing narratives to PDF generator

**Fix:** See [Common Issue #1](#issue-1-missing-narratives-in-pdf)

#### Pattern 2: Incomplete PDF

```
FAILED tests/test_pdf_completeness.py::test_pdf_size
AssertionError: PDF size 6,234 bytes, expected 15,000-20,000 bytes
```

**Diagnosis:** Missing sections in PDF

**Fix:** See [Common Issue #2](#issue-2-incomplete-pdf-small-file-size)

#### Pattern 3: Calculation Errors

```
FAILED tests/test_calculations.py::test_estimated_credit
AssertionError: Expected $50,000.00, got $0.00
```

**Diagnosis:** Aggregated data not flowing to PDF

**Fix:** See [Common Issue #3](#issue-3-incorrect-calculations)

#### Pattern 4: API Failures

```
ERROR tests/test_narrative_generation_integration.py
APIConnectionError: You.com API authentication failed
```

**Diagnosis:** Invalid or missing API key

**Fix:** See [Common Issue #4](#issue-4-api-authentication-failures)

### Log Analysis

Check logs for detailed diagnostic information:

```bash
# View recent logs
tail -f logs/rd_tax_agent.log

# Search for errors
grep "ERROR" logs/rd_tax_agent.log

# Search for specific component
grep "AuditTrailAgent" logs/rd_tax_agent.log
grep "PDFGenerator" logs/rd_tax_agent.log
```

**Key Log Indicators:**

✅ **Healthy Pipeline:**
```
INFO: Starting audit trail for 5 projects
INFO: Generated 5 narratives
INFO: Aggregated data: {'total_qualified_hours': 1250.0, ...}
INFO: Creating AuditReport with complete data
INFO: Generating PDF for report RD_TAX_2024_20251030_143022
INFO: PDF generated: outputs/report.pdf (17234 bytes)
```

❌ **Unhealthy Pipeline:**
```
WARNING: Missing narrative for Project Alpha
ERROR: AuditReport missing narratives field
ERROR: Failed to generate PDF: ValueError
```

---

## Common Issues and Fixes


### Issue 1: Missing Narratives in PDF

**Symptoms:**
- PDF is 4-8 KB instead of 15-20 KB
- PDF has 3-5 pages instead of 9-12 pages
- Technical Narratives section is empty or missing
- Individual project sections lack narrative text

**Root Cause:**
AuditReport model not including narratives field, or AuditTrailAgent not populating it.

**Verification:**
```bash
pytest tests/test_audit_report_fields.py::test_narratives_field_present -v
pytest tests/test_pdf_completeness.py::test_narratives_present -v
```

**Fix:**

1. Verify AuditReport model includes narratives field:
```python
# In models/tax_models.py
class AuditReport(BaseModel):
    # ... other fields ...
    narratives: Dict[str, str] = Field(
        description="Technical narratives for each project"
    )
```

2. Verify AuditTrailAgent populates narratives:
```python
# In agents/audit_trail_agent.py, run() method
report = AuditReport(
    # ... other fields ...
    narratives=narratives,  # Must be included
    compliance_reviews=compliance_reviews,
    aggregated_data=aggregated_data
)
```

3. Verify PDFGenerator uses narratives:
```python
# In utils/pdf_generator.py
def _create_technical_narratives(self, report: AuditReport):
    for project in report.projects:
        narrative = report.narratives.get(project.project_name, "")
        # ... add to PDF ...
```

**Validation:**
```bash
pytest tests/test_complete_pipeline.py -v
```

---

### Issue 2: Incomplete PDF (Small File Size)

**Symptoms:**
- PDF file size < 10 KB
- PDF has < 7 pages
- Missing sections (TOC, Executive Summary, or Citations)

**Root Cause:**
PDF generator not calling all section generation methods, or sections failing silently.

**Verification:**
```bash
pytest tests/test_pdf_completeness.py::test_all_sections_present -v
pytest tests/test_pdf_sections.py -v
```

**Fix:**

1. Verify all sections are generated in `generate_report()`:
```python
# In utils/pdf_generator.py
def generate_report(self, report: AuditReport, output_dir: str, filename: str):
    elements = []
    elements.extend(self._create_cover_page(report))
    elements.extend(self._create_table_of_contents())
    elements.extend(self._create_executive_summary(report))
    elements.extend(self._create_project_breakdown(report))
    elements.extend(self._create_project_sections(report))
    elements.extend(self._create_technical_narratives(report))  # Must be included
    elements.extend(self._create_irs_citations(report))  # Must be included
    
    doc.build(elements)
```

2. Check for exceptions in section generation:
```bash
grep "ERROR.*_create_" logs/rd_tax_agent.log
```

3. Add validation before PDF generation:
```python
if not report.narratives:
    raise ValueError("AuditReport missing narratives")
if not report.aggregated_data:
    raise ValueError("AuditReport missing aggregated_data")
```

**Validation:**
```bash
python verify_pdf_reports.py
```

---

### Issue 3: Incorrect Calculations

**Symptoms:**
- Estimated credit = $0.00 or incorrect value
- Total hours/costs don't match sum of projects
- Average confidence is 0% or incorrect

**Root Cause:**
Aggregated data not calculated correctly or not passed to PDF generator.

**Verification:**
```bash
pytest tests/test_calculations.py -v
pytest tests/test_executive_summary_aggregated_data.py -v
```

**Fix:**

1. Verify aggregation logic in AuditTrailAgent:
```python
# In agents/audit_trail_agent.py
def _aggregate_report_data(self, qualified_projects, narratives, compliance_reviews):
    df = pd.DataFrame([{
        'project_name': p.project_name,
        'qualified_hours': p.qualified_hours,
        'qualified_cost': p.qualified_cost,
        'confidence': p.confidence_score
    } for p in qualified_projects])
    
    aggregated_data = {
        'total_qualified_hours': float(df['qualified_hours'].sum()),
        'total_qualified_cost': float(df['qualified_cost'].sum()),
        'estimated_credit': float(df['qualified_cost'].sum() * 0.20),  # Must be 20%
        'average_confidence': float(df['confidence'].mean()),
        # ... other fields ...
    }
    return aggregated_data
```

2. Verify AuditReport receives aggregated data:
```python
report = AuditReport(
    total_qualified_hours=aggregated_data['total_qualified_hours'],
    total_qualified_cost=aggregated_data['total_qualified_cost'],
    estimated_credit=aggregated_data['estimated_credit'],
    # ... other fields ...
    aggregated_data=aggregated_data  # Must be included
)
```

3. Verify PDF uses correct values:
```python
# In utils/pdf_generator.py
def _create_executive_summary(self, report: AuditReport):
    summary_data = [
        ['Estimated R&D Credit:', f"${report.estimated_credit:,.2f}"],
        # Use report fields, not aggregated_data directly
    ]
```

**Validation:**
```bash
pytest tests/test_calculations.py::test_calculation_accuracy -v
```

---

### Issue 4: API Authentication Failures

**Symptoms:**
- Tests fail with "authentication failed" or "401 Unauthorized"
- Narrative generation fails
- Compliance review fails

**Root Cause:**
Missing or invalid API keys in `.env` file.

**Verification:**
```bash
# Check if .env file exists
ls -la rd_tax_agent/.env

# Verify API keys are set (don't print actual keys)
python -c "from utils.config import get_config; c = get_config(); print('YOUCOM_API_KEY:', 'SET' if c.youcom_api_key else 'MISSING')"
```

**Fix:**

1. Create or update `.env` file:
```bash
cd rd_tax_agent
cp .env.example .env  # If .env.example exists
nano .env  # Or use your preferred editor
```

2. Add required API keys:
```bash
# You.com API
YOUCOM_API_KEY=your_actual_api_key_here

# OpenRouter API (for GLM 4.5)
OPENROUTER_API_KEY=your_actual_api_key_here

# Optional: Clockify and Unified.to
CLOCKIFY_API_KEY=your_clockify_key
UNIFIED_TO_API_KEY=your_unified_to_key
```

3. Verify keys are loaded:
```python
from utils.config import get_config
config = get_config()
assert config.youcom_api_key, "YOUCOM_API_KEY not set"
assert config.openrouter_api_key, "OPENROUTER_API_KEY not set"
```

**Validation:**
```bash
pytest tests/test_you_com_integration.py::test_api_authentication -v
```

---

### Issue 5: Slow Performance

**Symptoms:**
- Pipeline takes > 60 seconds for 10 projects
- Narrative generation is slow
- Tests timeout

**Root Cause:**
Sequential API calls instead of concurrent, or API rate limiting.

**Verification:**
```bash
pytest tests/test_api_performance.py -v
```

**Fix:**

1. Verify concurrent processing is enabled:
```python
# In agents/audit_trail_agent.py
async def _generate_narratives_batch(self, qualified_projects, max_concurrent=5):
    # Should use asyncio.gather for concurrent calls
    tasks = [self._generate_narrative_async(p) for p in qualified_projects]
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

2. Check rate limiter configuration:
```python
# In tools/youcom_rate_limiter.py
rate_limiter = YouComRateLimiter(
    requests_per_minute=60,  # Adjust based on API limits
    requests_per_day=1000
)
```

3. Monitor API response times:
```bash
grep "API call duration" logs/rd_tax_agent.log
```

**Validation:**
```bash
time pytest tests/test_complete_pipeline.py::test_pipeline_with_10_projects -v
# Should complete in < 60 seconds
```

---

### Issue 6: ChromaDB/Vector Database Errors

**Symptoms:**
- "Collection not found" errors
- RAG queries fail
- Knowledge base queries return no results

**Root Cause:**
Knowledge base not indexed or ChromaDB not initialized.

**Verification:**
```bash
# Check if ChromaDB file exists
ls -la knowledge_base/chroma.sqlite3

# Verify collection exists
python -c "from tools.vector_db import VectorDB; db = VectorDB(); print(db.collection.count())"
```

**Fix:**

1. Run indexing pipeline:
```bash
cd rd_tax_agent
python scripts/run_indexing_pipeline.py
```

2. Verify indexing completed:
```bash
python scripts/verify_indexing.py
```

3. Check indexed document count:
```python
from tools.vector_db import VectorDB
db = VectorDB()
count = db.collection.count()
print(f"Indexed documents: {count}")
# Should be > 0
```

**Validation:**
```bash
pytest tests/test_rd_knowledge_tool.py -v
pytest tests/test_rag_integration.py -v
```

---

## Performance Benchmarks


### Expected Performance Metrics

| Operation | Project Count | Expected Time | Max Acceptable Time |
|-----------|---------------|---------------|---------------------|
| Data Ingestion | N/A | < 5 seconds | 10 seconds |
| Qualification | 10 projects | < 15 seconds | 30 seconds |
| Narrative Generation | 10 projects | < 30 seconds | 60 seconds |
| Compliance Review | 10 projects | < 20 seconds | 40 seconds |
| PDF Generation | 10 projects | < 10 seconds | 20 seconds |
| **Complete Pipeline** | **10 projects** | **< 60 seconds** | **120 seconds** |

### Performance Testing

Run performance benchmarks:

```bash
# Test narrative generation performance
pytest tests/test_api_performance.py::test_narrative_generation_performance -v

# Test complete pipeline performance
pytest tests/test_complete_pipeline.py::test_pipeline_performance -v --durations=10
```

### Performance Optimization Tips

1. **Use Concurrent Processing:**
   - Enable `max_concurrent=5` for API calls
   - Use `asyncio.gather()` for parallel operations

2. **Enable Caching:**
   - Cache You.com API responses
   - Cache GLM 4.5 reasoning results
   - Use Redis for distributed caching (optional)

3. **Optimize Database Queries:**
   - Use batch queries for ChromaDB
   - Limit vector search results to top 5-10

4. **Monitor Rate Limits:**
   - Track API usage with YouComAPIMonitor
   - Implement exponential backoff for retries

---

## API Health Verification

### Manual API Health Check

Test each API endpoint manually:

```bash
# Test You.com Agent API
python -c "
from tools.you_com_client import YouComClient
from utils.config import get_config
client = YouComClient(api_key=get_config().youcom_api_key)
response = client.agent_run(prompt='Test', agent_mode='express', stream=False)
print('You.com Agent API: OK' if response else 'FAILED')
"

# Test GLM 4.5 via OpenRouter
python -c "
from tools.glm_reasoner import GLMReasoner
from utils.config import get_config
reasoner = GLMReasoner(api_key=get_config().openrouter_api_key)
response = reasoner.reason('Test query')
print('GLM 4.5 API: OK' if response else 'FAILED')
"
```

### Automated Health Check

Use the health check tool:

```bash
# Run comprehensive health check
python -c "
from tools.health_check import HealthCheck
health = HealthCheck()
results = health.check_all()
for service, status in results.items():
    print(f'{service}: {status}')
"
```

### API Monitoring Dashboard

View API usage statistics:

```bash
# View You.com API usage
python -c "
from tools.youcom_api_monitor import YouComAPIMonitor
monitor = YouComAPIMonitor()
stats = monitor.get_usage_stats()
print(f'Total Requests: {stats[\"total_requests\"]}')
print(f'Success Rate: {stats[\"success_rate\"]:.1%}')
print(f'Avg Response Time: {stats[\"avg_response_time\"]:.2f}s')
"
```

---

## Data Flow Verification

### Verify Complete Data Flow

Test data flows correctly through all pipeline stages:

```bash
# Run data flow diagnostic
pytest tests/test_audit_trail_logging.py::test_complete_data_flow -v
```

### Expected Data Flow

```
1. Data Ingestion Agent
   ↓ (time_entries, payroll_data)
2. Qualification Agent
   ↓ (qualified_projects with reasoning)
3. Audit Trail Agent
   ├─ Generate Narratives → narratives dict
   ├─ Review Narratives → compliance_reviews dict
   ├─ Aggregate Data → aggregated_data dict
   └─ Create AuditReport (includes all three dicts)
   ↓ (complete AuditReport)
4. PDF Generator
   ├─ Validate AuditReport completeness
   ├─ Generate all 7 sections
   └─ Build PDF
   ↓ (complete PDF file)
5. Output: Complete PDF (15-20KB, 9-12 pages)
```

### Data Flow Checkpoints

Verify data at each checkpoint:

**Checkpoint 1: After Qualification**
```python
assert len(qualified_projects) > 0
assert all(p.reasoning for p in qualified_projects)
assert all(p.irs_source for p in qualified_projects)
```

**Checkpoint 2: After Narrative Generation**
```python
assert len(narratives) == len(qualified_projects)
assert all(len(n) > 500 for n in narratives.values())
```

**Checkpoint 3: After Aggregation**
```python
assert 'total_qualified_cost' in aggregated_data
assert 'estimated_credit' in aggregated_data
assert aggregated_data['estimated_credit'] == aggregated_data['total_qualified_cost'] * 0.20
```

**Checkpoint 4: After AuditReport Creation**
```python
assert report.narratives is not None
assert report.aggregated_data is not None
assert len(report.narratives) == len(report.projects)
```

**Checkpoint 5: After PDF Generation**
```python
assert Path(pdf_path).exists()
assert Path(pdf_path).stat().st_size >= 15000  # 15 KB minimum
```

---

## Troubleshooting Workflow

Follow this workflow when encountering issues:

### Step 1: Identify the Failure Point

```bash
# Run diagnostic test
pytest tests/test_pipeline_diagnostic.py -v -s

# Check logs
tail -100 logs/rd_tax_agent.log
```

### Step 2: Isolate the Component

```bash
# Test individual components
pytest tests/test_audit_trail_agent.py -v  # If narrative generation fails
pytest tests/test_pdf_generator.py -v      # If PDF generation fails
pytest tests/test_you_com_client.py -v     # If API calls fail
```

### Step 3: Verify Configuration

```bash
# Check environment variables
python -c "
from utils.config import get_config
config = get_config()
print('YOUCOM_API_KEY:', 'SET' if config.youcom_api_key else 'MISSING')
print('OPENROUTER_API_KEY:', 'SET' if config.openrouter_api_key else 'MISSING')
"

# Check file permissions
ls -la outputs/
ls -la knowledge_base/
```

### Step 4: Run Targeted Fix

Based on the issue identified, apply the appropriate fix from [Common Issues and Fixes](#common-issues-and-fixes).

### Step 5: Validate Fix

```bash
# Re-run failed test
pytest tests/test_complete_pipeline.py -v

# Run full verification
python verify_pdf_reports.py
```

---

## Continuous Monitoring

### Daily Health Checks

Run these checks daily in production:

```bash
# Quick smoke test (< 2 minutes)
pytest tests/test_complete_pipeline.py::test_pipeline_with_5_projects -v

# API health check
python -c "from tools.health_check import HealthCheck; HealthCheck().check_all()"

# Check disk space for outputs
df -h outputs/
```

### Weekly Full Verification

Run comprehensive verification weekly:

```bash
# Full test suite
pytest tests/ -v --cov=. --cov-report=html

# Performance benchmarks
pytest tests/test_api_performance.py -v

# Generate verification report
python verify_pdf_reports.py > weekly_verification_report.txt
```

### Monitoring Alerts

Set up alerts for:

- Test failures in CI/CD pipeline
- API error rate > 5%
- Average response time > 10 seconds
- PDF generation failures
- Disk space < 1 GB in outputs/

---

## Additional Resources

### Documentation

- [Audit Trail Agent README](agents/AUDIT_TRAIL_AGENT_README.md)
- [PDF Generator README](utils/PDF_GENERATOR_README.md)
- [You.com Client README](tools/you_com_client.py)
- [Testing Guide](tests/README.md)

### Example Scripts

- [Audit Trail Usage Example](examples/audit_trail_agent_usage_example.py)
- [PDF Generator Usage Example](examples/pdf_generator_usage_example.py)
- [Batch Narrative Generation](examples/batch_narrative_generation_example.py)

### Support

For additional support:

1. Check existing test files in `tests/` for examples
2. Review implementation summaries in `TASK_*_IMPLEMENTATION_SUMMARY.md` files
3. Examine logs in `logs/rd_tax_agent.log`
4. Run diagnostic script: `python run_diagnostic.py`

---

**Document Version:** 1.0  
**Last Updated:** October 30, 2025  
**Maintained By:** R&D Tax Credit Automation Team
