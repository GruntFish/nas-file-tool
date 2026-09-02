FROM alpine:latest

# 安装系统工具和 Python
RUN apk add --no-cache \
    python3 \
    py3-pip \
    jpegoptim \
    optipng \
    cwebp \
    && rm -rf /var/cache/apk/*

# 用 pip 安装 Flask（Alpine 的 py3-flask 包有问题）
RUN pip3 install --no-cache-dir flask

WORKDIR /app

COPY processor.py .
COPY app.py .
COPY templates/ ./templates/

EXPOSE 5000

VOLUME /data

CMD ["python3", "/app/app.py"]
