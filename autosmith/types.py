from typing import Dict, Optional

import pkg_resources
from pydantic import BaseModel, validator

from .version import __version__


class EncodedTool(BaseModel):
    """EncodedTool is a tool encoded as a string"""

    function: str
    function_name: str
    input_class_name: str
    input_class_schema: str
    description: str
    input_class_raw_schema: Optional[str] = None


class ToolEnv(BaseModel):
    """ToolEnv is the environment for a tool"""

    requirements: str
    title: str = "Tool environment"
    version: str = __version__
    host: str = "0.0.0.0"
    port: int = 8080
    tools: Dict[str, EncodedTool] = {}

    @validator("requirements")
    def requirements_must_be_valid(cls, v):
        try:
            pkg_resources.parse_requirements(v.splitlines())
        except ValueError:
            raise ValueError("Requirements must be valid")
        return v
