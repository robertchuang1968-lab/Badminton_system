.PHONY: run test lint install

run:
	python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

lint:
	python -m py_compile app/*.py app/**/*.py

install:
	pip install -r requirements.txt
