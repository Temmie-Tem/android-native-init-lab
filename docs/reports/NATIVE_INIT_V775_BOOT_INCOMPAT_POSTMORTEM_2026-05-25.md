# Native Init V775 Boot Incompatibility Postmortem Report

## Result

- decision: `v775-non-dtb-custom-kernel-incompat-classified`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_boot_incompat_postmortem_v775.py`
- evidence: `tmp/wifi/v775-boot-incompat-postmortem/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_boot_incompat_postmortem_v775.py
python3 scripts/revalidation/native_wifi_boot_incompat_postmortem_v775.py plan
python3 scripts/revalidation/native_wifi_boot_incompat_postmortem_v775.py run
```

## Evidence Summary

| Signal | v724 stock | V773 diagnostic |
| --- | --- | --- |
| boot header args | match after normalized unpack | match after normalized unpack |
| kernel size | `49827613` | `49827629` |
| size delta | baseline | `+16` bytes |
| FDT count | `3` | `3` |
| FDT offsets | `48830500`, `49327831`, `49827440` | `48830516`, `49327847`, `49827456` |
| pre-DTB payload delta | baseline | `+16` bytes |
| `A90V765` marker count | `0` | `19` |
| production marker coarse delta | `RKP=6`, `RTIC=3` | `RKP=7`, `RTIC=2` |

Version strings differ:

- v724 stock: `Linux version 4.14.190-25818860-abA908NKSU5EWA3 ... clang version 10.0.7 ... Thu Jan 12 18:53:40 KST 2023`
- V773 diagnostic: `Linux version 4.14.190 ... clang version 10.0.6 ... Mon May 25 01:27:22 KST 2026`

Kernel config observability surface matches between the extracted v724 and
diagnostic configs:

| Config | Value |
| --- | --- |
| `CONFIG_KPROBES` | `n` |
| `CONFIG_DYNAMIC_DEBUG` | `n` |
| `CONFIG_FTRACE` | `y` |
| `CONFIG_FUNCTION_TRACER` | `n` |
| `CONFIG_TRACEPOINTS` | `y` |
| `CONFIG_BPF_SYSCALL` | `y` |
| `CONFIG_BPF_EVENTS` | `y` |

## Interpretation

V775 closes the missing-DTB explanation as the only root cause. V773/V774 proved
the diagnostic image contains an appended DTB tail and uses boot header metadata
matching v724, but it still failed live boot.

The remaining host-only differences are now narrower:

1. the diagnostic kernel pre-DTB payload is `16` bytes larger, shifting every
   appended FDT offset by `16` bytes;
2. the kernel provenance/toolchain string differs from Samsung production stock;
3. coarse production/security marker counts differ for `RKP` and `RTIC`;
4. Samsung production transforms or bootloader acceptance metadata remain
   unproven for the locally built OSRC kernel.

That is enough to pause the custom-kernel flashing route. Repeating V770, V773,
or an equivalent OSRC-built kernel image is not justified until a separate
host-only compatibility gate explains these differences or produces a safer
artifact contract.

## Observability Route

The stock v724 kernel still leaves one useful route: static tracepoints.
`kprobes`, dynamic debug, and function ftrace filtering are unavailable, but
`CONFIG_TRACEPOINTS=y` and `CONFIG_BPF_SYSCALL=y` make a bounded read-only
tracepoint inventory the next practical gate. BPF tracepoint attach remains only
a candidate until live feasibility is proven.

## Safety

- device command: not executed
- partition write/flash/reboot: not executed
- Wi-Fi HAL/scan/connect/credential use: not executed
- DHCP/routes/external ping: not executed

## Next

V776 should use the recovered stock v724 native boot and perform only bounded
read-only tracepoint inventory: capture `available_events`, search for
ICNSS/WLAN/QMI/QRTR candidates, and classify whether a later BPF tracepoint
attach proof is worth attempting. No custom kernel flash before a new
compatibility classifier explains V774.
