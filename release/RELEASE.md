# NoteOS 1.0 Release Artifacts

This directory contains pre-compiled, deterministic kernel boot images and release manifests for Samsung Galaxy Note 10.1 (GT-N8000).

## Release Files in this Directory
- **`boot.img`** (`7,350,272` bytes, <= 7.5 MiB)
  - Production release kernel image.
  - Zero debug code, silent boot, Plymouth graphical boot splash enabled.
  - SHA256: `6de03d4f2a2ba5bfe96bea21fe30d34f1f30972597195485293fed583c2d6863`
- **`boot-debug.img`** (`7,358,464` bytes, <= 7.5 MiB)
  - Diagnostic kernel image.
  - Verbose serial console (`ttySAC2,115200`), transient USB RNDIS networking (`192.168.3.2`), and SSH on RAM-backed overlay.
  - SHA256: `45e824aac58d8a10d2d1569d00b7c82212e092247a8525bbc9c7c0c12cc78552`
- **`SHA256SUMS`**: Cryptographic checksum verification file.
- **`manifest.txt`**: Complete artifact manifest.

## Obtaining the Rootfs Archive (`rootfs.tar.gz`)
Due to Git file size limits (GitHub limits files to 100 MB), the complete base Debian 12 root filesystem archive (`rootfs.tar.gz`, ~430 MiB) is **not tracked directly in the Git repository**.

You can obtain the rootfs in one of two ways:

### Option 1: Download from GitHub Releases (Recommended)
Download `noteos-n8000-1.0-rootfs.tar.gz` from the official [NoteOS GitHub Releases](https://github.com/zmalrobot/NoteOs/releases) page and place it as `release/rootfs.tar.gz`:
```bash
# Verify checksum after download:
sha256sum release/rootfs.tar.gz
```

### Option 2: Build from Source
You can build the exact bit-for-bit reproducible rootfs locally in minutes using Docker/Podman:
```bash
./scripts/05_build_rootfs.sh
```
The output will be placed in `out/n8000/rootfs.tar.gz`.

