#! /bin/bash -e
cd "$( dirname "${BASH_SOURCE[0]}" )"
cd ..

[ -d "dist" ] && rm -r dist/

python -m build
