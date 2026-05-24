# Native Init V775 Boot Incompatibility Postmortem Plan

## Goal

Classify the remaining V774 custom-kernel boot failure without another live
flash.

## Inputs

- known-good boot image: `stage3/boot_linux_v724.img`
- known-good kernel payload: `tmp/wifi/v770-instrumented-diagnostic-boot-staging/base-unpack/kernel`
- V773 diagnostic boot image: `tmp/wifi/v773-stock-dtb-tail-repack/boot_linux_v773_icnss_diag_stockdtb.img`
- V773 diagnostic kernel payload: `tmp/wifi/v773-stock-dtb-tail-repack/instrumented-image-with-stock-dtb-tail.bin`
- V774 failure report: `docs/reports/NATIVE_INIT_V774_STOCK_DTB_TAIL_LIVE_BOOT_FAIL_2026-05-25.md`
- kernel config extracts: `tmp/wifi/v772-boot-incompat-classifier/logs/base-ikconfig.txt`, `tmp/wifi/v772-boot-incompat-classifier/logs/diag-ikconfig.txt`

## Rules

- Host-only analysis only.
- No device command, boot partition write, flash, reboot, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, or external ping.
- Do not retry V770, V773, or any equivalent Samsung OSRC-built custom kernel image as-is.
- Treat tracepoint/BPF checks as selection of a future read-only live gate, not as V775 live work.

## Checks

1. Confirm V774 is documented and rollback is complete.
2. Compare v724 and V773 boot header arguments after normalized unpack.
3. Compare v724 and V773 kernel payload size, FDT offsets, and pre-DTB size delta.
4. Compare Linux version/provenance strings and embedded config observability surface.
5. Count production/security marker strings (`RKP`, `CFP`, `RTIC`, `DEFEX`, `KNOX`, `PROCA`, `FIVE`) as a coarse host-only signal.
6. Classify stock-kernel observability options from config: kprobes, dynamic debug, function tracer, tracepoints, and BPF syscall.

## Success Criteria

- The classifier confirms the missing DTB tail is no longer the only blocker.
- The classifier preserves the no-flash rule and selects a safer stock-kernel
  observability path.
- Output is written to private `tmp/wifi/v775-boot-incompat-postmortem/`
  evidence with `manifest.json` and `summary.md`.

## Next If Classified

V776 should use the stock v724 kernel only and perform a bounded read-only
tracepoint inventory: mount/read/cleanup tracefs if required, capture
`available_events`, identify any ICNSS/WLAN/QMI/QRTR tracepoint candidates, and
only then decide whether a BPF tracepoint attach proof is useful. No custom
kernel flash should be attempted before a separate host-only compatibility gate
explains the V774 failure.
