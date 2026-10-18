FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY migrate.py ./
COPY migrations ./migrations

RUN useradd --create-home app
USER app

# Runs once and exits; a non-zero exit means a migration failed.
CMD ["python", "migrate.py"]
