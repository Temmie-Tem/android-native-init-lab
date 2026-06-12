# Native Init V2246 Post-FWREADY Tail Symbol/Source Map (2026-06-12)

## Scope

Host-only mapper over the V2245 public-safe tail stack, the bit-exact stock
`System.map`, and the checked kernel/qcacld source tree. No device I/O, no
flash, no BPF attach, no tracefs write, no Wi-Fi scan/connect, no network route
change, and no private raw helper output is published here.

Inputs:

- `workspace/private/runs/kernel/v2245-post-fwready-tail-inventory-20260612-114711/summary.json`
- `workspace/private/runs/kernel/v2197-stock-kallsyms/System.map`
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source`

Generated private summary:

- `workspace/private/runs/kernel/v2246-post-fwready-tail-symbol-source-map-20260612-115530/summary.json`
- `workspace/private/runs/kernel/v2246-post-fwready-tail-symbol-source-map-20260612-115530/post_fwready_tail_symbol_source_map.json`

## Result

Decision: `v2246-post-fwready-tail-symbol-source-map-pass`.

All seven V2245 post-FWREADY tail stack functions are now mapped to both stock
kallsyms entries and source definitions. This gives the next live sampler a
concrete target whitelist for post-FWREADY firmware_class/qcacld-HDD code-path
identity.

| Symbol | V2245 Stack Offset | Stock Address | Source Definition |
| --- | --- | --- | --- |
| `_request_firmware` | `+0x638/0x770` | `0xffffff80089b06a8` | `drivers/base/firmware_class.c:1221` |
| `request_firmware` | `+0x44/0x70` | `0xffffff80089b0640` | `drivers/base/firmware_class.c:1287` |
| `qdf_file_read` | `+0x3c/0xf0` | `0xffffff8008c741e0` | `qca-wifi-host-cmn/qdf/linux/src/qdf_file.c:27` |
| `qdf_ini_parse` | `+0x48/0x228` | `0xffffff8008c821b8` | `qca-wifi-host-cmn/qdf/src/qdf_parse.c:27` |
| `cfg_parse` | `+0x1330/0x13b8` | `0xffffff8008ca5018` | `qca-wifi-host-cmn/cfg/src/cfg.c:765` |
| `hdd_context_create` | `+0xd0/0xd58` | `0xffffff8008b26340` | `qcacld-3.0/core/hdd/src/wlan_hdd_main.c:11385` |
| `wlan_hdd_pld_probe` | `+0x250/0x370` | `0xffffff8008afec98` | `qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c:1499` |

## Interpretation

V2245 established the dynamic tail discriminator:

`FW_READY -> boot_wlan write -> firmware_class WCNSS_qcom_cfg.ini request/feed -> qcacld/HDD probe -> ICNSS register/cfg/mode/ini completion -> wlan0`

V2246 turns the observed qcacld/HDD worker stack into a source-backed target set.
The next live T1 unit should run a per-boot exact-slide PC/LR sampler during the
post-FWREADY firmware_class/qcacld-HDD tail and score `ctx_pc`/`ctx_lr` hits
against this whitelist.

## Caveat

The next `System.map` symbol delta is not treated as function size on this
RKP/CFP/JOPP kernel. Several target functions have stack-reported sizes that are
larger than the next-symbol delta in the extracted kallsyms map. For the next
live sampler, use the per-boot codeword slide plus the whitelist identity and
stack-reported offsets; do not promote next-symbol deltas as function bounds and
do not reuse a numeric slide across boots.

## Safety

- Host-only parser.
- Private raw helper outputs stay under `workspace/private/**`.
- No device boot, flash, BPF attach, tracefs mutation, Wi-Fi scan/connect, or
  network change.
