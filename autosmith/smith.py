import os
import subprocess
import tempfile
import time
import urllib.request
from typing import Optional

from .env import get_requirements
from .template import render_container, render_requirements, render_server
from .types import Function, ToolEnv


def smith(func: Function, env: Optional[ToolEnv] = None) -> ToolEnv:
    """Adds func to given env (or creates new one)"""
    if env is None:
        env = ToolEnv(requirements=get_requirements(func))
    if env.container_id is not None:
        subprocess.run(["docker", "kill", env.container_id])
    # create directory for temp files
    with tempfile.TemporaryDirectory() as tmpdirname:
        with open(os.path.join(tmpdirname, "Dockerfile"), "w") as f:
            f.write(render_container(env))
        with open(os.path.join(tmpdirname, "main.py"), "w") as f:
            f.write(render_server(func, tool_env=env))
        with open(os.path.join(tmpdirname, "requirements.txt"), "w") as f:
            f.write(render_requirements(env))
        # remove old containers with same image name
        output = subprocess.run(
            ["docker", "ps", "-a", "-q", "--filter", f"ancestor={env.title}"],
            capture_output=True,
        )
        if output.returncode != 0:
            raise ValueError("Docker ps failed")
        for cid in output.stdout.decode("utf-8").splitlines():
            print("found these containers", cid)
            subprocess.run(["docker", "rm", "-f", cid])

        # remove old images
        subprocess.run(["docker", "rmi", env.title])
        # build docker image
        output = subprocess.run(["docker", "build", "-t", env.title, tmpdirname])
        if output.returncode != 0:
            raise ValueError("Docker build failed")
        output = subprocess.run(
            ["docker", "run", "-d", "-p", f"{env.port}:8080", env.title],
            capture_output=True,
        )
        if output.returncode != 0:
            raise ValueError("Docker run failed")
        env.container_id = output.stdout.decode("utf-8").strip()

    success = False
    for _ in range(10):
        try:
            urllib.request.urlopen(f"http://localhost:{env.port}/docs")
            success = True
            break
        except Exception as e:
            print(e)
            time.sleep(0.5)
    if not success:
        raise ValueError("Could not connect to server")

    return env
