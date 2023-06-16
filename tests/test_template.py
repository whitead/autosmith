import ast

import pytest
from pydantic import BaseModel

from autosmith.template import (
    func_to_url,
    get_func_description,
    get_func_name,
    make_schema,
    render_container,
    render_server,
)
from autosmith.types import ToolEnv


def is_valid_python(code):
    try:
        ast.parse(code)
    except SyntaxError:
        return False
    return True


def test_make_schema():
    def func(a: int, b: float) -> int:
        """Add a and b"""
        return int(a + b)

    class Func(BaseModel):
        """Add a and b"""

        a: int
        b: float

    schema = make_schema(func)
    assert schema.schema() == Func.schema()


def test_make_schema_imports():
    def func(a: int, b: float) -> int:
        """Add a and b"""
        return int(a + b)

    class Func(BaseModel):
        """Add a and b"""

        a: int
        b: float

    schema = make_schema(func)
    print(schema.schema())
    assert schema.schema() == Func.schema()


def test_empty_schema():
    """Test with callable function and make sure schema is empty"""

    def func() -> str:
        """print hello world"""
        return "hello world"

    class Func(BaseModel):
        """print hello world"""

        pass

    schema = make_schema(func)
    assert schema.schema() == Func.schema()


def test_get_func_name():
    def func(a: int, b: float) -> int:
        """Add a and b"""
        return int(a + b)

    assert get_func_name(func) == "func"


def test_get_func_description():
    def func(a: int, b: float) -> int:
        """Add a and b"""
        return int(a + b)

    assert get_func_description(func) == "Add a and b"


def test_func_to_url():
    assert func_to_url("foo_bar") == "foo-bar"


def test_template_server_models():
    """Test with callable function and BaseModel schema"""

    def func(a: int, b: float) -> int:
        """Add a and b"""
        return int(a + b)

    class Schema(BaseModel):
        a: int
        b: float

    rendered = render_server(func, schema=Schema)
    assert is_valid_python(rendered)


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
    rendered = render_server(func, schema)
    assert is_valid_python(rendered)


def test_template_server_infer():
    """Test with callable function and BaseModel schema"""

    def func(a: int, b: float) -> int:
        """Add a and b"""
        return int(a + b)

    rendered = render_server(func)
    assert is_valid_python(rendered)


def test_template_server_fail():
    """Test with callable function and BaseModel schema"""

    func = """
    def func(a: int, b: float) -> int:
        '''Add a and b'''
        return a + b
    """
    with pytest.raises(ValueError):
        render_server(func)

    def no_doc():
        pass

    with pytest.raises(ValueError):
        render_server(no_doc)


def test_template_container():
    """Test templating container"""
    tool_env = ToolEnv(requirements="pytest==6.2.2")
    rendered = render_container(tool_env)
    assert tool_env.host in rendered
