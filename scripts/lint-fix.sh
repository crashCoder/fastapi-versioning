#!/bin/bash -e
cd "$( dirname "${BASH_SOURCE[0]}" )"
cd ..

isort .
black .
