# Dockerfile
FROM python:3.11-slim

# 安装系统依赖（包括媒体处理工具）
RUN apt-get update && apt-get install -y \
    jpegoptim \
    optipng \
    webp \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY . .

# 创建数据目录
RUN mkdir -p /data

# 暴露端口
EXPOSE 8658

# 启动命令
CMD ["python", "app.py"]
