from math import *  # noqa

import pytest
from numpy import arange
from pydantic import BaseModel

from autosmith.func import (
    consistent_requirements,
    func_to_url,
    get_func_description,
    get_func_imports,
    get_func_name,
    get_imports,
    get_requirements_from_imports,
    make_schema,
    merge_requirements,
)


def test_nested_imports():
    source = "import a.b.c\n" "from a.b import c\n" "c.do_something()\n"
    imports, _ = get_imports(source)
    # Assert that the imports list contains the expected modules
    assert imports == {"a.b.c": "a.b.c", "c": "a.b"}


def test_imports_with_aliases():
    source = "import a as b\n" "from a import b as c\n" "c.do_something()\n" "b = c"
    imports, _ = get_imports(source)
    assert imports == {"b": "a", "c": "a"}


def test_wildcard_imports():
    source = "from foo import *\n" "from bar import *\n" "import bar\n"
    imports, wildcards = get_imports(source)
    assert wildcards == set(["foo", "bar"])
    assert "bar" in imports


def test_body_alone_imports():
    # fmt: off
    # type: ignore
    # isort: skip
    def func():
        import a  # noqa
        import b as c  # noqa
    # fmt: on
    imports = get_func_imports(func)
    assert set(imports) == set(["a", "b", "math"])


def test_body_and_module_func_imports():
    # fmt: off
    # type: ignore
    # isort: skip
    def func():
        arange(3)
        pytest.main()
    # fmt: on
    imports = get_func_imports(func)
    assert set(imports) == set(["numpy", "pytest", "math"])


def test_mixed_func_imports():
    # fmt: off
    # type: ignore
    # isort: skip
    def func():
        sin(3)  # noqa
        arange(3)
        pytest.main()
        import foo  # noqa
    # fmt: on
    imports = get_func_imports(func)
    assert set(imports) == set(["numpy", "pytest", "foo", "math"])


def test_get_requirements():
    reqs = get_requirements_from_imports(["numpy", "pytest", "foo", "math"])
    assert "numpy" in reqs
    assert "pytest" in reqs
    assert "foo" not in reqs


def test_consistent_requirements():
    env = """
    numpy==1.19.5
    pytest==6.2.2
    """
    proposed = """
    numpy==1.19.5
    pytest==6.2.2
    """

    assert consistent_requirements(env, proposed)

    proposed = """
    numpy==1.19.5
    """

    assert consistent_requirements(env, proposed)

    proposed = """
    numpy==1.18
    pytest
    """

    assert not consistent_requirements(env, proposed)


def test_str_func():
    get_func_imports("def foo(): pass")


def test_merge_requirements():
    env = """
    numpy==1.19.5
    pytest==6.2.2
    """
    proposed = """
    numpy==1.19.5
    pytest==6.2.2
    """

    assert consistent_requirements(env, merge_requirements(env, proposed))

    proposed = """
    numpy
    """

    assert not consistent_requirements(env, merge_requirements(env, proposed))

    proposed = """
    rdkit
    """

    assert consistent_requirements(env + "\nrdkit", merge_requirements(env, proposed))


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
