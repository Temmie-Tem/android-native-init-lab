# Native Init V2276 Codeword Mismatch Postprocess

## Summary

- Cycle: `V2276`
- Type: host-only postprocess of existing V2275 private codeword/workqueue logs.
- Decision: `v2276-codeword-uao-patch-aware-accepted-workqueue-no-target-hit`
- Result: `PASS` for the codeword acceptance-policy discriminator; `NEGATIVE` for the V2275 `work->func` target hit discriminator.
- Evidence input: `workspace/private/runs/kernel/v2275-workqueue-codeword-live-20260612-172723`
- New script: `workspace/public/src/scripts/revalidation/native_kernel_v2276_codeword_mismatch_postprocess.py`
- Device action: none.

## Codeword Result

V2275's same-boot codeword sampler had a strong best slide but failed the existing V2216 policy:

- Best slide: `0xccef4`
- Existing V2216 acceptance: `false`, reason `not_accepted`
- PC codeword match: `712/715`
- LR-4 codeword match: `709/709`
- LR codeword match: `709/709`
- PC mismatch count: `3`

V2276 explains all three PC mismatches as ARM64 UAO runtime alternatives. The source contract is in `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/arch/arm64/include/asm/alternative.h`: UAO alternatives replace post-index privileged load/store forms with unprivileged `ldtr` / `sttr` plus explicit address update because unprivileged instructions have no post-increment or pair forms.

| sample | comm | static PC | stock | live | class | LR/LR-4 |
| --- | --- | --- | --- | --- | --- | --- |
| `167` | `init` | `0xffffff80099a3244` | `0xf80084c3` | `0xf80008c3` | `uao_user_alternative_str_to_sttr` | exact |
| `196` | `a90_bpf_perf_re` | `0xffffff80099a2bac` | `0xa8c12027` | `0xf8400827` | `uao_ldp_first_lane_to_ldtr` | exact |
| `627` | `init` | `0xffffff80099a332c` | `0xa88128c9` | `0xf80008c9` | `uao_stp_first_lane_to_sttr` | exact |

Decoded instruction pairs:

- `0xf80084c3` = `str x3, [x6], #8`; `0xf80008c3` = `sttr x3, [x6]`.
- `0xa8c12027` = `ldp x7, x8, [x1], #16`; `0xf8400827` = `ldtr x7, [x1]`.
- `0xa88128c9` = `stp x9, x10, [x6], #16`; `0xf80008c9` = `sttr x9, [x6]`.

Conclusion: accept the V2275 slide only under a narrow `UAO-runtime-alternative PC mismatch + exact LR/LR-4` policy. This is not a general relaxation of codeword matching.

## Workqueue Reclassification

With the V2275 slide accepted under the bounded UAO-aware rule, V2276 reclassifies the already collected workqueue function-pointer samples:

- Classification: `workqueue-no-target-hit`
- Workqueue stats: `total=12511`, `stored=2048`, `queue_work=6254`, `execute_start=6257`, `overflow=10463`
- Stored sample count: `2048`
- Kind counts: `queue_work=1018`, `execute_start=1024`, `unknown=6`
- Target hit count: `0`
- Target list: `request_firmware_work_func`, `_request_firmware`, `request_firmware`, `qdf_file_read`, `qdf_ini_parse`, `cfg_parse`, `hdd_context_create`, `wlan_hdd_pld_probe`

Interpretation: the V2274/V2275 workqueue `work->func` oracle is now classifiable, and it is negative for the firmware_class/qcacld-HDD target list. Do not rerun the same combined workqueue/codeword capture for this question.

## Next T1 Implication

The next meaningful T1 unit should not be another generic CPU-clock or identical `work->func` capture. If kernel observation remains the selected tier, build a narrower oracle around workqueue `execute_start` call-stack or callsite context so the worker can be tied to the V2253 firmware_class/qcacld-HDD stack rather than only the `work->func` pointer.

## Safety Scope

- Host-only analysis; no device flash, reboot, tracefs control write, or live attach.
- No Wi-Fi scan/connect/DHCP/ping, credentials, routes, or external network test.
- No `probe_write_user`, kernel writes, eSoC/PCIe/GDSC/PMIC/GPIO paths, platform bind/unbind, or partition writes.
- Raw private logs remain under `workspace/private/**`; this report includes only metadata and instruction words required for the discriminator.

## Validation

Commands run:

```bash
python3 -m py_compile workspace/public/src/scripts/revalidation/native_kernel_v2276_codeword_mismatch_postprocess.py
PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_kernel_v2276_codeword_mismatch_postprocess.py \
  --json-out workspace/private/runs/kernel/v2275-workqueue-codeword-live-20260612-172723/v2276_postprocess_summary.json
```
