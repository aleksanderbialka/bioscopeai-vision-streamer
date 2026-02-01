#!/bin/bash

# This script runs the tests for the bioscopeai-vision-streamer project.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR/.."

source /var/www/bioscopeai-vision-streamer/app/bioscopeai_vision_streamer_env/bin/activate
pytest -p pytest_github_actions_annotate_failures --junitxml=results/pytest-results.xml --html=results/pytest-report.html --self-contained-html
