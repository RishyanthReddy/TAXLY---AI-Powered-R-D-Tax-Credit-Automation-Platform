# Fixture Generation Scripts

This directory contains scripts for generating and enriching test fixtures using real API calls.

## Scripts

### 1. generate_fixtures.py (Real API Data)

**Purpose**: Fetch real API responses and generate test fixtures

**What it does**:
- Connects to Clockify API to fetch workspace, users, projects, and time entries
- Connects to Unified.to API to fetch candidates and employees
- Connects to OpenRouter API to generate LLM responses for R&D analysis
- Saves all responses as JSON fixtures
- Automatically runs enrichment script to add sample data

**Usage**:
```bash
python scripts/generate_fixtures.py
```

**Requirements**:
- Valid API keys in `.env` file:
  - `CLOCKIFY_API_KEY`
  - `UNIFIED_TO_API_KEY`
  - `OPENROUTER_API_KEY`
- Internet connection
- Python packages: `requests`, `openai`

**Output**:
- `tests/fixtures/clockify_responses.json`
- `tests/fixtures/unified_to_responses.json`
- `tests/fixtures/openrouter_responses.json`

### 2. enrich_fixtures.py (Rule-Based Enrichment)

**Purpose**: Enrich real API responses with realistic sample data

**What it does**:
- Detects empty arrays in API responses
- Adds realistic sample data matching real API schemas
- Generates R&D-specific project descriptions
- Creates time entries with qualified research activities
- Generates payslip data with wage calculations
- Adds metadata about generation and enrichment

**Usage**:
```bash
python scripts/enrich_fixtures.py
```

**Enrichment Details**:

#### Clockify Enrichment
- **Projects**: Adds 3 R&D projects
  - ML Model Development
  - Cloud Infrastructure Optimization
  - API Integration Framework
- **Time Entries**: Adds 30+ entries with:
  - R&D activity descriptions
  - Realistic time allocations (5-8 hours)
  - Weekday-only entries
  - Links to enriched projects

#### Unified.to Enrichment
- **Payslips**: Adds quarterly payslips for employees
  - Realistic salary calculations ($85k-$115k range)
  - Tax deductions (federal, state, social security, medicare)
  - R&D time allocation percentages (70-80%)
  - Proper date ranges and pay periods

#### Metadata
- Generation timestamp
- Source information
- Enrichment version
- Usage notes

**Output**:
- Updates existing fixture files in place
- Adds `_metadata` field to each fixture

---

### 3. ai_enrich_fixtures.py (AI-Powered Enrichment)

**Purpose**: Use AI (GLM 4.5 AIR) to generate realistic, diverse mock data

**What it does**:
- Generates realistic R&D project descriptions using AI
- Creates diverse time entry descriptions with technical details
- Generates employee profiles with varied backgrounds
- Creates project templates for frontend selection
- Produces schema-aware, realistic mock data

**Usage**:
```bash
python scripts/ai_enrich_fixtures.py
```

**Requirements**:
- Valid `OPENROUTER_API_KEY` in `.env` file
- Internet connection
- Python packages: `openai`, `requests`

**AI-Generated Content**:

#### Projects (5 generated)
- Creative, tech-focused names
- Detailed R&D descriptions with technical challenges
- Diverse categories (ML, Cloud, Security, APIs, etc.)
- Realistic hour estimates

#### Time Entries (50 generated)
- Authentic technical descriptions
- Varied activities (coding, testing, research, debugging)
- R&D-qualified language
- Professional tone

#### Employee Profiles (10 generated)
- Diverse names and backgrounds
- Realistic job titles and salaries
- R&D time allocation percentages
- Skills and professional bios

#### Project Templates (10 generated)
- Frontend-ready templates
- Category-organized
- R&D qualification scores
- Typical activities and challenges
- Example deliverables

**Output**:
- `tests/fixtures/clockify_responses.json` (enriched with AI projects and entries)
- `tests/fixtures/unified_to_responses.json` (enriched with AI employees)
- `tests/fixtures/project_templates.json` (NEW - frontend templates)

**Benefits**:
- **Realistic**: AI generates human-like, professional content
- **Diverse**: Wide variety of projects, activities, and profiles
- **Schema-aware**: Matches real API structures perfectly
- **Frontend-ready**: Templates can be used directly in UI
- **Testing-friendly**: Comprehensive data for all test scenarios

## Workflow

### Complete Fixture Generation (Recommended)

For the most realistic, diverse fixtures:

```bash
# Step 1: Generate fixtures from real APIs
python scripts/generate_fixtures.py

# Step 2: Add AI-powered enrichment
python scripts/ai_enrich_fixtures.py
```

This will:
1. Fetch real API responses
2. Add rule-based sample data
3. Generate AI-powered realistic content
4. Create frontend templates
5. Add metadata

### Quick Fixture Generation

For basic fixtures without AI:

```bash
# Generate fixtures from real APIs (includes auto-enrichment)
python scripts/generate_fixtures.py
```

This will:
1. Fetch real API responses
2. Save raw responses as JSON
3. Automatically enrich with sample data
4. Add metadata

### Manual Enrichment Only

If you already have fixtures and just want to enrich them:

```bash
# Rule-based enrichment
python scripts/enrich_fixtures.py

# OR AI-powered enrichment (more realistic)
python scripts/ai_enrich_fixtures.py
```

### Comparison: Rule-Based vs AI Enrichment

