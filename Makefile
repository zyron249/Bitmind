install:
	pip install -r requirements.txt

test:
	pytest -q

lint:
	ruff check . || true

run:
	uvicorn bitmind.api.main:app --reload --port 8000

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
