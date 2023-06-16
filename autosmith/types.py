import os
import pickle
import subprocess
from pathlib import Path
from typing import Callable, Dict, Optional, Union

import pkg_resources
from pydantic import BaseModel, HttpUrl, PrivateAttr, computed_field, validator

from .version import __version__

Function = Union[str, Callable]


class EncodedTool(BaseModel):
    """EncodedTool is a tool encoded as a string"""

    function: str
    function_name: str
    input_class_name: str
    input_class_schema: str
    description: str
    input_class_raw_schema: Optional[str] = None

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
    title: str = "tool-environment"
    version: str = __version__
    host: str = "0.0.0.0"
    port: int = 8080
    tools: Dict[str, EncodedTool] = {}
    docker_file_commands: str = ""
    base_image: str = "python:3.11-slim"
    container_id: Optional[str] = None
    _saved: bool = PrivateAttr(False)
    save_dir: Optional[Path] = Path.home() / ".autosmith"

    @validator("requirements")
    def requirements_must_be_valid(cls, v):
        try:
            pkg_resources.parse_requirements(v.splitlines())
        except ValueError:
            raise ValueError("Requirements must be valid")
        return v

    @computed_field  # type: ignore[misc]
    @property  # type: ignore[misc]
    def url(self) -> HttpUrl:
        """url is the url of the tool environment"""
        return HttpUrl(f"http://{self.host}:{self.port}")

    def __del__(self):
        if self.container_id is not None and not self._saved:
            subprocess.run(["docker", "rm", "-f", self.container_id])

    def save(self):
        """Save the tool environment"""
        if self.save_dir is None:
            raise ValueError("save_dir must be set")
        if not self.save_dir.exists():
            os.mkdir(self.save_dir)
        with open(self.save_dir / f"{self.title}", "wb") as f:
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
