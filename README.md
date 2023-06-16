# autosmith

Make tools quickly

## Install

**You must have docker installed and running.**

```bash
pip install autosmith
```

## Usage

The package will inspect a python function, its imports, argument types,
and start a container that serves it on an endpoint.

```python
from autosmith import smith
import requests

def hello():
    """Return hello"""
    return 'hello'

env = smith(hello)
print(requests.get(env.url + '/hello'))
# 'hello'
```

By default, the container will be removed when returned `ToolEnv` (`env` below) is
garbage collected. You can keep the container via `env.save()`.
You can then load via `env.load()`.

```python

def double(x: int):
    """Double an integer"""
    return x * 2

env = smith(double)
env.name = 'myenv'
env.save()

del env

print(requests.get(env.url + '/double?x=2'))
# 4

env = ToolEnv.load('myenv')

del env # now the container will be removed
```

The `ToolEnv` object is meant to collect functions
and slowly build up an environment. Note that the functions you
define need not be executable in your python environment.

```python
def nparange(n: int):
    """Return a numpy array"""
    import numpy as np
    return np.arange(n)

def double(x: int):
    """Double an integer"""
    return x * 2

env = smith(nparange)
env = smith(double, env=env)

print(requests.get(env.url + '/nparange?n=5'))
# [0, 1, 2, 3, 4]
```
