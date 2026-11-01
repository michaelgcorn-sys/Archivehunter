# Archive Hunter on Fly.io (or any host that runs containers)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
# The built-in browser (reads archive pages that block plain downloads) and the scan reader (OCR)
RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium tesseract-ocr tesseract-ocr-eng tesseract-ocr-deu fonts-dejavu-core ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

EXPOSE 8080
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
