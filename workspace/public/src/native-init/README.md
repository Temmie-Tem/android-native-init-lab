# Current Native Init Source

This directory is the canonical source root for the current native-init baseline.
It contains the V726 source closure: shared `a90_*` modules, `init_v724.c`,
`init_v725_fasttransport.c`, the `v319/` and `v724/` include modules, and
current helper source files.

Historical `init_v*` files remain under
`workspace/public/archive/stage3/linux_init/`. Moved current files are kept
there as compatibility symlinks for historical scripts.

Generated binaries do not belong here. They are ignored and should be written to
`workspace/private/builds/native-init/`.
