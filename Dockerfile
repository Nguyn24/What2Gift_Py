# Base image Python
FROM python:3.11-slim

# Cài công cụ cơ bản và Ollama
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://ollama.com/install.sh | sh && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Tạo thư mục app
WORKDIR /app

# Copy dependencies
COPY requirements.txt .

# Cài đặt thư viện Python
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn
COPY . .

# Tải sẵn model (tùy chọn — có thể đổi model khác)
RUN ollama pull llama3

# Mở cổng cho FastAPI
EXPOSE 8000

# Chạy Ollama + FastAPI song song
CMD ollama serve & uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}
