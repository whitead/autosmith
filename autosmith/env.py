import ast
import inspect
import sys
import textwrap
from typing import Callable, Dict, List, Mapping, Set, Tuple, Union, cast

import importlib_metadata


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


def get_func_imports(func: Union[Callable, str]) -> List[str]:
    """Get the imports necessary to run a function - either present in module or body"""
    module_imports: Dict[str, str] = dict()
    module_wildcards: Set[str] = set()
    source: str
    if isinstance(func, str):
        source = textwrap.dedent(func)
    else:
        func = cast(Callable, func)
        module_name: str = func.__module__
        module_source: str = inspect.getsource(sys.modules[module_name])
        module_imports, module_wildcards = get_imports(module_source)
        source = textwrap.dedent(inspect.getsource(func))

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

    Note that this does account for versions!
    """
    # We can use the pkg_resources and packaging modules to parse and compare requirements
    import pkg_resources

    # make them lists so they aren't consumed
    env_reqs = list(pkg_resources.parse_requirements(env_requirements.splitlines()))
    func_reqs = list(pkg_resources.parse_requirements(func_requirements.splitlines()))
    # kind of weird, but we assume func requirements has ==
    for req in env_reqs:
        if not any(
            [
                any(
                    req.specifier.filter(  # type: ignore
                        [str(r.specifier).split("==")[-1]]
                    )  # type: ignore
                )
                for r in func_reqs
                if r.key == req.key
            ]
        ):
            return False
    return True


def get_requirements(func: Union[Callable, str]) -> str:
    """Get the requirements for a function"""
    func_imports = get_func_imports(func)
    func_requirements = get_requirements_from_imports(func_imports)
    return func_requirements
