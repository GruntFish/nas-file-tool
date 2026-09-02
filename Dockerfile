FROM alpine:latest

# 安装系统工具和 Python
RUN apk add --no-cache \
    python3 \
    py3-pip \
    jpegoptim \
    optipng \
    libwebp-tools \
    && rm -rf /var/cache/apk/*

# 用 pip 安装 Flask
RUN pip3 install --no-cache-dir flask

WORKDIR /app

COPY processor.py .
COPY app.py .
COPY templates/ ./templates/

EXPOSE 5000

VOLUME /data

CMD ["python3", "/app/app.py"]
