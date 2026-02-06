# confyui-aei

[![PyPI](https://img.shields.io/pypi/v/confyui-aei.svg)](https://pypi.org/project/confyui-aei/)
[![Changelog](https://img.shields.io/github/v/release/mse11/confyui-aei?include_prereleases&label=changelog)](https://github.com/mse11/confyui-aei/releases)
[![Tests](https://github.com/mse11/confyui-aei/actions/workflows/test.yml/badge.svg)](https://github.com/mse11/confyui-aei/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/mse11/confyui-aei/blob/master/LICENSE)

ConfUI Advanced Easy Installer

## Installation

Install this tool using `pip`:
```bash
pip install confyui-aei
```
## Usage

For help, run:
```bash
confyui-aei --help
```
You can also use:
```bash
python -m confyui_aei --help
```
## Development

To contribute to this tool, first checkout the code. Then create a new virtual environment:
```bash
cd confyui-aei
python -m venv venv
source venv/bin/activate
```
Now install the dependencies and test dependencies:
```bash
pip install -e '.[test]'
```
To run the tests:
```bash
python -m pytest
```
