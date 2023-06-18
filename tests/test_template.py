import ast

import pytest
from pydantic import BaseModel

from autosmith.docker import Docker
from autosmith.env import ToolEnv


def is_valid_python(code):
    try:
        ast.parse(code)
    except SyntaxError:
        return False
    return True


def test_template_server_models():
    """Test with callable function and BaseModel schema"""

    def func(a: int, b: float) -> int:
        """Add a and b"""
        return int(a + b)

    class Schema(BaseModel):
        a: int
        b: float

    env = ToolEnv(docker=Docker(mock=None))
    env.add_tool(func, schema=Schema)
    rendered = env.render_server()
    assert is_valid_python(rendered)
    print(rendered)
    assert "Schema(BaseModel):" in rendered


def test_template_server_str():
    """Test with callable function and BaseModel schema"""

    func = """
    def func(a: int, b: float) -> int:
        '''Add a and b'''
        return int(a + b)
    """
    schema = """
    class Schema(BaseModel):
        a: int
        b: float
    """
    env = ToolEnv(docker=Docker(mock=None))
    env.add_tool(func, schema=schema)
    rendered = env.render_server()
    assert is_valid_python(rendered)
    assert "Schema(BaseModel):" in rendered


def test_template_server_infer():
    """Test with callable function and BaseModel schema"""

    def func(a: int, b: float) -> int:
        """Add a and b"""
        return int(a + b)

    env = ToolEnv(docker=Docker(mock=None))
    env.add_tool(func)
    rendered = env.render_server()
    assert is_valid_python(rendered)
    assert "Func(BaseModel):" in rendered


def test_template_server_fail():
    """Test with callable function and BaseModel schema"""

    func = """
    def func(a: int, b: float) -> int:
        '''Add a and b'''
        return a + b
    """

    env = ToolEnv(docker=Docker(mock=None))
    with pytest.raises(ValueError):
        env.add_tool(func)

    def no_doc():
        pass

    with pytest.raises(ValueError):
        env.add_tool(no_doc)


def test_template_container():
    """Test templating container"""
    tool_env = ToolEnv(requirements="pytest==6.2.2")
    rendered = tool_env.render_container()
    assert str(tool_env.port) in rendered
