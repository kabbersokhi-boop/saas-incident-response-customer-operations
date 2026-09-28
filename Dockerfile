FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy tests and helper scripts as well as the app so the documented in-container
# pytest and verification commands work from the same image.
COPY pyproject.toml ./
COPY app ./app
COPY tests ./tests
COPY scripts ./scripts
RUN pip install --upgrade pip && pip install ".[test]"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
