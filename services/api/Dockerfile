# Trip Companion API — local/dev image (mock providers by default).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
RUN pip install -e .

# migrations, seed script and the mock providers' fixtures (tests/fixtures/{places,flights,egypt})
COPY alembic.ini ./
COPY migrations ./migrations
COPY scripts ./scripts
COPY tests/fixtures ./tests/fixtures
COPY docker-entrypoint.sh ./

EXPOSE 8000
ENTRYPOINT ["sh", "./docker-entrypoint.sh"]
