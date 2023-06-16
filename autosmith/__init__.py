import subprocess

# check if docker is installed
try:
    subprocess.run(["docker", "ps"])
except FileNotFoundError:
    raise ImportError("Docker is not installed")
