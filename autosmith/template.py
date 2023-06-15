import ast
import inspect
import json
import textwrap
from typing import Callable, Optional, Union, cast

from jinja2 import Environment, PackageLoader
from pydantic import BaseModel, create_model

from .env import consistent_requirements, get_requirements
from .types import EncodedTool, ToolEnv


def make_schema(func: Callable) -> BaseModel:
    """Make a schema from a function"""
    name = func.__name__
    desc = func.__doc__
    properties = {}
    for arg in func.__code__.co_varnames:
        # use type hints
        if arg in func.__annotations__:
            properties[arg] = (func.__annotations__[arg], ...)
        # use default values
        elif func.__defaults__ and arg in func.__defaults__:
            properties[arg] = (
                type(
                    func.__defaults__[
                        func.__code__.co_varnames.index(arg) - len(func.__defaults__)
                    ]
                ),
                ...,
            )
        # use str as default
        else:
            properties[arg] = (str, ...)
    return create_model(name, **properties, description=desc)


def get_func_name(func: Union[Callable, str]) -> str:
    """Get the name of a function"""
    if callable(func):
        return func.__name__

    source: str = textwrap.dedent(cast(str, func))
    source_node: ast.AST = ast.parse(source)
    for n in ast.walk(source_node):
        if isinstance(n, ast.FunctionDef):
            return n.name
    raise ValueError("Could not find function name")


def get_func_description(func: Union[Callable, str]) -> str:
    """Get the description of a function"""
    if callable(func):
        return func.__doc__ if func.__doc__ else ""

    source: str = textwrap.dedent(cast(str, func))
    source_node: ast.AST = ast.parse(source)
    for n in ast.walk(source_node):
        if isinstance(n, ast.FunctionDef):
            ds = ast.get_docstring(n)
            if ds is None:
                return ""
            return str(ds)
    raise ValueError("Could not find function description")


def func_to_url(name: str) -> str:
    return name.replace("_", "-")


def template_server(
    func: Union[Callable, str],
    schema: Optional[Union[BaseModel, str]] = None,
    tool_env: Optional[ToolEnv] = None,
) -> str:
    """Stamp a function with a schema and tool environment"""
    if isinstance(func, str) and schema is None:
        raise ValueError("Must provide schema if func is a string")
    raw_schema: Optional[str] = None
    schema_title: str = ""
    if schema is None:
        schema = make_schema(cast(Callable, func))
    if not isinstance(schema, str):
        schema_title = schema.__name__
        schema = json.dumps(schema.schema())
    else:
        schema = cast(str, schema)
        # check if schema is valid json
        try:
            json.loads(schema)
            schema_title = json.loads(schema)["title"]
        except json.JSONDecodeError:
            # if not, assume it's python code
            raw_schema = textwrap.dedent(schema)
            schema_title = (
                raw_schema.split("(BaseModel):")[0].split("class ")[1].strip()
            )
    func_requirements = get_requirements(func)
    env = Environment(loader=PackageLoader("autosmith", "templates"))

    if not tool_env:
        tool_env = ToolEnv(requirements=func_requirements, tools={})

    if not consistent_requirements(tool_env.requirements, func_requirements):
        raise ValueError("Requirements are not consistent")

    if callable(func):
        source = textwrap.dedent(inspect.getsource(func))
    else:
        source = textwrap.dedent(func)

    # convert schema and func to tool
    tool = EncodedTool(
        function=source,
        function_name=get_func_name(func),
        description=get_func_description(func),
        input_class_name=schema_title,
        input_class_schema=schema,
        input_class_raw_schema=raw_schema,
    )

    # add tool to tool_env
    tool_env.tools[func_to_url(tool.function_name)] = tool

    # render tool_env
    template = env.get_template("main.py.jinja")
    return template.render(env=tool_env)


def template_container(tool_env: ToolEnv) -> str:
    """template a container with a tool environment"""
    env = Environment(loader=PackageLoader("autosmith", "templates"))
    template = env.get_template("Dockerfile.jinja")
    return template.render(env=tool_env)