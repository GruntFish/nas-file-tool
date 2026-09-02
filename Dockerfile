FROM ubuntu:22.04

# 设置非交互式安装，避免卡住
ENV DEBIAN_FRONTEND=noninteractive

# 更新系统并安装依赖
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    jpegoptim \
    optipng \
    webp \
    && rm -rf /var/lib/apt/lists/*

# 安装 Flask
RUN pip3 install flask --break-system-packages

WORKDIR /app

COPY processor.py .
COPY app.py .
COPY templates/ ./templates/

EXPOSE 5000

VOLUME /data

CMD ["python3", "/app/app.py"]
