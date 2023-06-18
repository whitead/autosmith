import inspect
import json
import os
import pickle
import tempfile
import textwrap
import time
import urllib.request
from pathlib import Path
from typing import Callable, Dict, Optional, Union, cast

import pkg_resources
from datamodel_code_generator.parser.jsonschema import JsonSchemaParser
from jinja2 import Environment, PackageLoader
from pydantic import BaseModel, Field, PrivateAttr, validator

from .docker import Docker
from .func import (
    consistent_requirements,
    func_to_url,
    get_func_description,
    get_func_name,
    get_requirements,
    make_schema,
    merge_requirements,
)
from .version import __version__


class EncodedTool(BaseModel):
    """EncodedTool is a tool encoded as a string"""

    function: str
    function_name: str
    input_class_name: str
    description: str
    input_class_raw_schema: str

    @validator("input_class_name")
    def input_class_name_should_be_capitalized(cls, v):
        return v.capitalize()

    @validator("function_name")
    def function_name_cannot_be_docs(cls, v):
        if v == "docs" or v == "Docs":
            raise ValueError("Function name cannot be docs")
        return v


class ToolEnv(BaseModel):
    """ToolEnv is the environment for a set of tools"""

    requirements: str = ""
    name: str = "tool-environment"
    version: str = __version__
    host: str = "127.0.0.1"
    port: int = 8080
    tools: Dict[str, EncodedTool] = {}
    docker_file_commands: str = ""
    base_image: str = "python:3.11-slim"
    container_id: Optional[str] = None
    _saved: bool = PrivateAttr(False)
    save_dir: Optional[Path] = Path.home() / ".autosmith"
    docker: Docker = Field(default_factory=Docker)
    url: str = ""

    @validator("requirements")
    def requirements_must_be_valid(cls, v):
        try:
            pkg_resources.parse_requirements(v.splitlines())
        except ValueError:
            raise ValueError("Requirements must be valid")
        return v

    @validator("url", always=True, pre=True)
    def url_is_computed(cls, v, values) -> str:
        """url is the url of the tool environment"""
        return f"http://{values['host']}:{values['port']}"

    def close(self):
        cid = self.container_id
        if cid is not None and not self._saved:
            self.docker.remove_container(cid)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def save(self):
        """Save the tool environment"""
        if self.save_dir is None:
            raise ValueError("save_dir must be set")
        if not self.save_dir.exists():
            os.mkdir(self.save_dir)
        with open(self.save_dir / f"{self.name}", "wb") as f:
            pickle.dump(self, f)
        self._saved = True

    @classmethod
    def load(
        cls,
        title: str = "tool-environment",
        save_dir: Path = Path.home() / ".autosmith",
    ):
        """Load a tool environment"""
        with open(save_dir / f"{title}", "rb") as f:
            o = pickle.load(f)
        o._saved = False
        return o

    def start(self):
        if self.container_id is not None:
            self.docker.remove_container(self.container_id)
        self.container_id = self.docker.run_container(self.name, self.port)

    def build(
        self,
    ):
        """Adds func to given env (or creates new one)"""
        if self.container_id is not None:
            self.docker.remove_container(self.container_id)

        self.docker.remove_image(self.name)
        # create directory for temp files
        with tempfile.TemporaryDirectory() as tmpdirname:
            with open(os.path.join(tmpdirname, "Dockerfile"), "w") as f:
                f.write(self.render_container())
            with open(os.path.join(tmpdirname, "main.py"), "w") as f:
                f.write(self.render_server())
            with open(os.path.join(tmpdirname, "requirements.txt"), "w") as f:
                f.write(self.render_requirements())
            self.docker.build_image(self.name, Path(tmpdirname))
            self.container_id = self.docker.run_container(self.name, self.port)

        success = bool(self.docker.mock)
        for _ in range(10):
            if success:
                break
            try:
                urllib.request.urlopen(f"{self.url}/docs")
                success = True
            except Exception:
                time.sleep(0.5)
        if not success:
            raise ValueError("Could not connect to server")

    def add_tool(
        self,
        func: Union[Callable, str],
        schema: Optional[Union[BaseModel, str]] = None,
    ):
        """Stamp a function with a schema and tool environment"""
        if isinstance(func, str) and schema is None:
            raise ValueError("Must provide schema if func is a string")
        raw_schema: Optional[str] = None
        schema_title: str = ""
        if schema is None:
            schema = make_schema(cast(Callable, func))
        if not isinstance(schema, str):
            schema_title = schema.__name__
            parser = JsonSchemaParser(schema.schema_json())
            parser.parse_raw()
            raw_schema = parser.results[0].render()
        else:
            schema = cast(str, schema)
            # check if schema is valid json
            try:
                schema_title = json.loads(schema)["title"]
                parser = JsonSchemaParser(schema)
                parser.parse_raw()
                raw_schema = parser.results[0].render()
            except json.JSONDecodeError:
                # if not, assume it's python code
                raw_schema = textwrap.dedent(schema)
                schema_title = (
                    raw_schema.split("(BaseModel):")[0].split("class ")[1].strip()
                )

        func_requirements = get_requirements(func)

        if not consistent_requirements(self.requirements, func_requirements):
            self.requirements = merge_requirements(self.requirements, func_requirements)

        if not consistent_requirements(self.requirements, func_requirements):
            raise ValueError("Cannot make requirements consistent")

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
            input_class_raw_schema=raw_schema,
        )

        # add tool to tool_env
        self.tools[func_to_url(tool.function_name)] = tool
        self.build()

    def render_server(self) -> str:
        # render tool_env
        jinja_env = Environment(loader=PackageLoader("autosmith", "templates"))
        template = jinja_env.get_template("main.py.jinja")
        return template.render(env=self)

    def render_container(self) -> str:
        """template a container with a tool environment"""
        env = Environment(loader=PackageLoader("autosmith", "templates"))
        template = env.get_template("Dockerfile.jinja")
        return template.render(env=self)

    def render_requirements(self) -> str:
        """Render requirements.txt from tool_env"""
        env = Environment(loader=PackageLoader("autosmith", "templates"))
        template = env.get_template("requirements.txt.jinja")
        return template.render(env=self)
