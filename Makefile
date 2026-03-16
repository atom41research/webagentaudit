.PHONY: test test-fast test-unit test-browser test-e2e test-all test-docker test-docker-unit test-docker-e2e test-seq test-debug

WORKERS ?= auto

# Default: fast unit tests only (~3-5s)
test: test-fast

test-fast:
	uv run pytest -m unit -n $(WORKERS) --dist worksteal -q

test-unit: test-fast

test-browser:
	uv run pytest -m browser -n $(WORKERS) --dist worksteal -v

test-e2e:
	uv run pytest -m e2e -n 4 --dist worksteal -v

test-all:
	uv run pytest -n $(WORKERS) --dist worksteal -v

# Sequential (for debugging — full output, no xdist capture)
test-seq:
	uv run pytest -v

# Debug specific test: make test-debug TEST=tests/e2e/test_detection_e2e.py
test-debug:
	uv run pytest -v -s --tb=long $(TEST)

# Docker targets
test-docker:
	docker compose -f docker-compose.test.yml run --rm --build test

test-docker-unit:
	docker compose -f docker-compose.test.yml run --rm --build test-unit

test-docker-e2e:
	docker compose -f docker-compose.test.yml run --rm --build test-e2e
