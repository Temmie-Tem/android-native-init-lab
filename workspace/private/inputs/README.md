# Private Inputs

Restore private inputs here after a fresh clone.

Expected subdirectories:

- `firmware/` — proprietary firmware/vendor extracts.
- `boot_images/` — trusted seed/current boot images and SHA sidecars.
- `toolchains/` — local cross toolchains when not provided by system packages.
- `external_tools/` — static userland helpers such as busybox, toybox, a90_tcpctl, a90_usbnet.
- `kernel_source/` — Samsung/open-source kernel source or build tree snapshots.

Do not commit restored contents. Publish only redacted manifests and SHA metadata.
