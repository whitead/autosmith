from .env import ToolEnv

store = dict()


def register_env(env: ToolEnv) -> ToolEnv:
    """Register an environment"""
    store[env.name] = env
    return env
