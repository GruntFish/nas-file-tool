FROM python:3.11-alpine

# ===== 安装最小化依赖 =====
# 【修复】vips-tools 改为 vips-dev，或者直接安装 vips
RUN apk add --no-cache \
    jpegoptim \
    optipng \
    webp-tools \
    vips \
    vips-dev \
    && rm -rf /var/cache/apk/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && find /usr/local/lib/python3.11/site-packages -name "*.pyc" -delete \
    && find /usr/local/lib/python3.11/site-packages -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

COPY . .

RUN mkdir -p /data

EXPOSE 8658

CMD ["python", "app.py"]
