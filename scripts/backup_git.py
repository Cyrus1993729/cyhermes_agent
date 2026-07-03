"""Hermes auto backup — triggered daily by cron (no_agent)"""
import subprocess, sys, os

HERMES_DIR = os.path.join(os.environ["LOCALAPPDATA"], "hermes")
os.chdir(HERMES_DIR)

# Stage all changes
subprocess.run(["git", "add", "-A"], capture_output=True)

# Check if there's anything to commit
r = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
if r.returncode == 0:
    sys.exit(0)  # No changes, silent exit

# Commit
subprocess.run(["git", "commit", "-m", "auto backup"], capture_output=True)

# Push
r = subprocess.run(["git", "push"], capture_output=True, text=True)
if r.returncode != 0:
    print("BACKUP FAILED: git push error")
    print(r.stderr)
    print("Manual: cd %LOCALAPPDATA%\\hermes && git push")
    sys.exit(1)
