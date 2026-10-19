FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py db.py mock_api.py sync.py ./

RUN useradd --create-home app
USER app

EXPOSE 8000

# Serves the API by default; override the command with `python sync.py` to run one booking sync.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
