import subprocess
import sys

# Path to the virtual environment
venv_path = "venv"

# Command to activate the virtual environment and execute the Python script
command = f"source {venv_path}/bin/activate && python start.py"

# Execute the command using subprocess
subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
subprocess.run(command, shell=True)
