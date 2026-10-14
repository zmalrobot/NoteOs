FROM docker.io/library/debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive

RUN dpkg --add-architecture armhf && apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    crossbuild-essential-armhf \
    gcc-arm-linux-gnueabihf \
    bison \
    flex \
    bc \
    libssl-dev \
    libelf-dev \
    device-tree-compiler \
    u-boot-tools \
    python3 \
    python3-pip \
    cpio \
    kmod \
    rsync \
    git \
    wget \
    curl \
    xz-utils \
    zstd \
    pigz \
    busybox-static:armhf \
    mmdebstrap \
    qemu-user-static \
    binfmt-support \
    e2fsprogs \
    dosfstools \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY tools/mkbootimg.py /usr/local/bin/mkbootimg
RUN chmod +x /usr/local/bin/mkbootimg

WORKDIR /work

