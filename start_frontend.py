"""
Start Frontend Script

Opens the frontend pages in the default web browser.
"""

import webbrowser
import os
from pathlib import Path

# Get the frontend directory
frontend_dir = Path(__file__).parent / "frontend"

# List of pages to open
pages = [
    "home.html",
    "index.html",  # Dashboard
    "workflow.html",
    "reports.html"
]

print("Opening R&D Tax Credit Automation Frontend...")
print("=" * 60)

for page in pages:
    page_path = frontend_dir / page
    if page_path.exists():
        url = f"file:///{page_path.absolute()}"
        print(f"Opening: {page}")
        webbrowser.open(url)
    else:
        print(f"Warning: {page} not found")

print("=" * 60)
print("Frontend pages opened in browser!")
print("\nBackend is running at: http://localhost:8000")
print("API Documentation: http://localhost:8000/docs")
print("\nPress Ctrl+C to stop the backend")
