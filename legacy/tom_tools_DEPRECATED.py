import subprocess
import os
from tools.project_paths import project_path_str

class TomTools:
    def __init__(self):
        self.chrome_profile = "Rajesh Ponnapuretti" # Change if different on your system
        self.config_dir = project_path_str("tom_config")

    async def open_application(self, app_name):
        """Handles opening Word, Excel, Chrome, etc. via Process"""
        print(f"[Tom] Requesting to open: {app_name}")
        
        if app_name.lower() == "chrome":
            # Chrome logic with profile path detection needs specific flags
            cmd = f'start "" "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"'
            
            # If you want specific profile, use: --user-data-dir="C:\Users\...\AppData\Local\Google\Chrome\User Data"
            subprocess.run(cmd)
            return {"status": "success", "message": f"Opened {app_name}"}
        elif app_name.lower() == "word":
            subprocess.Popen(["winword.exe"])
            return {"status": "success", "message": f"Opened Word"}
            
        # Add more apps here
        
    async def open_profile_browser(self):
        """Logic to open specific Chrome Profile"""
        # This requires the profile path usually at: C:\Users\[User]\AppData\Local\Google\Chrome\User Data
        print("[Tom] Opening specific Chrome profile...")
        subprocess.Popen(["cmd", "/k", "start chrome"]) 
        return {"status": "pending_manual_check", "message": "Browser opened, check for Rajesh profile"}

    async def create_file(self, path, content):
        """Writes text or code to a file"""
        try:
            with open(path, "w") as f:
                f.write(content)
            print(f"[Tom] Wrote to: {path}")
            return {"status": "success"}
        except Exception as e:
            print(f"[Tom] Error writing file: {e}")
            return {"status": "error", "message": str(e)}

    async def write_code_and_run(self, filename, code):
        """Writes a website and opens it locally"""
        path = f"{filename}"
        await self.create_file(path, code)
        # Open the file
        await self.open_application("edge") # Using Edge to open HTML/JS for now
        
    async def draft_email(self, recipient, subject, body):
        """Prepares an email, does not send yet without approval"""
        return {
            "status": "ready", 
            "recipient": recipient, 
            "subject": subject, 
            "body_preview": body[:100] + "..." 
        }
