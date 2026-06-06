# Boot Image Inputs

Place trusted seed/current boot images here when restoring a workspace. Verify
against public SHA manifests before flashing or rebuilding derivatives.

Current baseline boot images may also be written here by builders when they are
used as the next build or rollback input. Ramdisk directories, cpio files, and
compiled init/helper binaries stay under `../../builds/`.
