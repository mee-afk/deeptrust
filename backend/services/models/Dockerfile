FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for OpenCV (updated package names for Debian trixie)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Remove dlib from requirements (not essential for demo)
RUN sed -i '/dlib/d' requirements.txt

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
RUN touch ./app/__init__.py

EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]