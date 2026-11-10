.PHONY: test doc check-prompts clean

test:
	python3 -m pytest -q tests

doc:
	python3 -I scripts/build-doc.py --out docs/index.html

check-prompts:
	python3 scripts/check-prompts.py --expect 15

clean:
	rm -rf .pytest_cache build dist *.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
