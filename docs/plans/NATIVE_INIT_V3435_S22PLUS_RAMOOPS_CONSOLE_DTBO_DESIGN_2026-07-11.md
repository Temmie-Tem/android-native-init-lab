# V3435 S22+ Ramoops Console/Dmesg DTBO Design

## Verdict

`HOST_BUILD_PASS_NO_LIVE`.

V3435 corrects the S22+ observability substrate before more direct-PID1, USB,
or distro work. The final product target remains native/Debian without Android
userspace. The stock-global-PID1 service-supervisor path is an interim bring-up
and recovery fallback, not the final architecture.

This unit is host-only. It contacted no device, rebooted nothing, and performed
no flash or partition write. It authorizes no live action.

Machine-readable contract:

```text
docs/plans/s22plus-v3435-ramoops-console-dtbo-contract.json
```

## Root Cause

All four exact FYG8 vendor DTB variants contain the same ramoops allocation:

```text
compatible   = "ramoops"
size         = 0x200000       # 2 MiB
pmsg-size    = 0x200000       # consumes all 2 MiB
console-size = absent
record-size  = absent
ftrace-size  = absent
reg          = absent         # dynamic reserved-memory allocation
```

The pinned running Magisk kernel has `CONFIG_PSTORE`, `CONFIG_PSTORE_RAM`,
`CONFIG_PSTORE_CONSOLE`, and `CONFIG_PSTORE_PMSG` enabled. Its exact ramoops
source parses missing frontend-size properties as zero and computes:

```text
dmesg_size = region_size - console_size - ftrace_size - pmsg_size
```

The stock result is therefore zero console space and zero dmesg record space.
The previous status-only DTBO live PASS enabled a pmsg-only backend. Empty
`console-ramoops`/`dmesg-ramoops` results from M13/M18/M22 did not test a
console or dmesg frontend and do not retire ramoops retention.

`console=null` is not changed. Once a nonzero `console-size` causes the ramoops
backend to advertise `PSTORE_FLAGS_CONSOLE`, pstore registers its own console
with `CON_PRINTBUFFER | CON_ENABLED | CON_ANYTIME`.

## Selected Layout

The existing 2 MiB allocation remains unchanged:

| Frontend | Size |
|---|---:|
| pmsg | 1 MiB (`0x100000`) |
| console | 512 KiB (`0x80000`) |
| dmesg total | 512 KiB (`0x80000`) |
| dmesg record | 256 KiB (`0x40000`) |
| dmesg records | 2 |
| ftrace | 0 |

Every nonzero configured size is a power of two and the sum is exactly 2 MiB.
Keeping 1 MiB for pmsg limits the temporary Android-side reduction while still
creating a useful continuous console and two panic/oops records.

## DTBO Construction

Stock DTBO entries 9 and 10 both target the `ramoops_mem` fixup at
`fragment@116`. V3435 adds only these properties to each target overlay:

```text
status       = "okay"
pmsg-size    = <0x100000>
console-size = <0x80000>
record-size  = <0x40000>
```

Straight `fdtput` growth would move Samsung's 512-byte `SignerVer02` trailer.
The builder therefore compacts each target FDT property-name string table using
legal suffix sharing, then pads the FDT back to its exact original entry size.
Each overlay recovers 140 string-table bytes, needs 79 bytes for the new
properties, and ends with 61 bytes of FDT trailing padding.

The resulting invariants are:

- raw partition image remains exactly 8 MiB;
- DT table header, total size, 11 entry sizes, and 11 entry offsets are unchanged;
- non-target entries are byte-identical;
- target entries differ semantically only at the four allowlisted properties;
- Samsung's 512-byte signer trailer is byte-identical and stays at the same offset;
- all bytes after the DT table, including AVB metadata/footer, are byte-identical;
- each patched overlay applies successfully to every one of the four vendor DTBs;
- candidate and rollback Odin APs each contain only `dtbo.img.lz4`.

The payload change intentionally invalidates the stock AVB hash descriptor.
The AVB metadata is preserved, not forged or re-signed. A future live gate must
reverify the already established disabled-verification/orange baseline, but
that precondition does not authorize a flash.

## Pinned Candidate

```text
raw DTBO SHA256
  3c4d38a9d4833bab648cd36c3c0c78a2bfed35ca80dc4532b5e877cbaa8fa281

dtbo.img.lz4 SHA256
  4202edca2a0d06ab691c492151b5f4228b1bd28eace06b1a72c36e35cac7c84b

candidate AP.tar.md5 SHA256
  622ac0259eb61a7c9ef71eff44d4ea8bb3edbc6a90c3f2b237be7fdf88cb0264

stock rollback raw DTBO SHA256
  97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
```

Private artifact root:

```text
workspace/private/outputs/s22plus_v3435_ramoops_console_dtbo_v0_1/
```

## Future Live Gate

The first future live run must be a true Android positive control, not another
direct-PID1 candidate:

1. Require the known Magisk boot baseline and stock DTBO rollback artifact.
2. Flash only the exact V3435 candidate under a fresh SHA-pinned exception.
3. Require Android/root return and exact candidate DTBO readback.
4. Require live DT values for status and all three sizes.
5. Require ramoops backend/parameter registration before any fault.
6. Emit a fresh run-bound marker to kmsg and pmsg.
7. Under a separate one-shot exception, trigger exactly one intentional panic.
8. Recover console, dmesg, and pmsg records before restoring stock DTBO.
9. Restore stock DTBO and prove the clean baseline.

PASS requires the exact run-bound marker in a retained ramoops record. PASS
reopens a module-free direct-PID1 witness. Failure after proven backend
registration retires ramoops and moves the witness track to EUD/UART.

No such exception or live helper is created by V3435.
