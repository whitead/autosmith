from .types import ToolEnv
import subprocess

store = dict()

def register_env(env: ToolEnv) -> ToolEnv:
    """Register an environment"""
    store[env.title] = env
    return env
