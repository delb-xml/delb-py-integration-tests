[private]
default:
  @just --list


_check-for-venv:
    #!/usr/bin/env python3
    import os, sys
    if os.environ.get("CI") == "true":
        raise SystemExit(0)
    if sys.prefix == sys.base_prefix:
        print("Please activate a virtual environment!")
        raise SystemExit(1)


# Fetch web resources
[group("corpora")]
fetch-web-resources *args:
    dit corpora fetch-web-resources {{args}}


# Formats and lints scripts
[group("dev")]
format-and-lint:
    black src/
    mypy --check-untyped-defs src/
    flake8 --ignore LOG011 --max-line-length 89 src/


# Sets everything up to run the tests from a fresh clone
[group("general")]
get-ready: _check-for-venv
    pip install -e .
    git submodule update


# Excutes maintenace tasks
[group("general")]
maintenance:
    find logs -name "*.log" -mtime +7
    git submodule foreach git clean --force
    git submodule foreach git gc


# Normalizes contents of included git submodules
[group("corpora")]
normalize-corpora *args:
    dit corpora normalize {{args}}


# Pushes 'delb-integration-tests' branch of corpus submodules to remotes, overwriting existing instances
[group("corpora")]
push-submodules:
    git submodule foreach \
      git push --force origin delb-integration-tests:delb-integration-tests


# Calculate and report some corpus statistics
[group("corpora")]
summarize:
    dit corpora summarize


# Run tests
[group("tests")]
run-tests:
    dit tests run --sample-volume 25 location-paths
    dit tests run lxml-model-concordance parse-serialize-equality
