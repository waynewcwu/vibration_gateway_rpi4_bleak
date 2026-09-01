FROM --platform=$TARGETPLATFORM python:3.11-bookworm

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        git \
        libdbus-1-dev \
        libglib2.0-dev \
        nodejs \
        npm \
        tar \
        xz-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
