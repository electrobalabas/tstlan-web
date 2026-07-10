FROM python:3.13-slim

WORKDIR /app

RUN set -eux; \
    apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY tests/fixtures/native_unidriver.c /app/native_unidriver.c
COPY tests/docker/unidriver/server.py /app/server.py

RUN set -eux; \
    gcc -shared -fPIC /app/native_unidriver.c -o /app/libunidriver.so; \
    python -c "import ctypes; ctypes.CDLL('/app/libunidriver.so')"

EXPOSE 9000

CMD ["python", "/app/server.py", "--host", "0.0.0.0", "--port", "9000", "--library", "/app/libunidriver.so"]
