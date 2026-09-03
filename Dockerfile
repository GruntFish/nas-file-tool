FROM alpine:latest

RUN apk add --no-cache \
    python3 \
    py3-pip \
    jpegoptim \
    optipng \
    libwebp-tools \
    imagemagick \
    && rm -rf /var/cache/apk/*

RUN apk add --no-cache gcc musl-dev python3-dev && \
    python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir flask croniter && \
    apk del gcc musl-dev python3-dev

ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY processor.py .
COPY app.py .
COPY core/ ./core/
COPY modules/ ./modules/
COPY templates/ ./templates/
COPY favicon.ico .

EXPOSE 8668

VOLUME /data

CMD ["python3", "/app/app.py"]
