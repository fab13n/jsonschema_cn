#!/bin/bash
ENV=venvpy36
if [[ ! -d "$ENV" ]]; then
    python3 -m venv $ENV
    ln -s venvpy36/bin/activate .
    . activate
    pip install jsview parsimonious ipython coverage wheel
fi
if [[ "$VIRTUAL_ENV" == "" ]]; then
    . activate
fi
coverage erase
coverage run --include './jsonschema_cn/**' -m jsonschema_cn.test
coverage report -m
