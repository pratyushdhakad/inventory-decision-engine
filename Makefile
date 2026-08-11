.PHONY: run test

run:
	PYTHONPATH=src python3 -m inventory_decision_engine.pipeline

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v
