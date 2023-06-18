import ast
import inspect
import sys
import textwrap
import warnings
from typing import Callable, Dict, List, Mapping, Set, Tuple, Union, cast

import importlib_metadata
from packaging.requirements import Requirement
from pydantic import BaseModel, create_model

Function = Union[str, Callable]


def _parse_requirements(requirements: str) -> Set[Requirement]:
    """Parse a requirements.txt file into a set of Requirement objects"""
    return set(
        [
            Requirement(line.strip())
            for line in requirements.splitlines()
            if len(line.strip()) > 0
        ]
    )


def get_imports(source: str) -> Tuple[Dict[str, str], Set[str]]:
    module_node: ast.AST = ast.parse(source)
    imports: Dict[str, str] = dict()
    wildcards = set()
    # Walk through all the nodes in the module body
    for n in ast.walk(module_node):
        if isinstance(n, ast.Import):
            imports.update({a.name: a.name for a in n.names if not a.asname})
            imports.update({a.asname: a.name for a in n.names if a.asname})
        # If the node is an import-from statement
        elif isinstance(n, ast.ImportFrom):
            imports.update({a.asname: cast(str, n.module) for a in n.names if a.asname})
            imports.update(
                {a.name: cast(str, n.module) for a in n.names if not a.asname}
            )
            if "*" in imports:
                wildcards.add(imports["*"])
    return imports, wildcards


def get_func_imports(func: Function) -> List[str]:
    """Get the imports necessary to run a function - either present in module or body"""
    module_imports: Dict[str, str] = dict()
    module_wildcards: Set[str] = set()
    source: str
    if isinstance(func, str):
        source = textwrap.dedent(func)
    else:
        func = cast(Callable, func)
        source = textwrap.dedent(inspect.getsource(func))

        module_name: str = func.__module__
        if module_name != "__main__":
            module_source: str = inspect.getsource(sys.modules[module_name])
            module_imports, module_wildcards = get_imports(module_source)

    func_imports, func_wildcards = get_imports(source)
    all_imports = set(func_imports.values()) | module_wildcards | func_wildcards
    source_node: ast.AST = ast.parse(source)
    # now see which module imports are actually used in the function
    for n in ast.walk(source_node):
        if isinstance(n, ast.Name):
            if n.id in module_imports:
                all_imports.add(module_imports[n.id])
    return list(all_imports)


def get_requirements_from_imports(imports: List[str]) -> str:
    """Get the PyPI package name and versions for a list of imports as requirements.txt"""
    packages: Mapping[str, List[str]] = importlib_metadata.packages_distributions()
    pypi_names: List[str] = []
    for module in imports:
        if module in packages:
            # Use the first element of the list as the distribution name
            dist: str = packages[module][0]
            version: str = importlib_metadata.version(dist)
            specifier: str = f"{dist}=={version}"
            pypi_names.append(specifier)
    return "\n".join(pypi_names)


def consistent_requirements(env_requirements: str, func_requirements: str) -> bool:
    """Checks if a function's requirements are consistent with the environment

    Does not account for versions currently
    """

    # make them lists so they aren't consumed
    env_reqs = _parse_requirements(env_requirements)
    func_reqs = _parse_requirements(func_requirements)

    return env_reqs.issuperset(func_reqs)


def merge_requirements(env_requirements: str, func_requirements: str) -> str:
    """Merge the requirements of a function and an environment to create new requirements"""
    env_reqs = _parse_requirements(env_requirements)
    func_reqs = _parse_requirements(func_requirements)

    merged_reqs = env_reqs.union(func_reqs)
    return "\n".join([str(r) for r in merged_reqs])


def get_requirements(func: Function) -> str:
    """Get the requirements for a function"""
    func_imports = get_func_imports(func)
    func_requirements = get_requirements_from_imports(func_imports)
    return func_requirements


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


def make_schema(func: Callable) -> BaseModel:
    """Make a schema from a function"""
    name = func.__name__
    desc = func.__doc__
    if desc is None:
        raise ValueError("Function must have a docstring if inferring schema")
    properties = {}
    for arg in func.__code__.co_varnames[: func.__code__.co_argcount]:
        # use default values
        if func.__defaults__ and arg in func.__defaults__:
            properties[arg] = func.__defaults__[func.__code__.co_varnames.index(arg)]
        # use type hints (no elif - intentional
        if arg in func.__annotations__:
            if arg in properties:
                properties[arg] = (func.__annotations__[arg], properties[arg])
            else:
                properties[arg] = (func.__annotations__[arg], ...)
        # use str as default (or rely on type inference from default)
        else:
            properties[arg] = (str, ...)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return create_model(name.capitalize(), **properties, __doc__=desc)
