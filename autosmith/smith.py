import os
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Optional

from .docker import Docker
from .env import Function, ToolEnv
from .func import get_requirements
from .template import render_container, render_requirements, render_server


def smith(
    func: Function, env: Optional[ToolEnv] = None, docker: Optional[Docker] = None
) -> ToolEnv:
    """Adds func to given env (or creates new one)"""
    if docker is None:
        docker = Docker()
    if env is None:
        env = ToolEnv(requirements=get_requirements(func), docker=docker)
    if env.container_id is not None:
        docker.remove_container(env.container_id)

    # TODO: this logic should probably be in env

    docker.remove_image(env.name)
    # create directory for temp files
    with tempfile.TemporaryDirectory() as tmpdirname:
        with open(os.path.join(tmpdirname, "Dockerfile"), "w") as f:
            f.write(render_container(env))
        with open(os.path.join(tmpdirname, "main.py"), "w") as f:
            f.write(render_server(func, tool_env=env))
        with open(os.path.join(tmpdirname, "requirements.txt"), "w") as f:
            f.write(render_requirements(env))
        docker.build_image(env.name, Path(tmpdirname))
        env.container_id = docker.run_container(env.name, env.port)

    success = bool(docker.mock)
    for _ in range(10):
        if success:
            break
        try:
            urllib.request.urlopen(f"{env.url}/docs")
            success = True
        except Exception:
            time.sleep(0.5)
    if not success:
        raise ValueError("Could not connect to server")

    return env
