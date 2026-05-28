FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /code

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY ./app /code/app
COPY ./data /code/data

RUN mkdir -p /code/data && \
    adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /code

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
