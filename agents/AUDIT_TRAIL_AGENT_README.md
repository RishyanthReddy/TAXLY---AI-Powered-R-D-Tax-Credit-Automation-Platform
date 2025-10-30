# Audit Trail Agent Documentation

## Overview

The **AuditTrailAgent** is a PydanticAI-based agent responsible for generating comprehensive, audit-ready documentation for R&D tax credit claims. It orchestrates the complete audit trail generation workflow, from narrative creation to PDF report generation.

## Purpose

The AuditTrailAgent serves as the final stage in the R&D Tax Credit Automation pipeline, transforming qualified project data into professional, IRS-compliant documentation that can withstand audit scrutiny.

### Key Responsibilities

1. **Narrative Generation**: Creates detailed technical narratives for each qualified R&D project using You.com Agent API
2. **Compliance Review**: Reviews narratives for IRS compliance completeness using You.com Express Agent API
3. **Data Aggregation**: Aggregates all project data, calculates totals, and generates summary statistics using Pandas
4. **PDF Report Generation**: Produces professional PDF reports with all required sections and documentation
5. **Status Tracking**: Maintains real-time status updates throughout the workflow for frontend visualization

## Architecture

### Dependencies

- **You.com Agent API**: For generating technical narratives with web-enhanced context
- **You.com Express Agent API**: For fast compliance reviews and quality checks
- **GLM 4.5 Air (via OpenRouter)**: For agent reasoning and decision-making
- **PDFGenerator**: For creating professional PDF reports (utils/pdf_generator.py)
- **Pandas**: For data aggregation and statistical analysis

### Data Flow

```
Input: List[QualifiedProject] from Qualification Agent
  ↓
Stage 1: Generate Narratives (You.com Agent API)
  │ - Concurrent processing (max 5 concurrent)
  │ - Fallback generation if API fails
  │ - Minimum 500 character validation
  ↓
Stage 2: Review Narratives (You.com Express Agent)
  │ - Compliance status assessment
  │ - Completeness scoring (0-100%)
  │ - Flag projects needing manual review
  ↓
Stage 3: Aggregate Data (Pandas)
  │ - Calculate totals (hours, costs)
  │ - Compute estimated credit (20% of costs)
  │ - Generate summary statistics
  │ - Confidence distribution analysis
  ↓
Stage 4: Generate PDF Report (PDFGenerator)
  │ - Create AuditReport with complete data
  │ - Pass narratives, reviews, aggregated data
  │ - Generate professional PDF output
  ↓
Output: AuditTrailResult with complete report and PDF
```

## Complete Workflow Documentation

### Stage 1: Narrative Generation

**Purpose**: Generate comprehensive technical narratives for each qualified project that address the IRS four-part test.

**Method**: `_generate_narratives_batch()` and `_generate_narrative()`

**Process**:
1. **Batch Processing Setup**:
   - Initialize semaphore for concurrency control (max 5 concurrent)
   - Create async tasks for all projects
   - Track progress with state updates

2. **Per-Project Narrative Generation**:
   - Optionally fetch narrative template using You.com Contents API
   - Create detailed prompt with:
     - Project name and qualification details
     - Qualification reasoning from the Qualification Agent
     - IRS citations and regulatory basis
     - Technical details (if available)
   - Call You.com Agent API in "express" mode to generate the narrative
   - Extract narrative text from API response
   - Validate narrative length (minimum 500 characters)

3. **Fallback Generation** (if needed):
   - Generate structured narrative from project data
   - Include all IRS four-part test elements
   - Ensure minimum length requirements
   - Log fallback usage for monitoring

4. **Concurrent Execution**:
   - Process multiple projects in parallel
   - Respect You.com API rate limits (max 5 concurrent)
   - Gather results with exception handling
   - Continue processing even if individual projects fail

**Input**:
- `qualified_projects`: List[QualifiedProject] - Projects from Qualification Agent
- `template_url`: Optional[str] - URL to fetch narrative template
- `max_concurrent`: int - Maximum concurrent API calls (default: 5)

