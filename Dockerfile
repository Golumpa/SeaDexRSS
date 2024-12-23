FROM python:3.11-alpine as base

RUN apk update && pip install --upgrade pip && \
	adduser -D -h /home/seadexrss -g 'HAL' seadexrss

WORKDIR /home/seadexrss

FROM base as builder

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN apk add build-base libffi-dev && \
	pip install -U poetry

COPY --chown=seadexrss:seadexrss poetry.lock pyproject.toml /home/seadexrss/

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --without dev --no-root

FROM base as runtime

ENV VIRTUAL_ENV=/home/seadexrss/.venv \
    PATH="/home/seadexrss/.venv/bin:$PATH"

COPY --from=builder --chown=seadexrss:seadexrss ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY --chown=seadexrss:seadexrss . .

USER seadexrss

CMD ["python", "app/main.py"]