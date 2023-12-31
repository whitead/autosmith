import os
import pickle
from pathlib import Path
from typing import Callable, Dict, Optional, Union

import pkg_resources
from pydantic import BaseModel, Field, PrivateAttr, validator

from .docker import Docker
from .version import __version__

Function = Union[str, Callable]


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

    requirements: str
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
