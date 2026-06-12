# Native Init V2248 Tail Capture Insertion Audit (2026-06-12)

## Scope

Host-only source/build audit for the next post-FWREADY tail capture. It does not
talk to the device, attach BPF, write tracefs, flash, reboot, scan/connect Wi-Fi,
or publish private raw logs.

Generated private summary:

- `workspace/private/runs/kernel/v2248-tail-capture-insertion-audit-20260612-120731/summary.json`

## Result

Decision: `v2248-tail-capture-insertion-audit-pass`.

| Check | Value |
| --- | --- |
| V2237 baseline | `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)` |
| fwclass bridge flag present | `true` |
| post-FWREADY tail order valid | `true` |
| host-side after-boot runner sufficient | `false` |
| embedded concurrent sampler required | `true` |
| next live cycle | `V2249` |

## Anchors

- V2237 keeps `A90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
  in `workspace/public/src/scripts/revalidation/build_native_init_boot_v2237_supplicant_terminate_poll.py`.
- The helper route calls `append_post_fw_ready_boot_wlan_trigger(stdout_buf)`,
  then sleeps 8 seconds, then runs the post-trigger samplers and
  `append_qcacld_firmware_class_fallback_feeder(stdout_buf, "after_boot_wlan_trigger", 30000)`
  in `workspace/public/src/native-init/helpers/a90_android_execns_probe.c`.
- The reusable V2216 sampler is `/cache/bin/a90_bpf_perf_regs_codeword_sample_ring`
  and requires `--allow-attach`.

## Interpretation

The qcacld/HDD tail begins inside the native-init helper immediately after the
post-FWREADY `boot_wlan` write. Running the existing V2216 host-side sampler
after the device has already reached normal control can miss the firmware_class
and HDD probe window. The next live unit must therefore start the sampler from
inside the native-init helper before the `boot_wlan` write and keep it alive
through the firmware_class feeder.

## V2249 Contract

- Start before: `append_post_fw_ready_boot_wlan_trigger(stdout_buf)`.
- Stay active through:
  `append_qcacld_firmware_class_fallback_feeder(stdout_buf, "after_boot_wlan_trigger", 30000)`.
- Run:
  `/cache/bin/a90_bpf_perf_regs_codeword_sample_ring --duration-ms 45000 --period-ns 1000000 --print-limit 512 --allow-attach`.
- Store helper output under:
  `/cache/native-init-v2249-tail-perf-regs-codeword.log`.
- Score the recovered summary with
  `workspace/public/src/scripts/revalidation/a90_kernel_v2247_tail_pc_lr_scorer.py`.

Preferred implementation: package/deploy the V2216 helper and launch it from a
compile-gated `a90_android_execns_probe` child before the `boot_wlan` write.
Embedding the sampler logic directly in the helper is acceptable but larger.
Running the host-side V2216 runner only after boot is explicitly insufficient.

## Safety

- Host-only parser and report.
- No boot image mutation, flash, BPF attach, tracefs write, Wi-Fi
  scan/connect, network route change, partition write, or private raw log
  publication.
