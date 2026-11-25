# Nothing here is a Python package: venv installs the suite's tools alone.
EDITABLE =

include pubrules-python.mk

.PHONY: check shellcheck

# The actions' scripts, as CI checks them.
SCRIPTS := $(wildcard actions/*/*.sh)

shellcheck: ## shellcheck on every action's scripts
	shellcheck $(SCRIPTS)

check: sync-check shellcheck functional ## Everything CI runs
