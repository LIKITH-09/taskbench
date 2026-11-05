# Shortcuts for macOS/Linux and CI. On Windows, run the commands shown on the right directly.
.PHONY: install lint format test validate db smoke dev heldout injection

install:          ## python -m pip install -e ".[dev,ollama]"
	python -m pip install -e ".[dev,ollama]"

lint:             ## ruff check . && ruff format --check .
	ruff check .
	ruff format --check .

format:           ## ruff format . && ruff check --fix .
	ruff format .
	ruff check --fix .

test:             ## pytest
	pytest

validate:         ## taskbench validate
	taskbench validate

db:               ## taskbench build-db
	taskbench build-db

smoke:            ## mock model, 3 dev tasks per config, no GPU, about a minute
	taskbench run --config all --split dev --limit 3 --epochs 1 --model mockllm/model --run-id smoke-mock

dev:              ## local model on all 40 dev tasks, 1 epoch
	taskbench run --config all --split dev --epochs 1

heldout:          ## the real experiment: 80 held-out tasks x 4 configs x 3 epochs (needs a clean git tree)
	taskbench run --config all --split heldout --condition main

injection:        ## injection condition: 10 tasks x {rag, agent} x 3 epochs
	taskbench run --config all --split heldout --condition injection
