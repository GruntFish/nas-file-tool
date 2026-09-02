FROM alpine:latest

RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-flask \
    jpegoptim \
    optipng \
    cwebp \
    && rm -rf /var/cache/apk/*

WORKDIR /app

COPY processor.py .
COPY app.py .
COPY templates/ ./templates/

EXPOSE 5000

VOLUME /data

CMD ["python3", "/app/app.py"]