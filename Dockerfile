# --- Stage 1: testing -------------------------------------------------------
FROM mcr.microsoft.com/playwright/python:v1.58.0 AS testing
USER root
COPY ./ca-bundle.crt /usr/local/share/ca-certificates/
RUN update-ca-certificates
WORKDIR /usr/src/app

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

COPY ./api/ ./api
COPY ./scraper/ ./scraper
COPY ./config_loader.py ./
COPY ./pyproject.toml ./
COPY ./tests/ ./tests
RUN touch ./tests/__init__.py

RUN coverage run --source=api,scraper,config_loader -m pytest tests \
 && coverage xml --omit="*/test*"

# --- Stage 2: runtime -------------------------------------------------------
FROM mcr.microsoft.com/playwright/python:v1.58.0
ARG COMMIT_ID
ARG BUILD_DATE
ENV COMMIT_ID=${COMMIT_ID} \
    BUILD_DATE=${BUILD_DATE} \
    XDG_CACHE_HOME=/tmp/.cache \
    XDG_CONFIG_HOME=/tmp/.config \
    HOME=/tmp \
    SCRAPER_CONFIG_PATH=/etc/scraper/config.json \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER root
COPY ./ca-bundle.crt /usr/local/share/ca-certificates/
RUN update-ca-certificates

WORKDIR /usr/src/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./api/ ./api
COPY ./scraper/ ./scraper
COPY ./config_loader.py ./
COPY --from=testing /usr/src/app/coverage.xml /tmp/coverage/coverage.xml

RUN mkdir -p /tmp/.cache /tmp/.config \
 && chgrp -R 0 /usr/src/app /tmp/.cache /tmp/.config /tmp/coverage \
 && chmod -R g=u /usr/src/app /tmp/.cache /tmp/.config /tmp/coverage

EXPOSE 8080
USER 1001
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
