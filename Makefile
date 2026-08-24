.PHONY: all test scan report ui clean

all: test scan

test:
	python -m unittest discover tests

scan:
	python -m sanchay.cli . --limit 10

report:
	python -m sanchay.cli . --report sanchay-report.html

ui:
	sanchay-ui .

clean:
	rm -rf __pycache__ sanchay/__pycache__ tests/__pycache__ .pytest_cache *.egg-info build dist
