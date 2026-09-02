FROM python:3.9-bullseye

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        bluez \
        ca-certificates \
        curl \
        git \
        iputils-ping \
        libdbus-1-dev \
        libglib2.0-dev \
        nodejs \
        npm \
        tar \
        xz-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
