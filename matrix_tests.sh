#!/bin/bash

set -eu -o pipefail

VERSION_LIST=$(yq eval -M -o csv '.jobs.build_and_test.strategy.matrix.python_version' .github/workflows/tests.yaml);
VERSIONS=($(echo $VERSION_LIST | sed 's/,/ /g'));

install_version() {
  version=$1;

  pyenv install $version;
}

use_version() {
  version=$1;
  retried=$2;
  install_successful=true;

  DEACTIVATE_RESPONSE=$( { deactivate || true; } 2>&1 );

  PYENV_LOCAL_RESPONSE=$( { pyenv local $version > outfile; rm outfile; } 2>&1 );

  if [ "$PYENV_LOCAL_RESPONSE" = "pyenv: version \`$version' not installed" ]; then
    install_successful=false;

    if [ "$retried" = "false" ]; then
      echo "$version is not installed, installing now";
      install_version $version;
    fi
  fi

  if [ "$retried" = "true" ] && [ ! $install_successful ]; then
    echo "Failed to install $version";
    exit 1;
  fi

  echo "Using version $version";
  pyenv local $version;
}

setup_environment() {
  rm -rf .venv;

  pip install --upgrade pip -q;
  pip install --upgrade uv -q;

  uv sync --frozen -q;
}

run_linters() {
  uv run flake8;
  uv run ruff check;
  uv run ruff format --diff;
}

run_tests() {
  uv run pytest;
}

get_coverage() {
  uv run coverage run;
  uv run coverage report;
}

main() {
  for VERSION in "${VERSIONS[@]}"; do
    echo "========================="
    use_version $VERSION false;

    echo "Setting up environment for $VERSION";
    setup_environment;

    echo "Running linters for $VERSION";
    run_linters;

    echo "Running pytest for $VERSION";
    run_tests;
  done

  echo "========================="
  echo "Getting coverage statistics for $VERSION";
  get_coverage;
}

cover_current_only() {
  VERSION=$(python -V | awk '{print $2}')

  echo "Running linters for $VERSION";
  run_linters;

  echo "Getting coverage statistics for $VERSION";
  get_coverage;
}

if [ "$*" = "-a" ]; then
  main;
else
  cover_current_only;
fi
