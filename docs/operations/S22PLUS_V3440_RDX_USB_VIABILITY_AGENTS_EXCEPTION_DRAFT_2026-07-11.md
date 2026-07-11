# S22+ V3440 RDX USB Viability Exception Draft

`DRAFT_INACTIVE` — this document is a policy proposal only. It authorizes no
device contact, panic, USB protocol command, flash, reboot, or dump retrieval.

## Proposed AGENTS.md Clause

**Narrow operator-authorized exception (2026-07-11, S22+ V3440 RDX USB
viability live gate):** after V3439 proved one attended SysRq panic reaches the
Samsung RDX kernel-panic screen but ramoops retains no current-run frame, Codex
may perform one bounded attended zero-flash RDX USB viability run on the
Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the checked helper
`workspace/public/src/scripts/revalidation/s22plus_v3440_rdx_usb_viability_gate.py`
SHA256 `cab62dcc89cb7f39d16e99b3d19106f1e5a418436d05a6d5fa7076aab136e4f8`.
The active clause must contain sentinel
`S22PLUS_V3440_RDX_USB_POLICY_STATE=ACTIVE`, and the operator must supply both
acknowledgements `S22PLUS-V3440-RDX-ONE-SYSRQ-PANIC` and
`S22PLUS-V3440-RDX-TWO-COMMAND-USB-PROBE`.

The current Android boot partition must first equal the known-booting Magisk
boot SHA256
`2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`,
the current DTBO must equal stock SHA256
`97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`,
Android identity/boot completion/Magisk root must pass, and exactly one ADB
target must be present. The host protocol references are pinned to
`bkerler/sboot_dump` commit
`8c9f6eb79ffbe702152ca7810f6382bf5e1bfd58` and `linux-msm/qdl` commit
`a00d81bc639908875862582f0d3cb0775d92e269`.
The private host runtime must use PyUSB `1.2.1` from wheel SHA256
`2b4c7cb86dbadf044dfb9d3a4ff69fd217013dbe78a792177a3feb172449ea36`
and prove a usable libusb-1.0 backend before the panic is armed.

The helper may write one run marker to `/dev/kmsg`, write `1` to
`/proc/sys/kernel/sysrq`, and write `c` once to `/proc/sysrq-trigger` to cause
one intentional panic. It may then observe host USB sysfs for at most 120
seconds. Only if exactly one Samsung S-Boot RDX endpoint `04e8:685d` appears may
it transiently detach and later reattach that endpoint's CDC-data kernel
driver and send exactly `PrEaMbLe\0`, require exact positive response
`AcKnOwLeDgMeNt\0`, then send exactly `PrObE\0` and receive at most 32768 bytes
of upload-area metadata. A negative or malformed acknowledgement must stop
before `PrObE`. The helper must never send `DaTaXfEr`, address ranges,
`PoWeRdOwN`, acknowledgements for data chunks, or any other S-Boot command.

If exact Qualcomm crash-dump endpoint `05c6:900e` appears, the helper may only
record that identity and stop; it must not invoke `qdl`, Sahara collection, a
programmer, Firehose, or any transfer in this gate. Any other USB identity is
`NO_PROOF_NO_RDX_USB_ENDPOINT`. The operator must physically use RDX EXIT after
the bounded observation and the helper must re-verify the unchanged Magisk
boot and stock DTBO hashes after Android returns. There is no candidate flash
and no rollback flash in this run; the mandatory timeline phase names are
retained with explicit `no_candidate_flash`/`no_rollback_flash` semantics.

This exception authorizes no RAM range or full dump, no partition-table or
storage operation, no device-memory write, no Odin, no boot/recovery/DTBO/
vendor_boot/vbmeta/BL/CP/CSC/super/userdata/EFS/sec_efs/RPMB/keymaster/modem/
bootloader flash, no raw host `dd`, no fastboot, no Magisk module, no EUD/UART
write, no format data, no native-init candidate, and no A90 action. The one
panic is not retryable under this clause. A positive probe only authorizes a
separately designed host-only bounded-dump unit; it does not authorize that
future transfer. `S22+ V3440 RDX USB viability live gate` is the policy marker.
