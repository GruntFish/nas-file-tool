FROM alpine:latest

# 1. 安装系统工具
RUN apk add --no-cache \
    python3 \
    py3-pip \
    jpegoptim \
    optipng \
    libwebp-tools \
    && rm -rf /var/cache/apk/*

# 2. 创建虚拟环境，在里面装 flask（绕过系统保护）
RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir flask

# 3. 把虚拟环境的命令加到 PATH（这样直接用 flask、python3 就行）
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY processor.py .
COPY app.py .
COPY templates/ ./templates/

EXPOSE 5000

VOLUME /data

CMD ["python3", "/app/app.py"]
