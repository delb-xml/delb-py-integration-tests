all_corpora := "corpora"
python_files := "*.py corpora/*.py git-submodules/*.py"


# Fetch web resources
fetch-web-resources *args:
    python corpora/fetch-web-resources.py {{args}}


# Formats and lints scripts
format-and-lint:
    black {{python_files}}
    mypy --check-untyped-defs {{python_files}}
    flake8 --max-line-length 89 {{python_files}}


# Link all git submodule contents in the data directory
link-submodules:
    python corpora/link-submodules.py


# Excutes maintenace tasks
maintenance:
    rm logs/multiprocessing-*
    find logs -name "*.log" -mtime +7
    git submodule foreach git clean
    git submodule foreach git gc


# Normalizes contents of included git submodules
normalize-submodules *args:
    python git-submodules/normalize.py {{args}}


# Pushes 'delb-integration-tests' branch of corpus submodules to remotes, overwriting existing instances
push-submodules:
    git submodule foreach \
      git push --force origin delb-integration-tests:delb-integration-tests


# Run all tests
run-tests *args:
    python test-location-paths.py {{args}}
    python test-lxml-model-concordance.py {{args}}
    python test-parse-serialize-equality.py {{args}}
