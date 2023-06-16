import subprocess
from typing import Callable, Dict, Optional, Union

import pkg_resources
from pydantic import BaseModel, validator

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
    """ToolEnv is the environment for a tool"""

    requirements: str
    title: str = "tool-environment"
    version: str = __version__
    host: str = "0.0.0.0"
    port: int = 8080
    tools: Dict[str, EncodedTool] = {}
    docker_file_precommands: str = ""
    base_image: str = "python:3.11-slim"
    container_id: Optional[str] = None

    @validator("requirements")
    def requirements_must_be_valid(cls, v):
        try:
            pkg_resources.parse_requirements(v.splitlines())
        except ValueError:
            raise ValueError("Requirements must be valid")
        return v

    def __del__(self):
        if self.container_id is not None:
            subprocess.run(["docker", "rm", "-f", self.container_id])
