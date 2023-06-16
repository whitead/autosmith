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
from autosmith.smith import smith
import requests

def hello():
    """Return hello"""
    return 'hello'

with smith(hello) as env:
    r = requests.get(env.url + '/hello')
    print(r.text)
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
url = env.url + '/double?x=2'
r = requests.get(url)
print(r.text)
# 4

env.name = 'myenv'
env.save()
del env

r = requests.get(url)
print(r.text)
# 4

env = ToolEnv.load('myenv')

# now the container will be removed since we didn't save
del env
```

The `ToolEnv` object is meant to collect functions
and slowly build up an environment. Note that the functions you
define need not be executable in your python environment.

```python
def nparange(n: int):
    """Return a numpy array"""
    import numpy as np
    # can only output standard python types
    return np.arange(n).astype(int).tolist()

def double(x: int):
    """Double an integer"""
    return x * 2

env = smith(nparange)
env = smith(double, env=env)

r = requests.get(env.url + '/nparange?n=5')
print(r.text)
# [0, 1, 2, 3, 4]
env.close() # another way to close the container
```
