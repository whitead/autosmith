import subprocess
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, validator


class Docker(BaseModel):
    mock: Optional[bool] = False

    @validator("mock")
    def docker_must_be_installed(cls, v):
        if v:
            return v
        try:
            subprocess.run(["docker", "--version"], capture_output=True)
        except FileNotFoundError:
            if v is None:
                return True
            raise ValueError("Docker must be installed")
        return v

    def remove_image(self, image_name: str):
        if self.mock:
            return
        # remove old containers with same image name
        output = subprocess.run(
            ["docker", "ps", "-a", "-q", "--filter", f"ancestor={image_name}"],
            capture_output=True,
        )
        if output.returncode != 0:
            raise ValueError("Docker ps failed")
        for cid in output.stdout.decode("utf-8").splitlines():
            subprocess.run(["docker", "rm", "-f", cid], capture_output=True)

        # remove old images
        subprocess.run(["docker", "rmi", image_name], capture_output=True)

    def build_image(self, image_name: str, dir: Path):
        if self.mock:
            return
        output = subprocess.run(
            ["docker", "build", "-t", image_name, dir], capture_output=True
        )
        if output.returncode != 0:
            raise ValueError("Docker build failed")

    def run_container(self, image_name: str, port: int) -> str:
        if self.mock:
            return "mock"
        output = subprocess.run(
            ["docker", "run", "-d", "-p", f"{port}:8080", image_name],
            capture_output=True,
        )
        if output.returncode != 0:
            raise ValueError("Docker run failed")
        return output.stdout.decode("utf-8").strip()

    def remove_container(self, cid: str):
        if self.mock:
            return
        subprocess.run(["docker", "rm", "-f", cid], capture_output=True)

    def is_running(self, cid: str) -> bool:
        if self.mock:
            return True
        output = subprocess.run(["docker", "inspect", cid], capture_output=True)
        if output.returncode != 0:
            return False
        return True
