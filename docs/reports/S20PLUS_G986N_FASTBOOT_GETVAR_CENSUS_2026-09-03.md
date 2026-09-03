# S20+ G986N classic-fastboot read-only census

State: **PASS - FOUR FIXED GETVARS; HEALTHY ANDROID RETURN**

## Scope

The attended ordinal-2 replacement ran only on the exact operator-owned
`SM-G986N/y2q/y2qksx/G986NKSS8IYC2`. It sent no command to S22+, A90, or any
other attached target. Ordinal 1 had previously ended `NO_PROOF` with zero
fastboot commands and remains immutably consumed.

The operator manually selected Magisk's bootloader reboot. The runner accepted
only the same-topology `18d1:d00d` classic-fastboot endpoint with one
`ff/42/03` interface and the reviewed bulk endpoint pair. It sent exactly these
four read-only commands and nothing else:

1. `getvar product` -> `kona`
2. `getvar is-userspace` -> `no`
3. `getvar version-bootloader` -> successful empty value
4. `getvar max-download-size` -> `805306368` (`0x30000000`, 768 MiB)

`is-userspace=no` proves this observed endpoint is bootloader fastboot rather
than fastbootd. The empty bootloader-version value is retained without further
interpretation. These observations do not prove that the optional
`fastboot boot` command is implemented or safe.

## Safety and terminal

- Fastboot command count: 4; all were the fixed `getvar` list.
- Download, payload, boot, flash, erase, unlock, partition, root, and host
  reboot commands: 0.
- All ADB and fastboot streams were captured privately before parsing.
- The operator returned using the physical `START` selection.
- Final health proved a fresh boot of the same exact target, Android
  `boot_completed=1`, stopped boot animation, and SELinux `Enforcing`.
- The shared S20+ action guard is absent. Ordinal 2 is consumed; no third
  ordinal is defined.

Private structured evidence:

- `workspace/private/runs/s20plus-g986n-fastboot-getvar-census/census-20260902T151105Z-1788361865846027780/probe-result.json`
  - size 3,907; SHA-256
    `1369b7a29b2ba7c5589be0cee89a1f09a865c344d0a6dce9c99967f5e2177ba8`
- `workspace/private/runs/s20plus-g986n-fastboot-getvar-census/census-20260902T151105Z-1788361865846027780/final-result.json`
  - size 1,538; SHA-256
    `d9a0d858ee8030274f91deba3fbb2a5bedc667b93732dc43cafa451fb5a6184a`

Terminal verdict:
`PASS_S20PLUS_G986N_FASTBOOT_GETVAR_CENSUS_RETURN_HEALTHY`.