**Output**: 
- Dictionary mapping project names to narrative text
- Example: `{"API Optimization": "Technical narrative text...", ...}`

**Data Flow Between Methods**:
```
_generate_narratives_batch()
  ↓ Creates async tasks
_generate_narrative_async()
  ↓ Wraps synchronous call
_generate_narrative()
  ↓ Generates narrative
  ↓ If fails or too short
_generate_fallback_narrative()
  ↓ Returns narrative text
```

**Error Handling**: 
- If You.com API fails: Generates fallback narrative from project data
- If narrative too short: Generates fallback narrative
- Logs all failures with detailed context
- Continues processing remaining projects
- Returns partial results if some projects fail

**Performance**:
- Concurrent processing: ~30 seconds for 10 projects
- Sequential would take: ~60 seconds for 10 projects
- Rate limiting prevents API throttling

### Stage 2: Compliance Review

**Purpose**: Review each generated narrative for IRS compliance completeness and quality.

**Method**: `_review_narrative()` and `_parse_compliance_review()`

**Process**:
1. **Review Preparation**:
   - Validate narrative is not empty
   - Create compliance review prompt using template
   - Add project context (qualification %, confidence, IRS source)
   - Include original qualification reasoning

2. **API Call**:
   - Call You.com Express Agent API for fast compliance review
   - Use "express" mode for quick QA checks
   - Extract review text from response

3. **Response Parsing**:
   - Extract compliance status (Compliant/Needs Revision/Non-Compliant)
   - Parse completeness score (0-100%)
   - Identify missing or weak elements
   - Extract narrative strengths
   - Parse specific recommendations
   - Extract risk assessment
   - Identify required revisions

4. **Flagging Logic**:
   - Flag if status is "Needs Revision" or "Non-Compliant"
   - Flag if completeness score < 70%
   - Flag if required revisions exist
   - Flag if project confidence score < 0.7

**Input**:
- `narrative`: str - Generated narrative text to review
- `project`: QualifiedProject - Project data for context

**Output**: 
- Dictionary with compliance review results:
```python
{
    'compliance_status': 'Compliant',  # or 'Needs Revision', 'Non-Compliant'
    'completeness_score': 85,  # 0-100
    'missing_elements': ['Process of experimentation details'],
    'strengths': ['Clear technical uncertainties', 'Good IRS citations'],
    'recommendations': ['Add more detail on experimentation process'],
    'risk_assessment': 'Low risk of IRS challenge',
    'required_revisions': [],  # Empty if compliant
    'flagged_for_review': False,  # True if manual review needed
    'review_summary': 'Status: Compliant | Completeness: 85%',
    'raw_review': '...'  # Full review text
}
```

**Data Flow Between Methods**:
```
_review_narrative()
  ↓ Creates review prompt
  ↓ Calls You.com Express Agent API
  ↓ Receives review text
_parse_compliance_review()
  ↓ Parses structured data
  ↓ Returns review dictionary
```

**Error Handling**:
- Raises APIConnectionError if You.com Express Agent fails
- Validates narrative is not empty before review
- Provides detailed error context for debugging
- Logs all review failures with project context

**Performance**:
- Review time: ~2-3 seconds per narrative
- Total for 10 projects: ~20-30 seconds
### Stage 3: Data Aggregation

**Purpose**: Aggregate all qualified project data for final report generation using Pandas.

**Method**: `_aggregate_report_data()`

**Process**:
1. **Data Validation**:
   - Validate qualified_projects is not empty
   - Validate tax_year is reasonable (2000-2100)

2. **DataFrame Creation**:
   - Convert List[QualifiedProject] to Pandas DataFrame
   - Include columns: project_name, qualified_hours, qualified_cost, confidence_score, qualification_percentage, flagged_for_review, irs_source, reasoning_length, citation_length

