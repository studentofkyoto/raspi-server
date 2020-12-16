# styling
pylint backend/lib/irrp.py --rcfile ./.pylintrc

# typing for documentation purpose
mypy backend/lib/irrp.py --strict --ignore-missing-imports

# typing for test codes
# mypy tests
