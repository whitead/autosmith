import subprocess

import requests

from autosmith.smith import smith


def test_smith():
    def test():
        """Test function"""
        import numpy as np

        return "hello world: " + str(np.random.random())

    env = smith(test)
    assert env.container_id is not None
    assert "numpy" in env.requirements
    assert "test" in env.tools

    r = requests.get(f"http://localhost:{env.port}/test")
    assert r.status_code == 200
    assert r.text.startswith('"hello world: ')

    cid = env.container_id
    assert subprocess.run(["docker", "inspect", cid]).returncode == 0

    def test2():
        """Test function 2"""
        return "Goodbye world"

    env = smith(test2, env)
    assert env.container_id is not None

    r = requests.get(f"http://localhost:{env.port}/test2")
    assert r.status_code == 200
    assert r.text == '"Goodbye world"'

    del env
    assert subprocess.run(["docker", "inspect", cid]).returncode == 1
