import os
import sys
import subprocess

print("Current Python:", sys.executable)
print("Arguments:", sys.argv)

# Let's try to re-execute using the venv python if we are not already
venv_python = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".venv", "Scripts", "python.exe"))
current_python = os.path.abspath(sys.executable)

if current_python.lower() != venv_python.lower() and os.path.exists(venv_python):
    print("Re-executing with venv python via subprocess...")
    # Wrap python executable and arguments in quotes if needed
    cmd = [venv_python] + sys.argv + ["--re-executed"]
    sys.exit(subprocess.call(cmd))
else:
    print("Already running in venv python or venv python not found!")
