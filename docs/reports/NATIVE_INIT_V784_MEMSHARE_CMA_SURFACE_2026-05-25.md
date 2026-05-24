# Native Init V784 Memshare/CMA Surface Report

## Result

- decision: `v784-native-memshare-cma-surface-classified`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_memshare_cma_surface_v784.py`
- evidence: `tmp/wifi/v784-memshare-cma-surface/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_memshare_cma_surface_v784.py
python3 scripts/revalidation/native_wifi_memshare_cma_surface_v784.py plan
python3 scripts/revalidation/native_wifi_memshare_cma_surface_v784.py run
```

V784 used the existing serial bridge and executed read-only commands only.

## Evidence Summary

| Signal | Value |
| --- | --- |
| runtime | `A90 Linux init 0.9.68 (v724)` |
| device mutating commands | `false` |
| Wi-Fi trigger | `false` |
| `CmaTotal` | `293601280` bytes |
| `CmaFree` | `243380224` bytes |
| `MemAvailable` | `5239176` kB |
| `firmware_class.path` | `/vendor/firmware_mnt/image` |
| `service_locator.enable` | `1` |
| `androidboot.cp_reserved_mem` | `off` |
| memshare sysfs | present |
| `client_4` | present |
| `client_4` size-zero marker | present |
| `client_4` no-clients marker | present |
| `linux,cma` reserved node | present |
| `pil_wlan_fw_region` | present |
| `mhi_region` | present |
| debugfs CMA surface | absent without mounting debugfs |

## V782 Failure Comparison

| Signal | Value |
| --- | --- |
| V782 request sizes | `100663296`, `33554432` bytes |
| V782 failed sizes | `100663296`, `33554432` bytes |
| V782 CMA failure | `8192` pages, `-12`, `33554432` bytes |
| V782 request sum | `134217728` bytes |
| current idle `CmaFree >= V782 sum` | `true` |

## Interpretation

V784 makes the memshare lead more specific.  The native runtime has visible
memshare platform sysfs, `client_4`, CMA, and relevant reserved-memory nodes.
Current idle `CmaFree` is larger than the V782 request sum, so the V782 failure
is not explained by a simple always-too-small idle CMA pool.

The better hypothesis is now narrower:

```text
modem sysmon window
  -> memshare client_4 / client id 3 requests 96 MiB and 32 MiB
  -> allocation fails despite idle CMA headroom existing after reboot
  -> service-notifier 74/180 never appears
```

That points to client registration, reserved-pool ownership, or timing under the
modem/sysmon transition.  The current native boot dmesg also includes
`client_id 3 / size 0` and `no memshare clients registered` markers for
`client_4`, which should be compared against Android with the same memshare/CMA
filters.

## Safety

- boot image or partition write: not executed
- reboot: not executed
- mount/unmount: not executed
- bind/unbind or `driver_override`: not executed
- module load/unload: not executed
- `boot_wlan` or `qcwlanstate ON`: not executed
- service-manager/Wi-Fi HAL: not executed
- scan/connect/credential use: not executed
- DHCP/routes/external ping: not executed

## Next

V785 should recapture Android and native logs with explicit memshare/CMA filters
and map `client_4` / client id `3` registration before any further `boot_wlan`,
`qcwlanstate`, daemon ordering, HAL, scan/connect, external ping, or custom
kernel flashing.
