# Everyday tasks. Run `make` to list them. The numbered scripts in scripts/ are the pipeline stages behind these.
PY = uv run python
WRANGLER = npx --yes wrangler@4.159.0

.DEFAULT_GOAL := help
.PHONY: help install build serve test daily progress deploy verify-live clean

help: ## List the tasks
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-12s %s\n", $$1, $$2}'

install: ## Install the Python dependencies
	uv sync

build: ## Build the site into site/ (with the local queue present, also refreshes corpus/archive)
	$(PY) scripts/14_build_site.py

site/index.html:
	$(PY) scripts/14_build_site.py

serve: site/index.html ## Preview the site locally, building it first if it isn't built yet
	$(WRANGLER) dev

test: ## Run the Python and JavaScript tests
	$(PY) -m unittest discover -s tests
	node --test tests/site_sort.test.cjs

daily: ## Fetch, queue and extract the new days, then rebuild the site
	$(PY) scripts/31_daily.py

progress: ## Show extraction progress
	$(PY) scripts/26_progress.py

deploy: ## Build and deploy main through GitHub Actions; pushing to main does the same
	gh workflow run deploy.yml --ref main

verify-live: ## Check that the live site serves exactly what site/ holds
	scripts/compare_live.sh

clean: ## Delete the generated pages, keeping the hand-written files in site/
	git clean -fdXq site
