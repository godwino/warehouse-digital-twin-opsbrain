PYTHON ?= python

.PHONY: install format lint test generate run

install:
	$(PYTHON) -m pip install -r requirements.txt

format:
	$(PYTHON) -m black src app tests scripts
	$(PYTHON) -m isort src app tests scripts

lint:
	$(PYTHON) -m ruff check src app tests scripts

test:
	$(PYTHON) -m pytest

generate:
	$(PYTHON) scripts/generate_demo_data.py

run:
	streamlit run app/streamlit_app.py
