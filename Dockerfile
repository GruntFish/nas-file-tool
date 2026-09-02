FROM alpine:latest

RUN apk add --no-cache \
    python3 \
    py3-pip \
    jpegoptim \
    optipng \
    libwebp-tools \
    && rm -rf /var/cache/apk/*

RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir flask

ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY processor.py .
COPY app.py .
COPY templates/ ./templates/
COPY favicon.ico .         

EXPOSE 5000

VOLUME /data

CMD ["python3", "/app/app.py"]