3. **Core Calculations**:
   - **Total Qualified Hours**: Sum of all project hours
   - **Total Qualified Cost**: Sum of all project costs
   - **Estimated Credit**: 20% of total qualified cost (federal R&D tax credit rate)
   - **Average Confidence**: Mean confidence score across all projects

4. **Confidence Distribution**:
   - High confidence: confidence >= 0.8
   - Medium confidence: 0.7 <= confidence < 0.8
   - Low confidence: confidence < 0.7
   - Count projects in each category

5. **Summary Statistics**:
   - Min/max/median confidence scores
   - Standard deviation of confidence
   - Min/max/median qualified hours
   - Min/max/median qualified costs
   - Average/min/max qualification percentages

6. **Top Projects Analysis**:
   - Sort projects by qualified cost (descending)
   - Calculate cumulative cost percentages
   - Identify projects contributing to 80% of total cost
   - Useful for focusing audit defense efforts

7. **Risk Assessment**:
   - Count flagged projects
   - Calculate flagged percentage
   - Log warnings if >30% flagged or average confidence <75%

**Input**:
- `qualified_projects`: List[QualifiedProject] - Projects from Qualification Agent
- `tax_year`: int - Tax year for the report

**Output**: 
- Dictionary with aggregated data:
```python
{
    # Core totals
    'total_qualified_hours': 1250.5,
    'total_qualified_cost': 156250.00,
    'estimated_credit': 31250.00,  # 20% of qualified cost
    
    # Confidence metrics
    'average_confidence': 0.85,
    'high_confidence_count': 7,
    'medium_confidence_count': 2,
    'low_confidence_count': 1,
    
    # Project counts
    'project_count': 10,
    'flagged_count': 1,
    'top_projects_80_count': 6,
    
    # DataFrames for detailed reporting
    'projects_df': <Pandas DataFrame>,
    
    # Summary statistics
    'summary_stats': {
        'min_confidence': 0.65,
        'max_confidence': 0.95,
        'median_confidence': 0.87,
        'std_confidence': 0.08,
        'min_qualified_hours': 45.0,
        'max_qualified_hours': 250.0,
        'median_qualified_hours': 120.0,
        'min_qualified_cost': 5625.00,
        'max_qualified_cost': 31250.00,
        'median_qualified_cost': 15000.00,
        'avg_qualification_percentage': 82.5,
        'min_qualification_percentage': 65.0,
        'max_qualification_percentage': 95.0
    },
    
    # Metadata
    'tax_year': 2024,
    'aggregation_timestamp': '2024-10-30T14:30:00'
}
```

**Data Flow**:
```
qualified_projects (List)
  ↓ Convert to DataFrame
projects_df (Pandas DataFrame)
  ↓ Aggregate with Pandas operations
  ↓ Calculate totals, means, counts
  ↓ Sort and analyze
aggregated_data (Dictionary)
```

**Error Handling**:
- Raises ValueError if qualified_projects is empty
- Raises ValueError if tax_year is invalid
- Logs warnings if many projects flagged (>30%)
- Logs warnings if average confidence is low (<75%)

**Performance**:
- Aggregation time: <1 second for 100 projects
- Pandas operations are highly optimized
- DataFrame operations are vectorized

### Stage 4: PDF Report Generation

**Purpose**: Create professional PDF report with all sections and complete data.

**Method**: `run()` - orchestrates PDF generation via PDFGenerator

**Process**:
1. **Data Preparation**:
   - Verify all three dictionaries are populated:
     - narratives (from Stage 1)
     - compliance_reviews (from Stage 2)
     - aggregated_data (from Stage 3)
   - Run assertion checks to ensure data completeness

2. **AuditReport Creation**:
   - Create AuditReport object with complete data:
     - report_id, generation_date, tax_year
     - total_qualified_hours, total_qualified_cost, estimated_credit
     - projects list
     - **narratives dictionary** (added in Task 4)
     - **compliance_reviews dictionary** (added in Task 4)
     - **aggregated_data dictionary** (added in Task 4)
   - Add company_name if provided

