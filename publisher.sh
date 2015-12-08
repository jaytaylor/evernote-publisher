#!/usr/bin/env bash

cd "$(dirname "$0")"

if ! [ -d venv ] || ! [ -d venv/bin ] || ! [ -e venv/bin/activate ]; then
    virtualenv venv
    . venv/bin/activate
    pip install -r requirements.txt
else
    . venv/bin/activate
fi

./app.py $*

