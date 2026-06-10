import os
import zipfile
from pathlib import Path

def create_migration_package():
    """Package the essential files for moving to a secondary laptop."""
    output_filename = "tom_migration_package.zip"
    
    # Files and directories to include
    include_list = [
        "AGENTS.md",
        "CLAUDE.md",
        "agent.py",
        "main.py",
        "requirements.txt",
        "launch_tom_ui.bat",
        "start_email_agent_daemon.bat",
        "start_instagram_agent_daemon.bat",
        "setup_secondary_laptop.ps1",
        "SECONDARY_LAPTOP_DEPLOYMENT_PLAN.md",
        "config/",
        "tools/",
        "agents/",
        "skills/",
        "safety/",
        "resources/",
    ]
    
    # Exclude list (patterns)
    exclude_patterns = [
        "__pycache__",
        ".git",
        "venv",
        "chromedriver.exe",
        "dist",
        "build",
        ".env", # Don't include .env for safety, user should create it on new machine or copy manually
        "credential",   # SECURITY: google-credentials.json and any *credential* file
        "token",        # SECURITY: OAuth token files
        ".pem", ".key", # SECURITY: private keys
    ]

    print(f"Creating migration package: {output_filename}")
    
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for item in include_list:
            path = Path(item)
            if not path.exists():
                print(f"Warning: {item} not found, skipping.")
                continue
                
            if path.is_file():
                zipf.write(path)
                print(f"Added file: {path}")
            elif path.is_dir():
                for root, dirs, files in os.walk(path):
                    # Filter out excluded directories
                    dirs[:] = [d for d in dirs if d not in exclude_patterns]
                    
                    for file in files:
                        if any(p in file for p in exclude_patterns):
                            continue
                        file_path = Path(root) / file
                        zipf.write(file_path)
                print(f"Added directory: {path}")

    print(f"\nMigration package created successfully: {os.path.abspath(output_filename)}")
    print("Copy this zip file and your '.env' file to the new laptop, then run setup_secondary_laptop.ps1")

if __name__ == "__main__":
    create_migration_package()