3. **PDF Generation**:
   - Generate unique filename with timestamp
   - Call PDFGenerator.generate_report()
   - Pass complete AuditReport object
   - Specify output directory and filename
   - Update AuditReport.pdf_path with generated path

4. **Result Building**:
   - Create AuditTrailResult object
   - Include report, pdf_path, narratives, compliance_reviews
   - Calculate execution time
   - Generate comprehensive summary

**Input**:
- Complete data from all previous stages
- PDFGenerator instance (optional, can be None)

**Output**: 
- PDF file at specified path
- AuditReport object with pdf_path set
- AuditTrailResult with all data

**Data Flow**:
```
narratives (Dict) ────┐
compliance_reviews ───┼──> AuditReport object
aggregated_data ──────┘         ↓
                          PDFGenerator
                                ↓
                          PDF file
                                ↓
                          AuditTrailResult
```

**Error Handling**:
- Continues without PDF if PDFGenerator not provided
- Logs warning if PDF generation fails
- Audit data still available for manual PDF generation
- Raises exceptions for critical failures

**Performance**:
- PDF generation: ~10 seconds for 10 projects
- Total pipeline: ~60 seconds for 10 projects

## Expected Inputs and Outputs

### Main Method: `run()`

**Input Parameters**:
```python
def run(
    self,
    qualified_projects: List[QualifiedProject],  # Required
    tax_year: int,                                # Required
    company_name: Optional[str] = None            # Optional
) -> AuditTrailResult:
```

**Input Details**:
- `qualified_projects`: List of QualifiedProject objects from Qualification Agent
  - Each project must have: project_name, qualified_hours, qualified_cost, confidence_score, qualification_percentage, reasoning, irs_source, supporting_citation
  - Minimum 1 project required
  - Recommended: 5-20 projects for typical report

- `tax_year`: Integer representing the tax year
  - Must be between 2000 and 2100
  - Typically current year or previous year

- `company_name`: Optional company name for report header
  - Used in PDF cover page
  - If None, report will not include company name

**Output: AuditTrailResult**
```python
class AuditTrailResult(BaseModel):
    report: Optional[AuditReport]              # Complete audit report object
    pdf_path: Optional[str]                    # Path to generated PDF
    narratives: Dict[str, str]                 # Project name -> narrative text
    compliance_reviews: Dict[str, Dict]        # Project name -> review results
    execution_time_seconds: float              # Total execution time
    summary: str                               # Human-readable summary
    aggregated_data: Optional[Dict[str, Any]]  # Aggregated statistics
```

**Example AuditTrailResult**:
```python
AuditTrailResult(
    report=AuditReport(
        report_id="RD_TAX_2024_20241030_143000",
        generation_date=datetime(2024, 10, 30, 14, 30, 0),
        tax_year=2024,
        total_qualified_hours=1250.5,
        total_qualified_cost=156250.00,
        estimated_credit=31250.00,
        projects=[...],  # 10 QualifiedProject objects
        narratives={...},  # 10 narratives
        compliance_reviews={...},  # 10 reviews
        aggregated_data={...},  # Full aggregated data
        pdf_path="outputs/reports/rd_tax_credit_report_2024_20241030_143000.pdf"
    ),
    pdf_path="outputs/reports/rd_tax_credit_report_2024_20241030_143000.pdf",
    narratives={
        "API Optimization": "Technical narrative for API Optimization project...",
        "Database Migration": "Technical narrative for Database Migration project...",
        # ... 8 more narratives
    },
    compliance_reviews={
        "API Optimization": {
            'compliance_status': 'Compliant',
            'completeness_score': 85,
            'flagged_for_review': False,
            # ... more review data
        },
        # ... 9 more reviews
    },
    execution_time_seconds=58.3,
    summary="Generated 10 narratives for 10 projects in 58.30 seconds. Total qualified cost: $156,250.00, Estimated credit: $31,250.00, Average confidence: 85.00%. PDF report saved to: outputs/reports/rd_tax_credit_report_2024_20241030_143000.pdf",
    aggregated_data={
        'total_qualified_hours': 1250.5,
        'total_qualified_cost': 156250.00,
        'estimated_credit': 31250.00,
        # ... more aggregated data
    }
)
```

