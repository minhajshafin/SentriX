FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN rm -rf /app/build && cmake -S . -B build && cmake --build build -j

CMD ["/app/build/sentrix_proxy"]
