"""
AI-powered fixture enrichment using GLM 4.5 AIR.
This script uses LLM to generate realistic, schema-aware mock data
that looks authentic and can be used as templates in the frontend.
"""

import json
from pathlib import Path
from openai import OpenAI
import sys

# API Configuration
OPENROUTER_API_KEY = "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"
FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"


def create_ai_client():
    """Create OpenRouter AI client."""
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )


def generate_clockify_projects(client, workspace_id, num_projects=5):
    """Generate realistic R&D projects using AI."""
    print(f"\nGenerating {num_projects} AI-powered Clockify projects...")
    
    prompt = f"""Generate {num_projects} realistic R&D software development projects for a tech company.
Each project should be eligible for R&D tax credits and include:
- Unique project ID (format: proj_<short_name>_<number>)
- Project name (creative, tech-focused)
- Detailed note explaining the R&D nature and technical challenges
- Estimated hours (between 40-200 hours)
- Color hex code

Return ONLY valid JSON array with this exact structure:
[
  {{
    "id": "proj_example_001",
    "name": "Project Name",
    "hourlyRate": {{"amount": 15000, "currency": "USD"}},
    "clientId": null,
    "workspaceId": "{workspace_id}",
    "billable": true,
    "memberships": [],
    "color": "#03A9F4",
    "estimate": {{"estimate": "PT80H", "type": "AUTO"}},
    "archived": false,
    "duration": "PT0H",
    "clientName": "",
    "note": "Detailed R&D description with technical challenges",
    "costRate": null,
    "timeEstimate": {{"estimate": 288000, "type": "AUTO", "resetOption": null}},
    "budgetEstimate": null,
    "public": true
  }}
]

Focus on diverse R&D areas: ML/AI, cloud infrastructure, security, APIs, data processing, etc."""

    try:
        completion = client.chat.completions.create(
            model="z-ai/glm-4.5-air:free",
            extra_headers={
                "HTTP-Referer": "https://rd-tax-credit-agent.local",
                "X-Title": "R&D Tax Credit Automation Agent"
            },
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = completion.choices[0].message.content.strip()
        
        # Extract JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        projects = json.loads(response_text)
        print(f"✓ Generated {len(projects)} AI-powered projects")
        return projects
    except Exception as e:
        print(f"✗ Error generating projects: {e}")
        return []


def generate_time_entries(client, projects, user_id, workspace_id, num_entries=50):
    """Generate realistic time entries using AI."""
    print(f"\nGenerating {num_entries} AI-powered time entries...")
    
    project_list = "\n".join([f"- {p['id']}: {p['name']}" for p in projects[:5]])
    
    prompt = f"""Generate {num_entries} realistic time entry descriptions for R&D software development work.
These are for R&D tax credit qualification, so they must describe qualified research activities.

Available projects:
{project_list}

Each entry should:
- Be 10-30 words describing specific technical work
- Include technical details (algorithms, architectures, experiments, optimization)
- Show problem-solving and uncertainty resolution
- Vary in activity type (coding, testing, research, design, debugging)
- Sound authentic and professional

Return ONLY a JSON array of strings (descriptions only):
["description 1", "description 2", ...]

Examples:
- "Implemented and tested 3 different caching strategies to optimize API response time under high load"
- "Debugged memory leak in ML model training pipeline; experimented with batch size optimization"
- "Researched and prototyped WebSocket architecture for real-time data synchronization"
"""

    try:
        completion = client.chat.completions.create(
            model="z-ai/glm-4.5-air:free",
            extra_headers={
                "HTTP-Referer": "https://rd-tax-credit-agent.local",
                "X-Title": "R&D Tax Credit Automation Agent"
            },
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = completion.choices[0].message.content.strip()
        
        # Extract JSON from response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        descriptions = json.loads(response_text)
        print(f"✓ Generated {len(descriptions)} AI-powered time entry descriptions")
        
        # Create full time entries with the AI descriptions
        from datetime import datetime, timedelta
        import random
        
        entries = []
        base_date = datetime.now() - timedelta(days=60)
        
        for i, description in enumerate(descriptions[:num_entries]):
            # Random date in the past 60 days (weekdays only)
            day_offset = random.randint(0, 59)
            entry_date = base_date + timedelta(days=day_offset)
            while entry_date.weekday() >= 5:  # Skip weekends
                day_offset = random.randint(0, 59)
                entry_date = base_date + timedelta(days=day_offset)
            
            # Random project
            project = random.choice(projects)
            
            # Random hours (4-9 hours)
            hours = random.randint(4, 9)
            
            start_time = entry_date.replace(hour=9, minute=0, second=0)
            end_time = start_time + timedelta(hours=hours)
            
            entry = {
                "id": f"time_entry_ai_{i+1:04d}",
                "description": description,
                "tagIds": ["tag_rd_qualified"],
                "userId": user_id,
                "billable": True,
                "taskId": None,
                "projectId": project["id"],
                "timeInterval": {
                    "start": start_time.isoformat() + "Z",
                    "end": end_time.isoformat() + "Z",
                    "duration": f"PT{hours}H"
                },
                "workspaceId": workspace_id,
                "isLocked": False
            }
            entries.append(entry)
        
        return entries
    except Exception as e:
        print(f"✗ Error generating time entries: {e}")
        return []


def generate_employee_profiles(client, num_employees=10):
    """Generate realistic employee profiles using AI."""
    print(f"\nGenerating {num_employees} AI-powered employee profiles...")
    
    prompt = f"""Generate {num_employees} realistic employee profiles for a tech company's R&D team.
Include diverse roles, names, and backgrounds.

Return ONLY valid JSON array with this structure:
[
  {{
    "id": "emp_unique_id",
    "name": "Full Name",
    "first_name": "First",
    "last_name": "Last",
    "title": "Job Title",
    "department": "Engineering/R&D",
    "emails": [{{"email": "email@company.com", "type": "WORK"}}],
    "telephones": [{{"telephone": "(555) 123-4567", "type": "WORK"}}],
    "hire_date": "2023-01-15",
    "employment_type": "FULL_TIME",
    "annual_salary": 95000,
    "rd_percentage": 0.75,
    "skills": ["Python", "Machine Learning", "AWS"],
    "bio": "Brief professional background"
  }}
]

Make names diverse (various ethnicities, genders). Salaries: $75k-$150k. R&D percentage: 60-90%.
Job titles: Software Engineer, Data Scientist, ML Engineer, DevOps Engineer, etc."""

    try:
        completion = client.chat.completions.create(
            model="z-ai/glm-4.5-air:free",
            extra_headers={
                "HTTP-Referer": "https://rd-tax-credit-agent.local",
                "X-Title": "R&D Tax Credit Automation Agent"
            },
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = completion.choices[0].message.content.strip()
        
        # Extract JSON from response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        employees = json.loads(response_text)
        print(f"✓ Generated {len(employees)} AI-powered employee profiles")
        return employees
    except Exception as e:
        print(f"✗ Error generating employees: {e}")
        return []


def generate_project_templates(client, num_templates=10):
    """Generate project templates for frontend selection."""
    print(f"\nGenerating {num_templates} project templates for frontend...")
    
    prompt = f"""Generate {num_templates} diverse R&D project templates that users can select in a frontend UI.
Each should represent a different type of R&D work eligible for tax credits.

Return ONLY valid JSON array:
[
  {{
    "template_id": "template_ml_model",
    "category": "Machine Learning",
    "name": "ML Model Development",
    "description": "Development of machine learning models with experimentation",
    "typical_activities": [
      "Algorithm selection and testing",
      "Hyperparameter tuning",
      "Model validation and optimization"
    ],
    "technical_challenges": [
      "Achieving target accuracy",
      "Reducing training time",
      "Handling imbalanced data"
    ],
    "estimated_hours": 120,
    "rd_qualification_score": 0.95,
    "example_deliverables": [
      "Trained model with >85% accuracy",
      "Performance benchmarks",
      "Technical documentation"
    ]
  }}
]

Categories: ML/AI, Cloud Infrastructure, Security, APIs, Data Processing, DevOps, Frontend, Backend, Mobile, IoT"""

    try:
        completion = client.chat.completions.create(
            model="z-ai/glm-4.5-air:free",
            extra_headers={
                "HTTP-Referer": "https://rd-tax-credit-agent.local",
                "X-Title": "R&D Tax Credit Automation Agent"
            },
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = completion.choices[0].message.content.strip()
        
        # Extract JSON from response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        templates = json.loads(response_text)
        print(f"✓ Generated {len(templates)} project templates")
        return templates
    except Exception as e:
        print(f"✗ Error generating templates: {e}")
        return []


def ai_enrich_clockify():
    """AI-powered enrichment of Clockify fixtures."""
    print("\n" + "=" * 60)
    print("AI-Powered Clockify Enrichment")
    print("=" * 60)
    
    client = create_ai_client()
    
    # Load existing fixture
    fixture_path = FIXTURES_DIR / "clockify_responses.json"
    with open(fixture_path) as f:
        data = json.load(f)
    
    workspace_id = data["workspace"]["id"]
    user_id = data["users"][0]["id"] if data["users"] else "sample_user_id"
    
    # Generate AI-powered projects
    ai_projects = generate_clockify_projects(client, workspace_id, num_projects=5)
    if ai_projects:
        # Merge with existing projects
        existing_project_ids = {p["id"] for p in data.get("projects", [])}
        new_projects = [p for p in ai_projects if p["id"] not in existing_project_ids]
        data["projects"] = data.get("projects", []) + new_projects
    
    # Generate AI-powered time entries
    if data.get("projects"):
        ai_entries = generate_time_entries(client, data["projects"], user_id, workspace_id, num_entries=50)
        if ai_entries:
            data["time_entries"] = data.get("time_entries", []) + ai_entries
    
    # Save enriched data
    with open(fixture_path, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"\n✓ Saved AI-enriched Clockify fixtures")
    print(f"  Total projects: {len(data.get('projects', []))}")
    print(f"  Total time entries: {len(data.get('time_entries', []))}")


def ai_enrich_unified_to():
    """AI-powered enrichment of Unified.to fixtures."""
    print("\n" + "=" * 60)
    print("AI-Powered Unified.to Enrichment")
    print("=" * 60)
    
    client = create_ai_client()
    
    # Load existing fixture
    fixture_path = FIXTURES_DIR / "unified_to_responses.json"
    with open(fixture_path) as f:
        data = json.load(f)
    
    # Generate AI-powered employee profiles
    ai_employees = generate_employee_profiles(client, num_employees=10)
    if ai_employees:
        # Add to existing employees
        data["ai_generated_employees"] = ai_employees
    
    # Save enriched data
    with open(fixture_path, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"\n✓ Saved AI-enriched Unified.to fixtures")
    print(f"  Real employees: {len(data.get('employees', []))}")
    print(f"  AI employees: {len(data.get('ai_generated_employees', []))}")


def generate_frontend_templates():
    """Generate project templates for frontend selection."""
    print("\n" + "=" * 60)
    print("Generating Frontend Project Templates")
    print("=" * 60)
    
    client = create_ai_client()
    
    # Generate templates
    templates = generate_project_templates(client, num_templates=10)
    
    if templates:
        # Save as separate fixture file
        template_path = FIXTURES_DIR / "project_templates.json"
        template_data = {
            "templates": templates,
            "metadata": {
                "generated_by": "AI (GLM 4.5 AIR)",
                "purpose": "Frontend project selection templates",
                "usage": "Users can select these templates when creating new R&D projects"
            }
        }
        
        with open(template_path, "w") as f:
            json.dump(template_data, f, indent=2)
        
        print(f"\n✓ Saved {len(templates)} project templates")
        print(f"  Location: {template_path}")


def main():
    """Main function for AI-powered enrichment."""
    print("=" * 60)
    print("AI-Powered Fixture Enrichment (GLM 4.5 AIR)")
    print("=" * 60)
    print("\nThis will generate realistic, diverse mock data using AI")
    print("Perfect for frontend templates and realistic testing scenarios")
    
    try:
        # Enrich Clockify with AI
        ai_enrich_clockify()
        
        # Enrich Unified.to with AI
        ai_enrich_unified_to()
        
        # Generate frontend templates
        generate_frontend_templates()
        
        print("\n" + "=" * 60)
        print("✓ AI-Powered Enrichment Complete!")
        print("=" * 60)
        print("\nGenerated:")
        print("  • 5 AI-generated R&D projects")
        print("  • 50 AI-generated time entries with realistic descriptions")
        print("  • 10 AI-generated employee profiles")
        print("  • 10 project templates for frontend selection")
        print("\nThese fixtures are ready for:")
        print("  • Frontend template selection")
        print("  • Realistic demo scenarios")
        print("  • Comprehensive testing")
        
    except Exception as e:
        print(f"\n✗ Error during AI enrichment: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
