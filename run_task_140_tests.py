"""
Quick Start Script for Task 140 Testing

This script helps you run all Task 140 integration tests with a single command.
It checks prerequisites, starts the backend if needed, and runs all tests.

Usage:
    python run_task_140_tests.py
"""

import os
import sys
import time
import subprocess
import webbrowser
from pathlib import Path

try:
    import requests
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm
except ImportError:
    print("Installing required dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "requests", "rich"], check=True)
    import requests
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm

console = Console()


def check_backend_running():
    """Check if backend is running"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def start_backend():
    """Start the backend server"""
    console.print("[yellow]Starting backend server...[/yellow]")
    
    # Check if main.py exists
    if not Path("main.py").exists():
        console.print("[red]Error: main.py not found. Are you in the rd_tax_agent directory?[/red]")
        return None
    
    # Start backend in background
    if sys.platform == "win32":
        process = subprocess.Popen(
            ["python", "-m", "uvicorn", "main:app", "--reload"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    else:
        process = subprocess.Popen(
            ["python", "-m", "uvicorn", "main:app", "--reload"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    
    # Wait for backend to start
    console.print("[yellow]Waiting for backend to start...[/yellow]")
    for i in range(30):
        time.sleep(1)
        if check_backend_running():
            console.print("[green]✓ Backend started successfully[/green]")
            return process
        console.print(f"[yellow]Waiting... ({i+1}/30)[/yellow]")
    
    console.print("[red]✗ Backend failed to start[/red]")
    return None


def run_automated_tests():
    """Run automated Python integration tests"""
    console.print("\n[bold cyan]Running Automated Integration Tests[/bold cyan]")
    
    if not Path("test_final_integration.py").exists():
        console.print("[red]Error: test_final_integration.py not found[/red]")
        return False
    
    result = subprocess.run([sys.executable, "test_final_integration.py"])
    return result.returncode == 0


def open_frontend_tests():
    """Open frontend test pages in browser"""
    console.print("\n[bold cyan]Opening Frontend Test Pages[/bold cyan]")
    
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        console.print("[red]Error: frontend directory not found[/red]")
        return False
    
    test_pages = [
        "test_complete_integration.html",
        "test_responsive.html"
    ]
    
    for page in test_pages:
        page_path = frontend_dir / page
        if page_path.exists():
            url = f"file:///{page_path.absolute()}"
            console.print(f"[green]Opening {page}...[/green]")
            webbrowser.open(url)
        else:
            console.print(f"[yellow]Warning: {page} not found[/yellow]")
    
    return True


def main():
    """Main entry point"""
    console.print(Panel.fit(
        "[bold cyan]Task 140: Final Integration Testing[/bold cyan]\n"
        "[yellow]Quick Start Script[/yellow]",
        border_style="cyan"
    ))
    
    # Check if we're in the right directory
    if not Path("main.py").exists():
        console.print("[red]Error: Please run this script from the rd_tax_agent directory[/red]")
        console.print("[yellow]Usage: cd rd_tax_agent && python run_task_140_tests.py[/yellow]")
        sys.exit(1)
    
    # Step 1: Check backend
    console.print("\n[bold]Step 1: Checking Backend[/bold]")
    backend_running = check_backend_running()
    
    if backend_running:
        console.print("[green]✓ Backend is already running[/green]")
        backend_process = None
    else:
        console.print("[yellow]Backend is not running[/yellow]")
        
        if Confirm.ask("Would you like to start the backend?"):
            backend_process = start_backend()
            if not backend_process:
                console.print("[red]Failed to start backend. Please start manually:[/red]")
                console.print("[yellow]uvicorn main:app --reload[/yellow]")
                sys.exit(1)
        else:
            console.print("[yellow]Please start the backend manually:[/yellow]")
            console.print("[yellow]uvicorn main:app --reload[/yellow]")
            sys.exit(1)
    
    # Step 2: Run automated tests
    console.print("\n[bold]Step 2: Running Automated Tests[/bold]")
    
    if Confirm.ask("Run automated Python integration tests?", default=True):
        success = run_automated_tests()
        if not success:
            console.print("[yellow]Some automated tests failed. Check the output above.[/yellow]")
    
    # Step 3: Open frontend tests
    console.print("\n[bold]Step 3: Frontend Tests[/bold]")
    
    if Confirm.ask("Open frontend test pages in browser?", default=True):
        open_frontend_tests()
        console.print("\n[green]Frontend test pages opened in browser[/green]")
        console.print("[yellow]Please run the tests manually in the browser[/yellow]")
    
    # Summary
    console.print("\n" + "="*70)
    console.print(Panel.fit(
        "[bold green]Testing Setup Complete[/bold green]\n\n"
        "Next Steps:\n"
        "1. Review automated test results above\n"
        "2. Complete frontend tests in browser\n"
        "3. Test responsive design on different viewports\n"
        "4. Review TASK_140_TESTING_GUIDE.md for detailed instructions\n\n"
        "When all tests pass, mark Task 140 as complete!",
        border_style="green"
    ))
    
    # Keep backend running
    if backend_process:
        console.print("\n[yellow]Backend is running. Press Ctrl+C to stop.[/yellow]")
        try:
            backend_process.wait()
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping backend...[/yellow]")
            backend_process.terminate()
            console.print("[green]Backend stopped[/green]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Testing interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
