import subprocess

import requests

from autosmith.smith import smith
from autosmith.types import ToolEnv


def test_smith():
    def test():
        """Test function"""
        import numpy as np

        return "hello world: " + str(np.random.random())

    env = smith(test)
    assert env.container_id is not None
    assert "numpy" in env.requirements
    assert "test" in env.tools

    r = requests.get(f"{env.url}/test")
    assert r.status_code == 200
    assert r.text.startswith('"hello world: ')

    cid = env.container_id
    assert subprocess.run(["docker", "inspect", cid]).returncode == 0

    def test2():
        """Test function 2"""
        return "Goodbye world"

    env = smith(test2, env)
    assert env.container_id is not None

    r = requests.get(f"{env.url}/test2")
    assert r.status_code == 200
    assert r.text == '"Goodbye world"'

    del env
    assert subprocess.run(["docker", "inspect", cid]).returncode == 1


def test_save():
    env = ToolEnv(requirements="numpy")
    json = env.json()
    env.save()

    env2 = ToolEnv.load(env.title)
    assert env2.json() == json


def test_persist_containers():
    def test():
        """Test function"""
        import numpy as np

        return "hello world: " + str(np.random.random())

    env = smith(test)
    env.save()
    url = env.url
    del env

    env2 = ToolEnv.load("tool-environment")
    assert env2.url == url
    assert env2.container_id is not None

    r = requests.get(f"{env2.url}/test")
    assert r.status_code == 200
    assert r.text.startswith('"hello world: ')
    cid = env2.container_id
    del env2

    assert subprocess.run(["docker", "inspect", cid]).returncode == 1
