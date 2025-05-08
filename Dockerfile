FROM python:3.12-alpine

# Install libmagic (necessary for python-magic lib)
RUN apk add --no-cache file

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    PYTHONPATH="${PYTHONPATH}:/app"

WORKDIR /app

RUN pip install poetry==1.8.3 && \
    addgroup -S web && \
    adduser -S -G web -h /app web && \
    chown web:web -R /app

USER web

COPY --chown=web:web poetry.lock pyproject.toml ./
COPY --chown=web:web src .

RUN poetry install && rm -rf $POETRY_CACHE_DIR

EXPOSE ${BACKEND_PORT}

CMD sh -c "poetry run uvicorn main:app --workers ${BACKEND_WORKERS_NUMBER} --host 0.0.0.0 --port ${BACKEND_PORT}"
