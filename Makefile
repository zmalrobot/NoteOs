# ==============================================================================
# NoteOS — Makefile
# Thin wrapper invoking modular, reproducible scripts in scripts/
# ==============================================================================

SHELL := /usr/bin/env bash
MAKEFLAGS += -j$(shell nproc 2>/dev/null || echo 4)

.PHONY: all help check backup firmware repartition kernel rootfs boot install verify rollback clean check-clean

help:
	@echo "NoteOS Build and Management System"
	@echo ""
	@echo "Available Targets:"
	@echo "  make check        - Verify host tools, disk space, and device connectivity"
	@echo "  make backup       - Dump device partitions to private backup directory"
	@echo "  make firmware     - Extract proprietary Wi-Fi/BT firmware to proprietary/"
	@echo "  make repartition  - (Dry-run) Check eMMC partition table layout"
	@echo "  make kernel       - Fetch, patch, and compile Linux kernel"
	@echo "  make rootfs       - Build clean Debian 12 armhf rootfs tarball"
	@echo "  make boot         - Package boot.img and boot-debug.img with 7.5 MiB check"
	@echo "  make install      - Flash NoteOS to device in TWRP (use with --dry-run / --full)"
	@echo "  make verify       - Verify post-installation device integrity"
	@echo "  make rollback     - Restore BOOT/RECOVERY from backup"
	@echo "  make check-clean  - Run repository privacy and cleanliness guard"
	@echo "  make clean        - Remove build artifacts and temporary files"

check:
	./scripts/00_check_prerequisites.sh

backup:
	./scripts/01_backup_device.sh

firmware:
	./scripts/02_extract_firmware.sh

repartition:
	./scripts/03_repartition.sh --dry-run

kernel:
	./scripts/04_build_kernel.sh

rootfs:
	./scripts/05_build_rootfs.sh

boot:
	./scripts/06_build_boot_image.sh

install:
	./scripts/07_install.sh --dry-run

verify:
	./scripts/08_verify_install.sh

rollback:
	./scripts/09_rollback.sh --dry-run

check-clean:
	./scripts/lib/check_repo_clean.sh

clean:
	rm -rf out .work logs *.log build/initramfs_root build/rootfs

