from setuptools import setup

# for typing
__version__ = ""
exec(open("autosmith/version.py").read())

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="autosmith",
    version=__version__,
    description="Make tools quickly automatically",
    author="Andrew White",
    author_email="white.d.andrew@gmail.com",
    url="https://github.com/whitead/autosmith",
    license="Apache 2.0",
    packages=["autosmith"],
    package_data={"autosmith": ["templates/*"]},
    install_requires=[
        "jinja2",
        "pydantic",
        "datamodel_code_generator",
        "importlib_metadata",
    ],
    test_suite="tests",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