## Error Handling

### Exception Types

1. **ValueError**:
   - Raised when: Input validation fails
   - Examples:
     - Empty qualified_projects list
     - Invalid tax_year (< 2000 or > 2100)
     - Empty narrative text
   - Handling: Validate inputs before calling methods

2. **APIConnectionError**:
   - Raised when: External API calls fail
   - Examples:
     - You.com Agent API unavailable
     - You.com Express Agent API authentication fails
     - Network connectivity issues
   - Handling: 
     - Narrative generation: Falls back to local generation
     - Compliance review: Re-raises exception (no fallback)
     - Logged with detailed context

3. **Exception** (Generic):
   - Raised when: Unexpected errors occur
   - Examples:
     - PDF generation fails
     - Data parsing errors
     - File system issues
   - Handling: Logged with full stack trace, workflow continues where possible

### Error Recovery Strategies

**Narrative Generation**:
- Primary: You.com Agent API
- Fallback: Local generation from project data
- Guarantee: Always returns a narrative (minimum 500 chars)

**Compliance Review**:
- Primary: You.com Express Agent API
- Fallback: None (raises exception)
- Rationale: Compliance review is critical, no automated fallback

**PDF Generation**:
- Primary: PDFGenerator
- Fallback: Continue without PDF
- Rationale: Audit data is preserved, PDF can be regenerated

**Data Aggregation**:
- No fallback (critical operation)
- Raises exception on failure
- Rationale: Incorrect calculations would invalidate report

### Logging Strategy

**Log Levels**:
- **INFO**: Normal workflow progress, stage completions
- **DEBUG**: Detailed data (prompts, responses, intermediate values)
- **WARNING**: Non-critical issues (fallback usage, low confidence)
- **ERROR**: Failures that don't stop workflow (individual project failures)
- **CRITICAL**: Failures that stop workflow (empty inputs, API auth failures)

**Key Log Points**:
1. Workflow start: Project count, tax year
2. Each stage start/completion: Stage name, duration
3. Narrative generation: Success/fallback, length, project name
4. Compliance review: Status, completeness score, flagged status
5. Data aggregation: Totals, averages, warnings
6. PDF generation: File path, size, page count
7. Workflow completion: Summary, execution time

**Log Format**:
```
2024-10-30 14:30:00 [INFO] Starting audit trail generation for 10 projects (tax year: 2024)
2024-10-30 14:30:05 [INFO] Generated narrative 1/10 for project: API Optimization
2024-10-30 14:30:35 [INFO] Successfully generated 10 narratives (total API calls: 10)
2024-10-30 14:30:50 [INFO] Compliance review complete: 10 narratives reviewed
2024-10-30 14:30:51 [INFO] Data aggregation complete: Total hours: 1,250.50, Total cost: $156,250.00
2024-10-30 14:31:00 [INFO] Successfully generated PDF report: outputs/reports/rd_tax_credit_report_2024_20241030_143000.pdf
2024-10-30 14:31:00 [INFO] Audit trail generation workflow complete
```

## Usage Examples

### Basic Usage

```python
from agents.audit_trail_agent import AuditTrailAgent
from tools.you_com_client import YouComClient
from tools.glm_reasoner import GLMReasoner
from utils.pdf_generator import PDFGenerator

# Initialize tools
youcom_client = YouComClient(api_key="your_youcom_api_key")
glm_reasoner = GLMReasoner(api_key="your_openrouter_api_key")
pdf_generator = PDFGenerator()

# Initialize agent
agent = AuditTrailAgent(
    youcom_client=youcom_client,
    glm_reasoner=glm_reasoner,
    pdf_generator=pdf_generator
)

# Run audit trail generation
result = agent.run(
    qualified_projects=qualified_projects,  # From Qualification Agent
    tax_year=2024,
    company_name="Acme Corporation"
)

# Access results
print(f"Generated report: {result.pdf_path}")
print(f"Total credit: ${result.report.estimated_credit:,.2f}")
print(f"Execution time: {result.execution_time_seconds:.2f} seconds")
print(f"Summary: {result.summary}")
```

