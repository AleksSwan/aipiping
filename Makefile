PYTHON=python
WORKER=worker
SHARED=shared
BACKEND=backend
PIP=$(PYTHON) -m pip
export PYTHONPATH := $(PWD):$(PWD)/shared:$(PWD)/worker:$(PWD)/backend
.PHONY: install test run lint

# Targets
show_paths:
	@echo $(PYTHONPATH)

test_worker:
	$(PYTHON) -m pytest $(WORKER)/tests/ -v

test_backend:
	$(PYTHON) -m pytest $(BACKEND)/tests/ -v

run_worker:
	$(PYTHON) $(WORKER)/app_$(WORKER)/main.py

run_backend:
	$(PYTHON) $(BACKEND)/app_$(BACKEND)/main.py

lint:
	isort $(BACKEND)/
	black $(BACKEND)/
	ruff check $(BACKEND)/
	mypy $(BACKEND)/ --check-untyped-defs
	isort $(WORKER)/
	black $(WORKER)/
	ruff check $(WORKER)/
	mypy $(WORKER)/ --check-untyped-defs
	isort $(SHARED)/
	black $(SHARED)/
	ruff check $(SHARED)/
	mypy $(SHARED)/ --check-untyped-defs

clean_worker:
	rm -rf $(WORKER)/__pycache__
	rm -rf $(WORKER)/*.egg-info
	rm -rf $(WORKER)/.pytest_cache
	rm -rf $(WORKER)/.mypy_cache
	rm -rf $(WORKER)/.ruff_cache

clean_backend:
	rm -rf $(BACKEND)/__pycache__
	rm -rf $(BACKEND)/*.egg-info
	rm -rf $(BACKEND)/.pytest_cache
	rm -rf $(BACKEND)/.mypy_cache
	rm -rf $(BACKEND)/.ruff_cache

