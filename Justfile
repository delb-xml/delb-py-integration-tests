[private]
default:
  @just --list


_check-for-venv:
    #!/usr/bin/env python3
    import sys
    if sys.prefix == sys.base_prefix:
        print("Please activate a virtual environment!")
        raise SystemExit(1)


# Fetch web resources
fetch-web-resources *args:
    dit corpora fetch-web-resources {{args}}


# Formats and lints scripts
format-and-lint:
    black src/
    mypy --check-untyped-defs src/
    flake8 --ignore LOG011 --max-line-length 89 src/


# Sets everything up to run the tests from a fresh clone
get-ready: _check-for-venv
    pip install -e .
    git submodule update


# Excutes maintenace tasks
maintenance:
    find logs -name "*.log" -mtime +7
    git submodule foreach git clean --force
    git submodule foreach git gc


# Normalizes contents of included git submodules
normalize-corpora *args:
    dit corpora normalize {{args}}


# Pushes 'delb-integration-tests' branch of corpus submodules to remotes, overwriting existing instances
push-submodules:
    git submodule foreach \
      git push --force origin delb-integration-tests:delb-integration-tests


# Calculate and report some corpus statistics
summarize:
    dit corpora summarize


# Run tests
run-tests:
    dit tests run --sample-volume 25 location-paths
    dit tests run lxml-model-concordance parse-serialize-equality
