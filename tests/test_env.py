import requests

from autosmith.docker import Docker
from autosmith.env import ToolEnv
from autosmith.smith import smith


def test_env_url():
    env = ToolEnv(requirements="numpy")
    assert env.url is not None
    assert str(env.url) == "http://127.0.0.1:8080"


def test_smith():
    def test():
        """Test function"""
        import numpy as np

        return "hello world: " + str(np.random.random())

    docker = Docker(mock=None)

    env = smith(test, docker=docker)
    assert env.container_id is not None
    assert "numpy" in env.requirements
    assert "test" in env.tools

    if not docker.mock:
        r = requests.get(f"{env.url}/test")
        assert r.status_code == 200
        assert r.text.startswith('"hello world: ')

    cid = env.container_id
    assert docker.is_running(cid)

    def test2():
        """Test function 2"""
        return "Goodbye world"

    env = smith(test2, env, docker=docker)
    assert env.container_id is not None

    if not docker.mock:
        r = requests.get(f"{env.url}/test2")
        assert r.status_code == 200
        assert r.text == '"Goodbye world"'

    del env
    assert not docker.is_running(cid) or docker.mock


def test_save():
    env = ToolEnv(requirements="numpy")
    json = env.json()
    env.save()

    env2 = ToolEnv.load(env.name)
    assert env2.json() == json


def test_persist_containers():
    def test():
        """Test function"""
        import numpy as np

        return "hello world: " + str(np.random.random())

    docker = Docker(mock=None)

    env = smith(test, docker=docker)
    env.save()
    url = env.url
    del env

    env2 = ToolEnv.load("tool-environment")
    env2.docker = docker
    assert env2.url == url
    assert env2.container_id is not None

    if not docker.mock:
        r = requests.get(f"{env2.url}/test")
        assert r.status_code == 200
        assert r.text.startswith('"hello world: ')
    cid = env2.container_id
    env2.close()

    assert not docker.is_running(cid) or docker.mock
