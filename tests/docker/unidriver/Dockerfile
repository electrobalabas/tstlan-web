FROM python:3.14-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY tests/fixtures/native_unidriver.c /app/native_unidriver.c
COPY tests/docker/unidriver/server.py /app/server.py

RUN gcc -shared -fPIC /app/native_unidriver.c -o /app/libunidriver.so

EXPOSE 9000

CMD ["python", "/app/server.py", "--host", "0.0.0.0", "--port", "9000", "--library", "/app/libunidriver.so"]
