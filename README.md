# autosmith

Make tools quickly

## Install

**You must have docker installed and running.**

```bash
pip install autosmith
```

## Usage

```python
from autosmith import smith
from urllib.request import urlopen

def hello():
    return 'hello'

env = smith(hello)
print(urlopen(env.url).read())
# 'hello'
```
