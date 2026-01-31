FROM python:3.12-slim

WORKDIR /app

# 安装 Node.js（用于运行官方 MCP Server）
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 创建 sandbox 目录
RUN mkdir -p /app/sandbox

CMD ["python", "main.py"]
