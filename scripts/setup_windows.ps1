$ErrorActionPreference = "Stop"
$PythonVersion = "3.12"
py -$PythonVersion -c "import sys; assert (3,10) <= sys.version_info < (3,14), 'Python 3.10-3.13 required'"
py -$PythonVersion -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e ".[test,windows]"