### With Status Updates

```python
from models.websocket_models import StatusUpdateMessage

def status_callback(message: StatusUpdateMessage):
    """Handle status updates for frontend display."""
    print(f"[{message.stage.value}] {message.status.value}: {message.details}")

# Initialize agent with callback
agent = AuditTrailAgent(
    youcom_client=youcom_client,
    glm_reasoner=glm_reasoner,
    pdf_generator=pdf_generator,
    status_callback=status_callback
)

# Run with real-time status updates
result = agent.run(
    qualified_projects=qualified_projects,
    tax_year=2024
)
```

### Without PDF Generator

```python
# Initialize agent without PDF generator
agent = AuditTrailAgent(
    youcom_client=youcom_client,
    glm_reasoner=glm_reasoner,
    pdf_generator=None  # PDF generation will be skipped
)

# Run audit trail generation
result = agent.run(
    qualified_projects=qualified_projects,
    tax_year=2024
)

# Access narratives and reviews without PDF
for project_name, narrative in result.narratives.items():
    review = result.compliance_reviews[project_name]
    print(f"\n{project_name}:")
    print(f"  Narrative length: {len(narrative)} chars")
    print(f"  Compliance: {review['compliance_status']}")
    print(f"  Completeness: {review['completeness_score']}%")
```

### Error Handling Example

```python
from utils.exceptions import APIConnectionError

try:
    result = agent.run(
        qualified_projects=qualified_projects,
        tax_year=2024
    )
    print(f"Success: {result.pdf_path}")
    
except ValueError as e:
    print(f"Input validation error: {e}")
    # Handle invalid inputs
    
except APIConnectionError as e:
    print(f"API connection failed: {e.message}")
    print(f"API: {e.api_name}")
    print(f"Endpoint: {e.endpoint}")
    # Handle API failures
    
except Exception as e:
    print(f"Unexpected error: {e}")
    # Handle other errors
```

### Accessing Detailed Results

```python
result = agent.run(qualified_projects=qualified_projects, tax_year=2024)

# Access narratives
for project_name, narrative in result.narratives.items():
    print(f"\n=== {project_name} ===")
    print(narrative[:200] + "...")  # First 200 chars

# Access compliance reviews
for project_name, review in result.compliance_reviews.items():
    if review['flagged_for_review']:
        print(f"\n⚠️  {project_name} flagged for review:")
        print(f"  Status: {review['compliance_status']}")
        print(f"  Completeness: {review['completeness_score']}%")
        print(f"  Required revisions: {len(review['required_revisions'])}")

# Access aggregated data
agg = result.aggregated_data
print(f"\n=== Aggregated Data ===")
print(f"Total Projects: {agg['project_count']}")
print(f"Total Hours: {agg['total_qualified_hours']:,.2f}")
print(f"Total Cost: ${agg['total_qualified_cost']:,.2f}")
print(f"Estimated Credit: ${agg['estimated_credit']:,.2f}")
print(f"Average Confidence: {agg['average_confidence']:.2%}")
print(f"High Confidence Projects: {agg['high_confidence_count']}")
print(f"Flagged Projects: {agg['flagged_count']}")
```

## Performance Metrics

### Typical Execution Times

