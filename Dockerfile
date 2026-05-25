# ---------------------------------------------------------------------------
# BhoomiSatya - AI Property Verification Service
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS base

# System dependencies for WeasyPrint (PDF generation) and general build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        libglib2.0-0 \
        shared-mime-info \
        fonts-noto \
        fonts-noto-cjk \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --create-home appuser

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# Install Playwright browsers (Chromium only — used for portal scraping)
RUN playwright install --with-deps chromium

# Copy application code and data
COPY src/ ./src/
COPY data/ ./data/

# Switch to non-root user
USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
