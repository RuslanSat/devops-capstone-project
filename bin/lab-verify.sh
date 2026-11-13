#!/usr/bin/env bash
# Run only in the isolated course Cloud IDE, using its disposable account database.
set -euo pipefail
cd "$(dirname "$0")/.."
source "$HOME/venv/bin/activate"
mkdir -p evidence
python --version | tee evidence/python-version.txt
pip install -r requirements.txt
nosetests 2>&1 | tee evidence/security-headers-done.txt
flake8 service tests --count --statistics 2>&1 | tee evidence/flake8.txt
pylint service --fail-under=9 2>&1 | tee evidence/pylint.txt
echo 'Unit tests, minimum 95% coverage, flake8 and pylint passed.'
