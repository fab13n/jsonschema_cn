#!/bin/bash
ENV=venv
ENV_ABS=$(cd $(dirname $0)/$ENV && pwd)
if [[ ! -d "$ENV_ABS" ]]; then
    # python3 -m venv $ENV
    ln -s $ENV_ABS/bin/activate .
    . activate
    $ENV_ABS/bin/pip install jsview jsonschema parsimonious ipython coverage wheel
    $ENV_ABS/bin/python setup.py bdist_wheel 
fi
if [[ "$VIRTUAL_ENV" == "" ]]; then
    . $ENV_ABS/bin/activate
fi
COVERAGE=$ENV_ABS/bin/coverage
$COVERAGE erase
$COVERAGE run --include './jsonschema_cn/**' -m jsonschema_cn.test
$COVERAGE report -m
