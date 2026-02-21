# FROM python:3.11-slim

# WORKDIR /app

# # Install system dependencies (minimal)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     gcc \
#     postgresql-client \
#     && rm -rf /var/lib/apt/lists/*

# # Copy only requirements first (for caching)
# COPY requirements.txt .

# # Install Python packages
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy only app directory (not entire context)
# COPY app/ ./app/

# # Create __init__.py if missing
# RUN touch ./app/__init__.py

# # Expose port
# EXPOSE 8001

# # Health check
# HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
#     CMD python -c "import requests; requests.get('http://localhost:8001/health')" || exit 1

# # Run application
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
RUN touch ./app/__init__.py

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]