# S20+ TWRP observation and UniLoader preparation

The exact `SM-G986N / y2q / y2qksx / G986NKSS8IYC2` reached
`PROVED_S20PLUS_G986N_TWRP_BASELINE_HEALTHY` at 22:20:25 KST on
2026-11-22. ADB reported recovery and the retained T2 identity for
TWRP `3.7.1_12-AstroForge_v2`. The observed `boot` capacity was
67,108,864 bytes. The observer opened zero block devices and read
zero bytes of partition content. It completed eight bounded host ADB
invocations, five addressed to S20+ and zero to any other target.
The action guard was released. Reboots, writes, mode transitions and
partition transfers were all zero.

## Capture binding and independent review

The T2 source closure expected the 25,006-byte capture helper from Git
`c41fd1ddf7` at SHA-256
`410e260129c0c50dca29b008dc7cf1051ee007816ab18bea76aeae62505ca0e4`.
Later S22+ changes modified the shared file, which stopped the original
S20+ checker before ADB. The
[S20+ observer launcher](../../workspace/public/src/scripts/revalidation/s20plus_g986n_twrp_observe_source_view_v1.py)
mounts the original capture helper and the pinned S20+ transport at the
paths the historical checker expects. The two source mounts and the new
qualification are read-only inside its private mount namespace. The
launcher calls the existing baseline with its fixed `--observe` mode.
The original source closure, shared checkout files, historical evidence
and historical review files are preserved.

Independent review returned `PASS_GO` for launcher SHA-256
`8b6a22bb1cceccbc6ba5870fe803f4f0a2cee47e4b7d5f6a8f2a7c0c48d685e7`
and test SHA-256
`35f886fd0c196994a792db28997f03031ee2fbacfae5b0feb5cd87a0c7a5144e`,
with zero open findings. The final view supplies private temporary
storage and standard device nodes so the bounded capture can open its
temporary files and `/dev/null`. Actual bounded host capture, retained
T2 host validation, both qualification readers, Python compilation,
28 baseline tests and five launcher tests passed before the device read.
The launcher tests exercised the live argument construction on the
enrolled host with its existing S20+ run directory.

The reviewed capture bytes, H0 input, test log and qualification are in
`workspace/private/outputs/s20plus_g986n/twrp_observe_source_view_v1/`.
The live baseline result is bound by SHA-256
`6755cdf623b398334ac3c9218df3192b61beeb742a442d7d5e9ca234c714f4fd`.
The consumed P2 owner is separate from this read-only observation.

## UniLoader and original Magisk boot

The [candidate and original Magisk rollback pair](S20PLUS_G986N_UNILOADER_PHYSICAL_PREPARATION_H0_2026-11-22.md#artifacts-and-observer)
passed a fresh host audit. Each AP contains only `boot.img.lz4`.
Both decompressed images match their pinned SHA-256 and the observed
64 MiB capacity. The rollback matches the retained resident Magisk AP.
The private `physical-preparation.json` links the exact pair, observation,
and review. Its SHA-256 is
`d33215de7d829ecc8523f5a7c8d3825abde9137675c85c7f799d2a3da484f99a`.

Live F1 preparation still needs a reviewed and activated UniLoader owner,
demonstrated current physical Download fallback, and a finite attended
grant. The owner's proof sequence is a new Magisk Android boot through
UniLoader with the matching FDT property, followed by one original AP
restore and a fresh rooted Android boot with the marker absent. The
connected read proves the TWRP starting state. Android boot, FDT marking
and original-boot restoration remain to be demonstrated on the device.
