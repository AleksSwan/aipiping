PYTHON=python
WORKER=worker
SHARED=shared
PIP=$(PYTHON) -m pip
export PYTHONPATH := $(PWD):$(PWD)/shared:$(PWD)/worker:$(PWD)/backend
.PHONY: install test run lint

# Targets
show_paths:
	@echo $(PYTHONPATH)

test_worker:
	$(PYTHON) -m pytest worker/tests/ -vv

run_worker:
	$(PYTHON) $(WORKER)/app/main.py

lint:
	isort $(WORKER)/
	black $(WORKER)/
	ruff check $(WORKER)/
	mypy $(WORKER)/
	isort $(SHARED)/
	black $(SHARED)/
	ruff check $(SHARED)/
	mypy $(SHARED)/

clean_worker:
	rm -rf $(WORKER)/__pycache__
	rm -rf $(WORKER)/*.egg-info
	rm -rf $(WORKER)/.pytest_cache
	rm -rf $(WORKER)/.mypy_cache
	rm -rf $(WORKER)/.ruff_cache


