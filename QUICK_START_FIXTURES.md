# Quick Start: Fixture Generation

## TL;DR

```bash
# Generate everything (recommended)
python scripts/generate_fixtures.py
python scripts/ai_enrich_fixtures.py

# Verify
pytest tests/test_fixtures.py -v
```

## What You Get

### Real API Data
- ✅ Clockify workspace, users, projects, time entries
- ✅ Unified.to candidates, employees, payslips
- ✅ OpenRouter LLM analysis (qualification, audit, compliance)

### Rule-Based Enrichment
- ✅ 3 R&D projects
- ✅ 33 time entries
- ✅ 9 payslips

### AI-Powered Enrichment
- ✅ 5 creative R&D projects
- ✅ 50 diverse time entries
- ✅ 10 employee profiles
- ✅ 10 project templates for frontend

## Commands

### Generate All Fixtures
```bash
# Step 1: Real API + rule-based
python scripts/generate_fixtures.py

# Step 2: AI enrichment (optional but recommended)
python scripts/ai_enrich_fixtures.py
```

### Verify Fixtures
```bash
# Run tests
pytest tests/test_fixtures.py -v

# Check file sizes
ls -lh tests/fixtures/*.json
```

### View Fixtures
```bash
# Pretty print
python -m json.tool tests/fixtures/project_templates.json

# Count entries
python -c "import json; print(len(json.load(open('tests/fixtures/clockify_responses.json'))['time_entries']))"
```

## File Locations

```
tests/fixtures/
├── clockify_responses.json      # Time tracking data
├── unified_to_responses.json    # HRIS/ATS data
├── openrouter_responses.json    # LLM analysis
└── project_templates.json       # Frontend templates (NEW!)
```

## Frontend Usage

```javascript
// Load templates
import templates from './fixtures/project_templates.json';

// Use in UI
const projectTemplates = templates.templates;
```

## Testing Usage

```python
import json

# Load fixture
with open('tests/fixtures/project_templates.json') as f:
    data = json.load(f)

# Use in test
templates = data['templates']
assert len(templates) == 10
```

## Troubleshooting

### API Errors
```bash
# Check API keys
cat .env | grep API_KEY

# Test connection
curl -H "X-Api-Key: YOUR_KEY" https://api.clockify.me/api/v1/workspaces
```

### Empty Data
```bash
# Run enrichment
python scripts/enrich_fixtures.py

# Or AI enrichment
python scripts/ai_enrich_fixtures.py
```

### Test Failures
```bash
# Regenerate fixtures
python scripts/generate_fixtures.py

# Run tests again
pytest tests/test_fixtures.py -v
```

## Next Steps

1. ✅ Generate fixtures
2. ✅ Run tests
3. ✅ Review templates
4. ✅ Integrate with frontend
5. ✅ Start building features

## Documentation

- **Full Guide**: [FIXTURE_GENERATION_SUMMARY.md](FIXTURE_GENERATION_SUMMARY.md)
- **Templates**: [tests/fixtures/TEMPLATES_GUIDE.md](tests/fixtures/TEMPLATES_GUIDE.md)
- **Scripts**: [scripts/README.md](scripts/README.md)
- **Testing**: [tests/README.md](tests/README.md)

## Support

Questions? Check:
1. Documentation files above
2. Test examples in `tests/test_fixtures.py`
3. Script code in `scripts/`