| Feature | Rule-Based | AI-Powered |
|---------|-----------|------------|
| **Speed** | Fast (~1 second) | Moderate (~30 seconds) |
| **Realism** | Good | Excellent |
| **Diversity** | Limited patterns | High variety |
| **Creativity** | Predictable | Creative names/descriptions |
| **Cost** | Free | Free (with rate limits) |
| **Use Case** | Quick testing | Frontend demos, realistic scenarios |

**Recommendation**: Use both! Run rule-based first for structure, then AI for realism.

### Verification

Run tests to verify fixtures are valid:

```bash
pytest tests/test_fixtures.py -v
```

## API Configuration

### Clockify API

**Base URL**: `https://api.clockify.me/api/v1`

**Authentication**: API key in header `X-Api-Key`

**Endpoints Used**:
- `GET /workspaces` - List workspaces
- `GET /workspaces/{id}` - Get workspace details
- `GET /workspaces/{id}/users` - List users
- `GET /workspaces/{id}/projects` - List projects
- `GET /workspaces/{id}/user/{userId}/time-entries` - List time entries

**Rate Limits**: Free tier allows reasonable usage for testing

### Unified.to API

**Base URL**: `https://api.unified.to`

**Authentication**: JWT token in header `authorization`

**Endpoints Used**:
- `GET /ats/{workspaceId}/candidate` - List candidates
- `GET /hris/{workspaceId}/employee` - List employees
- `GET /hris/{workspaceId}/payslip` - List payslips (not implemented by provider)

**Rate Limits**: Varies by plan

### OpenRouter API

**Base URL**: `https://openrouter.ai/api/v1`

**Authentication**: API key as Bearer token

**Model Used**: `z-ai/glm-4.5-air:free`

**Endpoints Used**:
- `POST /chat/completions` - Generate LLM responses

**Rate Limits**: Free tier has rate limits; script handles errors gracefully

## Troubleshooting

### API Authentication Errors

**Problem**: 401 Unauthorized or 403 Forbidden

**Solution**:
1. Verify API keys in `.env` are correct
2. Check API key permissions and scopes
3. Ensure workspace IDs are valid
4. Test API keys manually with curl

### Empty Data from APIs

**Problem**: APIs return empty arrays for projects/time entries

**Solution**:
- This is expected for new/test workspaces
- The enrichment script automatically adds sample data
- No action needed - enrichment handles this

### Rate Limit Errors

**Problem**: 429 Too Many Requests

**Solution**:
1. Wait a few minutes before retrying
2. For OpenRouter, try different free models
3. Use cached fixtures for development
4. Consider upgrading API plan for production

### Network Errors

**Problem**: Connection timeouts or DNS errors

**Solution**:
1. Check internet connection
2. Verify firewall/proxy settings
3. Try again later if API is down
4. Use cached fixtures as fallback

## Best Practices

### When to Regenerate Fixtures

Regenerate fixtures when:
- API response structures change
- New API endpoints are added
- Testing new LLM prompt variations
- Updating to new API versions
- Need fresh sample data

### When to Enrich Only

Run enrichment only when:
- You have valid fixtures but need more sample data
- Testing different data scenarios
- API rate limits prevent full regeneration
- Experimenting with fixture content

### Version Control

**Commit fixtures to git**:
- Fixtures are essential for tests
- Other developers need consistent test data
- CI/CD pipelines require fixtures

**Don't commit**:
- API keys (use `.env` file)
- Personal data from production APIs
- Temporary test files

### Data Privacy

**Safe to commit**:
- Sandbox/test API responses
- Synthetic data from enrichment
- LLM-generated examples

**Never commit**:
- Production customer data
- Real employee information
- Sensitive business data

## Examples

### Generate Fresh Fixtures

```bash
# Full regeneration with enrichment
python scripts/generate_fixtures.py

# Output:
# ============================================================
# Generating Test Fixtures from Real API Calls
# ============================================================
# Fetching Clockify workspace ID...
# ✓ Found workspace: InsightPro (ID: 69002f0cfa72440e4ca0cf35)
# ...
# ✓ All fixtures generated successfully!
```

### Enrich Existing Fixtures

```bash
# Add sample data to existing fixtures
python scripts/enrich_fixtures.py

# Output:
# ============================================================
# Enriching Test Fixtures with Sample Data
# ============================================================
# Enriching Clockify fixtures...
# ✓ Added 3 sample projects
# ✓ Added 33 sample time entries
# ...
```

### Verify Fixtures

```bash
# Run fixture validation tests
pytest tests/test_fixtures.py -v

# Output:
# tests/test_fixtures.py::TestClockifyFixtures::test_workspace_exists PASSED
# tests/test_fixtures.py::TestClockifyFixtures::test_projects_enriched PASSED
# ...
# ======================== 16 passed in 0.17s =========================
```

## Related Documentation

- [Test Fixtures README](../tests/fixtures/README.md) - Fixture usage guide
- [Testing Guide](../tests/README.md) - General testing documentation
- [Environment Setup](../.env.example) - API key configuration

## Maintenance

### Script Updates

When updating scripts:
1. Test with real API calls
2. Verify enrichment logic
3. Update tests if schema changes
4. Document new features in this README

### Adding New APIs

To add a new API source:
1. Add fetch function to `generate_fixtures.py`
2. Add enrichment function to `enrich_fixtures.py`
3. Create fixture file in `tests/fixtures/`
4. Add tests to `tests/test_fixtures.py`
5. Update documentation

### Schema Changes

When API schemas change:
1. Regenerate fixtures to get new structure
2. Update enrichment logic if needed
3. Update tests to match new schema
4. Document breaking changes
