# Phase 8: Containerized Network Health Check Service (Python 3.11-slim)
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required by pyATS / Unicon SSH
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml README.md ./
COPY src/ ./src/
COPY test_data/ ./test_data/
COPY testbed/ ./testbed/

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt fastapi uvicorn \
    && pip install --no-cache-dir --no-build-isolation --no-deps -e .

EXPOSE 8000

CMD ["uvicorn", "network_health.api.app:create_fastapi_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
