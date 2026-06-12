# Native Init V2242 User ELF Offset Context Audit

Date: `2026-06-12`

## Identity

| Field | Value |
| --- | --- |
| Run ID | `V2242` |
| Track | `T1 kernel observation` |
| Device baseline | `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)` |
| Runner | `workspace/public/src/scripts/revalidation/a90_kernel_v2242_user_elf_offset_context.py` |
| Private evidence | `workspace/private/runs/kernel/v2242-user-elf-offset-context-20260612-112444/` |
| Device flash | no |
| Wi-Fi scan/connect/DHCP/ping | no |

## Track Selection

T1 remains the highest meaningful track. V2241 established the user-space
identity formula for helper-owned `a90*` probe records:

```text
runtime_probe_ip = per-run_load_bias + helper_static_uprobe_offset
```

The next bounded unit was to verify that those helper static offsets are real
executable user-ELF locations, not just stable numeric fingerprints.

No track transition occurred. T2 WLAN work was not selected because this unit is
host-only and directly strengthens the observer interpretation stack.

## Question

Do the static `a90*` helper uprobe offsets map to executable `LOAD` segments in
the stripped user ELFs available on the host, and can bounded instruction
context be banked privately without publishing raw proprietary disassembly?

## Method

The runner performed host-only postprocessing:

1. parsed static uprobe offset tables from
   `workspace/public/src/native-init/helpers/a90_android_execns_probe.c`;
2. reused V2229/V2231/V2233 parser summaries to mark which helper offsets were
   observed live;
3. parsed AArch64 ELF program headers with `readelf -lW`;
4. required each static offset to fall inside an executable `LOAD` segment of
   the matching stripped user ELF;
5. computed `file_offset = segment.p_offset + (offset - segment.p_vaddr)`;
6. wrote bounded byte/disassembly windows only under `workspace/private/`.

Important axis correction: V2241's `group` is the helper/log surface. ELF
verification needs the actual loaded object. The `cnss_peripheral_uprobe_events`
surface is reported as `a90cnss`, but its offsets target
`libperipheral_client.so`, so V2242 tracks it as object `a90periph`.

Inputs:

- `workspace/private/runs/kernel/v2229-live-20260612-080114/parser/summary.json`
- `workspace/private/runs/kernel/v2231-live-20260612-081302/parser/summary.json`
- `workspace/private/runs/kernel/v2233-live-20260612-083738/parser/summary.json`
- `workspace/private/runs/kernel/v2241-user-uprobe-offset-base-map-20260612-111447/summary.json`
- `workspace/public/src/native-init/helpers/a90_android_execns_probe.c`

Validation commands:

```text
python3 -m py_compile workspace/public/src/scripts/revalidation/a90_kernel_v2242_user_elf_offset_context.py
python3 workspace/public/src/scripts/revalidation/a90_kernel_v2242_user_elf_offset_context.py
```

## Result

Decision:

```text
v2242-user-elf-offset-context-pass
```

Coverage:

| Metric | Value |
| --- | ---: |
| static specs checked | `208` |
| observed specs checked | `107` |
| key events checked | `11` |
| static issue count | `0` |
| observed issue count | `0` |
| key issue count | `0` |

Object mapping:

| Object | ELF |
| --- | --- |
| `a90cnss` | `tmp/wifi/v226-vendor-root-live-export/vendor-source/bin/cnss-daemon` |
| `a90libqmi` | `tmp/wifi/v226-vendor-root-live-export/vendor-source/lib64/libqmi_cci.so` |
| `a90periph` | `tmp/wifi/v226-vendor-root-live-export/vendor-source/lib64/libperipheral_client.so` |
| `a90pmsrv` | `tmp/wifi/v1942-qcril-radio-vendor-artifact-export/vendor-source/bin/pm-service` |

All four stripped ELFs have executable `LOAD` segments and every checked helper
offset landed in the expected executable segment.

Key event executable checks:

| Group | Object | Event | Offset | File offset | Segment |
| --- | --- | --- | ---: | ---: | --- |
| `a90cnss` | `a90cnss` | `wlfw_service_request` | `0xd9fc` | `0xd9fc` | `RE` |
| `a90cnss` | `a90cnss` | `wlfw_worker_done_signal` | `0xdff8` | `0xdff8` | `RE` |
| `a90cnss` | `a90cnss` | `wlfw_worker_post_done_wait` | `0xe070` | `0xe070` | `RE` |
| `a90cnss` | `a90cnss` | `wlfw_start` | `0xec00` | `0xec00` | `RE` |
| `a90cnss` | `a90cnss` | `wlfw_cap_qmi` | `0xf460` | `0xf460` | `RE` |
| `a90cnss` | `a90cnss` | `wlfw_bdf_entry` | `0xf76c` | `0xf76c` | `RE` |
| `a90cnss` | `a90cnss` | `wlfw_bdf_send_ret` | `0xfc48` | `0xfc48` | `RE` |
| `a90cnss` | `a90cnss` | `wlfw_bdf_result_log` | `0xfd08` | `0xfd08` | `RE` |
| `a90libqmi` | `a90libqmi` | `libqmi_loop_client_init_ret` | `0x7944` | `0x7944` | `RE` |
| `a90pmsrv` | `a90pmsrv` | `pm_server_register_entry` | `0x6048` | `0x6048` | `RE` |
| `a90pmsrv` | `a90pmsrv` | `pm_service_main_supported_list_init` | `0x77bc` | `0x77bc` | `RE` |

Private instruction context:

| Field | Value |
| --- | --- |
| Path | `workspace/private/runs/kernel/v2242-user-elf-offset-context-20260612-112444/private_instruction_context.json` |
| Entries | `107` |
| Disassembler | `aarch64-linux-gnu-objdump` |

The private context contains bounded stripped-ELF bytes/disassembly. It is not
committed and must not be copied into public reports.

## Interpretation

V2242 closes the next post-V2241 identity layer:

- all observed `a90*` helper offsets are executable user-code locations;
- all static helper offsets covered by the available objects are executable
  user-code locations;
- `libperipheral_client.so` must be modeled as its own object even when its
  helper surface appears under the `a90cnss` log group;
- future instruction-level interpretation can use the private context JSON
  rather than re-deriving ELF mappings.

This does not change the kernel exact-slide contract. Kernel canonical PC/LR and
function-pointer anchors still use the kernel System.map path; helper-owned
`a90*` records use user-ELF load bias plus static offset.

## Decision

Use this contract for future `a90*` instruction-context work:

1. treat `group` as log surface and `object` as ELF identity;
2. map `periph_*` helper offsets to `libperipheral_client.so`;
3. require static offsets to land in executable `LOAD` segments;
4. keep raw byte/disassembly windows under `workspace/private/`;
5. publish only metadata/counts and named event decisions.

## Safety

- `host_only`: true.
- `device_io`: false.
- `bpf_attach`: false.
- `tracefs_control_write`: false.
- `probe_write_user_executed`: false.
- `wifi_scan_connect`: false.
- `network_route_change`: false.
- `flash_reboot`: false.
- `partition_write`: false.
- public output contains only metadata and summary values; private raw artifacts
  remain under `workspace/private/`.
