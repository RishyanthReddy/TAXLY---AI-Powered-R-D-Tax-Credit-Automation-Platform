"""
Script to enrich test fixtures with realistic sample data.
This script takes the real API responses and adds sample data to empty arrays
to make fixtures more useful for testing.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
import random

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"


def enrich_clockify_fixtures():
    """Enrich Clockify fixtures with sample projects and time entries."""
    print("\nEnriching Clockify fixtures...")
    
    fixture_path = FIXTURES_DIR / "clockify_responses.json"
    with open(fixture_path) as f:
        data = json.load(f)
    
    workspace_id = data["workspace"]["id"]
    user_id = data["users"][0]["id"] if data["users"] else "sample_user_id"
    
    # Add sample projects if empty
    if not data.get("projects") or len(data["projects"]) == 0:
        data["projects"] = [
            {
                "id": "proj_ml_model_dev_001",
                "name": "ML Model Development",
                "hourlyRate": {"amount": 15000, "currency": "USD"},
                "clientId": None,
                "workspaceId": workspace_id,
                "billable": True,
                "memberships": [],
                "color": "#03A9F4",
                "estimate": {"estimate": "PT40H", "type": "AUTO"},
                "archived": False,
                "duration": "PT120H30M",
                "clientName": "",
                "note": "R&D project for developing machine learning algorithms for customer churn prediction",
                "costRate": None,
                "timeEstimate": {"estimate": 144000, "type": "AUTO", "resetOption": None},
                "budgetEstimate": None,
                "public": True
            },
            {
                "id": "proj_cloud_infra_002",
                "name": "Cloud Infrastructure Optimization",
                "hourlyRate": {"amount": 15000, "currency": "USD"},
                "clientId": None,
                "workspaceId": workspace_id,
                "billable": True,
                "memberships": [],
                "color": "#4CAF50",
                "estimate": {"estimate": "PT60H", "type": "AUTO"},
                "archived": False,
                "duration": "PT85H15M",
                "clientName": "",
                "note": "R&D project for optimizing cloud architecture and reducing latency",
                "costRate": None,
                "timeEstimate": {"estimate": 216000, "type": "AUTO", "resetOption": None},
                "budgetEstimate": None,
                "public": True
            },
            {
                "id": "proj_api_integration_003",
                "name": "API Integration Framework",
                "hourlyRate": {"amount": 15000, "currency": "USD"},
                "clientId": None,
                "workspaceId": workspace_id,
                "billable": True,
                "memberships": [],
                "color": "#FF9800",
                "estimate": {"estimate": "PT30H", "type": "AUTO"},
                "archived": False,
                "duration": "PT42H45M",
                "clientName": "",
                "note": "Developing novel API integration patterns for real-time data synchronization",
                "costRate": None,
                "timeEstimate": {"estimate": 108000, "type": "AUTO", "resetOption": None},
                "budgetEstimate": None,
                "public": True
            }
        ]
        print(f"✓ Added {len(data['projects'])} sample projects")
    
    # Add sample time entries if empty
    if not data.get("time_entries") or len(data["time_entries"]) == 0:
        base_date = datetime.now() - timedelta(days=30)
        
        data["time_entries"] = []
        
        # Generate time entries for the past 30 days
        rd_activities = [
            ("Algorithm experimentation with neural network architectures", "proj_ml_model_dev_001", 6),
            ("Hyperparameter tuning and model optimization", "proj_ml_model_dev_001", 8),
            ("Feature engineering for customer behavior prediction", "proj_ml_model_dev_001", 7),
            ("Testing different ML frameworks (TensorFlow vs PyTorch)", "proj_ml_model_dev_001", 5),
            ("Resolving model overfitting issues through regularization", "proj_ml_model_dev_001", 6),
            ("Cloud architecture design for distributed computing", "proj_cloud_infra_002", 8),
            ("Load balancing algorithm development and testing", "proj_cloud_infra_002", 7),
            ("Database query optimization experiments", "proj_cloud_infra_002", 6),
            ("Caching strategy implementation and benchmarking", "proj_cloud_infra_002", 5),
            ("API rate limiting algorithm design", "proj_api_integration_003", 6),
            ("Real-time data synchronization protocol development", "proj_api_integration_003", 8),
            ("Webhook retry mechanism with exponential backoff", "proj_api_integration_003", 7),
            ("API authentication flow optimization", "proj_api_integration_003", 5),
        ]
        
        entry_id = 1
        for day_offset in range(30):
            # Skip weekends
            current_date = base_date + timedelta(days=day_offset)
            if current_date.weekday() >= 5:  # Saturday or Sunday
                continue
            
            # Add 1-2 entries per day
            num_entries = random.randint(1, 2)
            for _ in range(num_entries):
                activity = random.choice(rd_activities)
                description, project_id, hours = activity
                
                start_time = current_date.replace(hour=9, minute=0, second=0)
                end_time = start_time + timedelta(hours=hours)
                
                entry = {
                    "id": f"time_entry_{entry_id:04d}",
                    "description": description,
                    "tagIds": ["tag_rd_qualified"],
                    "userId": user_id,
                    "billable": True,
                    "taskId": None,
                    "projectId": project_id,
                    "timeInterval": {
                        "start": start_time.isoformat() + "Z",
                        "end": end_time.isoformat() + "Z",
                        "duration": f"PT{hours}H"
                    },
                    "workspaceId": workspace_id,
                    "isLocked": False
                }
                data["time_entries"].append(entry)
                entry_id += 1
        
        print(f"✓ Added {len(data['time_entries'])} sample time entries")
    
    # Save enriched data
    with open(fixture_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"✓ Saved enriched Clockify fixtures")


def enrich_unified_to_fixtures():
    """Enrich Unified.to fixtures with additional sample data."""
    print("\nEnriching Unified.to fixtures...")
    
    fixture_path = FIXTURES_DIR / "unified_to_responses.json"
    with open(fixture_path) as f:
        data = json.load(f)
    
    # Add sample payslips since the endpoint isn't implemented
    if not data.get("payslips") or data["payslips"] is None:
        base_date = datetime.now() - timedelta(days=90)
        
        data["payslips"] = []
        
        # Generate quarterly payslips for employees
        for month_offset in [0, 1, 2]:
            pay_date = base_date + timedelta(days=30 * month_offset)
            
            # Add payslips for each employee
            for idx, employee in enumerate(data.get("employees", [])[:3]):
                employee_id = employee.get("id", f"emp_{idx}")
                employee_name = employee.get("name", f"Employee {idx}")
                
                # Calculate wages based on role (simulated)
                base_salary = 85000 + (idx * 15000)  # $85k-$115k range
                monthly_gross = base_salary / 12
                
                payslip = {
                    "id": f"payslip_{pay_date.strftime('%Y%m')}_{employee_id}",
                    "employee_id": employee_id,
                    "employee_name": employee_name,
                    "pay_period_start": pay_date.replace(day=1).isoformat(),
                    "pay_period_end": pay_date.replace(day=28).isoformat(),
                    "pay_date": pay_date.replace(day=30).isoformat(),
                    "gross_pay": round(monthly_gross, 2),
                    "net_pay": round(monthly_gross * 0.75, 2),  # After taxes
                    "deductions": {
                        "federal_tax": round(monthly_gross * 0.15, 2),
                        "state_tax": round(monthly_gross * 0.05, 2),
                        "social_security": round(monthly_gross * 0.062, 2),
                        "medicare": round(monthly_gross * 0.0145, 2)
                    },
                    "earnings": {
                        "base_salary": round(monthly_gross, 2),
                        "overtime": 0,
                        "bonus": 0
                    },
                    "currency": "USD",
                    "rd_qualified_percentage": 0.70 + (idx * 0.05)  # 70-80% R&D time
                }
                data["payslips"].append(payslip)
        
        print(f"✓ Added {len(data['payslips'])} sample payslips")
    
    # Save enriched data
    with open(fixture_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"✓ Saved enriched Unified.to fixtures")


def add_metadata_to_fixtures():
    """Add metadata about fixture generation to each file."""
    print("\nAdding metadata to fixtures...")
    
    metadata = {
        "generated_at": datetime.now().isoformat(),
        "source": "Real API calls with automated enrichment",
        "enrichment_version": "1.0",
        "note": "This fixture contains real API response structures with added sample data for testing"
    }
    
    for fixture_file in ["clockify_responses.json", "unified_to_responses.json"]:
        fixture_path = FIXTURES_DIR / fixture_file
        if fixture_path.exists():
            with open(fixture_path) as f:
                data = json.load(f)
            
            data["_metadata"] = metadata
            
            with open(fixture_path, "w") as f:
                json.dump(data, f, indent=2)
            
            print(f"✓ Added metadata to {fixture_file}")


def main():
    """Main function to enrich all fixtures."""
    print("=" * 60)
    print("Enriching Test Fixtures with Sample Data")
    print("=" * 60)
    
    # Enrich Clockify fixtures
    enrich_clockify_fixtures()
    
    # Enrich Unified.to fixtures
    enrich_unified_to_fixtures()
    
    # Add metadata
    add_metadata_to_fixtures()
    
    print("\n" + "=" * 60)
    print("✓ All fixtures enriched successfully!")
    print(f"✓ Fixtures location: {FIXTURES_DIR}")
    print("=" * 60)
    print("\nEnriched data includes:")
    print("  • Clockify: 3 R&D projects + 40+ time entries")
    print("  • Unified.to: Quarterly payslips for employees")
    print("  • Metadata: Generation timestamps and source info")


if __name__ == "__main__":
    main()
