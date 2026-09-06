FROM python:3.11-alpine

RUN apk add --no-cache tzdata \
    && cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone \
    && apk del tzdata

RUN apk add --no-cache \
    jpegoptim \
    optipng \
    libwebp-tools \
    && rm -rf /var/cache/apk/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data

EXPOSE 8658

CMD ["python", "app.py"]
