FROM mcr.microsoft.com/playwright/python:v1.58.0

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV SCRAPER_CONFIG_PATH=/etc/scraper/config.json \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# OpenShift runs containers as an arbitrary UID in GID 0.
# Make the app tree group-writable so that UID can read/write.
RUN chgrp -R 0 /app && chmod -R g=u /app

EXPOSE 8080
USER 1001

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
