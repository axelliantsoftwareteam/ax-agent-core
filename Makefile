PYTHON ?= python3

.PHONY: setup lint test run demo smoke

setup:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e .[dev]

lint:
	ruff check src tests examples
	mypy src

test:
	pytest

run:
	ax-agent run-demo

demo:
	ax-agent run-demo --scripted

smoke:
	$(PYTHON) examples/demo.py