| Projects | Narrative Gen | Compliance Review | Aggregation | PDF Gen | Total  |
|----------|---------------|-------------------|-------------|---------|--------|
| 1        | 6s            | 3s                | <1s         | 5s      | ~15s   |
| 5        | 15s           | 12s               | <1s         | 7s      | ~35s   |
| 10       | 30s           | 20s               | <1s         | 10s     | ~60s   |
| 20       | 60s           | 40s               | <1s         | 15s     | ~120s  |
| 50       | 150s          | 100s              | 1s          | 30s     | ~280s  |

### Optimization Strategies

1. **Concurrent Processing**:
   - Narratives generated concurrently (max 5)
   - Reduces narrative generation time by ~50%
   - Respects You.com API rate limits

2. **Caching** (Future Enhancement):
   - Cache narrative templates
   - Cache API responses for identical prompts
   - Could reduce repeat generation time by 80%

3. **Batch Operations**:
   - Pandas operations are vectorized
   - DataFrame aggregation is highly optimized
   - Aggregation time scales linearly

4. **PDF Optimization**:
   - Pre-calculate table dimensions
   - Cache style objects
   - Use efficient string formatting

## Requirements Traceability

This agent implements the following requirements from the specification:

- **Requirement 4.1**: Generate technical narratives using You.com Agent API
- **Requirement 4.2**: Validate narratives meet minimum length (>500 chars)
- **Requirement 4.3**: Review narratives for compliance using You.com Express Agent
- **Requirement 4.4**: Aggregate data and create complete AuditReport
- **Requirement 4.5**: Generate professional PDF reports
- **Requirement 6.3**: Flag narratives for manual review based on compliance
- **Requirement 8.1**: Maintain audit trail throughout workflow
- **Requirement 8.5**: Log all data flow between stages

## Troubleshooting

### Common Issues

**Issue**: Narratives are too short (<500 chars)
- **Cause**: You.com API returned insufficient content
- **Solution**: Fallback narrative is automatically generated
- **Prevention**: Check You.com API status, verify API key

**Issue**: Many projects flagged for review (>30%)
- **Cause**: Low confidence scores or incomplete narratives
- **Solution**: Review qualification criteria, improve project data quality
- **Prevention**: Ensure Qualification Agent has sufficient data

**Issue**: PDF generation fails
- **Cause**: Missing PDFGenerator, file system permissions, invalid data
- **Solution**: Check PDFGenerator initialization, verify output directory exists
- **Prevention**: Initialize agent with PDFGenerator, ensure write permissions

**Issue**: API connection errors
- **Cause**: Invalid API keys, network issues, rate limiting
- **Solution**: Verify API keys in .env file, check network connectivity
- **Prevention**: Use valid API keys, respect rate limits

**Issue**: Low average confidence (<75%)
- **Cause**: Insufficient project data, weak qualification reasoning
- **Solution**: Improve data quality, add more technical details
- **Prevention**: Ensure Data Ingestion Agent captures complete data

### Debug Mode

Enable detailed logging for troubleshooting:

```python
import logging

# Set audit trail logger to DEBUG level
logger = logging.getLogger('audit_trail')
logger.setLevel(logging.DEBUG)

# Add console handler
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Run agent with debug logging
result = agent.run(qualified_projects=qualified_projects, tax_year=2024)
```

## Related Documentation

- **PDFGenerator**: `utils/PDF_GENERATOR_README.md`
- **YouComClient**: `tools/you_com_client.py` docstrings
- **GLMReasoner**: `tools/GLM_REASONER_README.md`
- **QualifiedProject Model**: `models/TAX_MODELS_README.md`
- **AuditReport Model**: `models/TAX_MODELS_README.md`
- **Qualification Agent**: `agents/qualification_agent.py` docstrings

## Version History

- **v1.0** (2024-10-15): Initial implementation with basic workflow
- **v1.1** (2024-10-20): Added concurrent narrative generation
- **v1.2** (2024-10-25): Added compliance review stage
- **v1.3** (2024-10-30): Enhanced documentation with complete workflow details

---

**Last Updated**: October 30, 2025  
**Maintained By**: R&D Tax Credit Automation Team  
**Requirements**: Documentation (Task 20)
