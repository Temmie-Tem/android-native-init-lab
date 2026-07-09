# S22+ M34 S9 Devlink-Substrate Beacon Live Gate Result (2026-07-09)

## Verdict

S9 live gate was executed once under the bounded `AGENTS.md` boot-only
exception and is now consumed. The one-bit B1 predicate remained false even
after adding the Waipio devlink supplier substrate load-set.

Result:

```text
download-beacon-miss-parked-manual-download-required
```

Post-run analyzer decision:

```text
s22plus-m34-s9-b1-miss-stop-at-typec-or-i2c
```

Machine-readable evidence:

```text
workspace/private/runs/s22plus_m34_s9_devlink_substrate_beacon_live_gate_20260709T091154Z/result.json
workspace/private/runs/s22plus_m34_s9_devlink_substrate_beacon_live_gate_20260709T091154Z/timeline.json
workspace/private/runs/s22plus_m34_s9_devlink_substrate_beacon_live_gate_20260709T091154Z/s22plus_m34_s9_result_analysis.json
```

The selected device serial is intentionally not recorded in this report.

Codex added a dedicated fail-closed S9 helper, post-run analyzer, and tests:

```text
workspace/public/src/scripts/revalidation/s22plus_m34_s9_devlink_substrate_beacon_live_gate.py
workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s9_result.py
tests/test_s22plus_m34_s9_devlink_substrate_beacon_live_gate.py
tests/test_analyze_s22plus_m34_s9_result.py
```

## Candidate

The helper pins the S9 artifact from the v0.10 M34 runtime-gadget split build:

```text
AP.tar.md5 SHA256: 41a76ac1404c99273e9ec3aeae591dbfc94e1aa83daf97de9a7068e3c155022f
Padded boot.img SHA256: 509a05e4ff97dad39ca52eae6c57169e20d3ddbf1524d292e8c91b9286a80414
/init SHA256: 9f231faff6154dc08b6b4d1b6cd169e82c81bfdc1e8d02cc92d1ea5a02dbd390
Module-list SHA256: c07425f4c738b53822e9f6783a142a2b5eafd72a15bd34c06fb3b49357c8fe26
Template source SHA256: 8364aca94582fc325f89855b5cfd4e47ff8e41d2f18c341c99bd750ea3ebe3ae
Known booting Magisk base boot SHA256: 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

The helper validates the v0.10 manifest contract before any live path:

- stage is `S9`, stage number is `11`;
- module closure count is `89`;
- devlink supplier load-set is pinned;
- dep-complete new module delta is `qcom-pdc.ko`, `pinctrl-msm.ko`,
  `pinctrl-waipio.ko`;
- runtime strings include `devlink_supplier_closure=1`,
  `substrate_load_set=waipio_devlink`, `driver_load_only=1`, and
  `manual_power_write=0`;
- downstream configfs, UDC bind, TypeC role write, ssusb role write,
  FunctionFS, stock composite, persistent mounts, and block writes remain
  forbidden.

## Prelive Packet

Read-only prelive packet generation passed against the current rooted Android
baseline. The selected device serial is intentionally not recorded in this
report.

```text
workspace/private/runs/s22plus_m34_s9_devlink_substrate_beacon_live_gate_20260709T090409Z/s22plus_m34_s9_prelive_packet.json
```

Packet material hashes:

```text
active_exception_template: d63e6d5acbb8f708b812dfec555d0d6420323f2320d504184d6ac74cc91e5e95
android_reset_context_baseline_json: f415555d6263daa4ed11f033840f0131b3a4c9c47a66924285a40f661dc49289
android_s9_predicate_baseline_json: 1b2205a2a6da03315aa7c94e96b7aeb25403233757bd50de436559afa4a95054
runbook: 750db172df8ae4d77967862bef595acab0f1742ce2122c6b6de43308ebf8008b
```

Verifier passed:

```text
workspace/private/runs/s22plus_m34_s9_devlink_substrate_beacon_live_gate_20260709T090614Z_01/s22plus_m34_s9_devlink_substrate_beacon_live_gate.txt
```

## Analyzer

`analyze_s22plus_m34_s9_result.py` accepts only S9 result payloads with the
pinned artifact hashes and single `timeline.json` `events:[{name,timestamp_utc}]`
schema. A complete S9 `download-beacon-hit` advances the B-ladder to `S8B2`
(`port0_partner_exists`). A complete S9 MISS stops before B2 and keeps the next
unit focused on GENI I2C/max77705/TypeC reachability.

## Live Result

The live helper passed default dry-run first, then flashed only the pinned S9
boot AP. The original Odin endpoint disconnected after candidate transfer, but
no new Odin Download endpoint appeared during the 90 second beacon observation
window. The operator reported no bootloop during the window.

The candidate therefore parked on the false branch. The operator manually
entered Download mode through RDX, the helper detected the manual rollback
endpoint, flashed the pinned Magisk boot-only rollback AP, and Android returned
to the Magisk baseline. Post-rollback boot hash verification passed.

Analyzer summary:

```text
b1_observed: true
b1_state: false
ok_to_advance: false
ok_to_live_next_stage: false
magisk_baseline_restored: true
timeline: ordered, monotonic, required events present
```

Retained marker evidence was not found in pstore or `/proc/last_kmsg`; this is
not the deciding signal for S9 because the deciding signal was the absence of a
new Download endpoint during the bounded observation window.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m34_s9_devlink_substrate_beacon_live_gate.py \
  workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s9_result.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_s22plus_m34_s9_devlink_substrate_beacon_live_gate.py \
  tests/test_analyze_s22plus_m34_s9_result.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_s22plus_m34_runtime_gadget_split_build.py \
  tests/test_s22plus_m34_s8b1a_wide_i2c_beacon_live_gate.py \
  tests/test_analyze_s22plus_m34_s8b1a_result.py \
  tests/test_s22plus_m34_s8b1_beacon_probe_live_gate.py \
  tests/test_analyze_s22plus_m34_s8b1_result.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m34_s9_devlink_substrate_beacon_live_gate.py \
  --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m34_s9_devlink_substrate_beacon_live_gate.py \
  --prelive-packet

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m34_s9_devlink_substrate_beacon_live_gate.py \
  --verify-prelive-packet \
  workspace/private/runs/s22plus_m34_s9_devlink_substrate_beacon_live_gate_20260709T090409Z/s22plus_m34_s9_prelive_packet.json

git diff --check
```

Result:

```text
py_compile: OK
S9 helper/analyzer tests: Ran 63, OK
M34 S8/S8B1A/S9 regression tests: Ran 129, OK
S9 --offline-check: OK
S9 --prelive-packet: OK
S9 --verify-prelive-packet: OK
S9 default dry-run: OK
S9 live gate: rc=0, MISS, Magisk rollback clean
git diff --check: OK
```

## Next Step

Do not proceed to B2/B3/B4 on the current evidence. S9 closed the most likely
devlink supplier substrate gap and B1 still missed, so the next unit should be
host-only investigation of why native-init still does not expose either
`/sys/class/typec/port0` or any `/sys/bus/i2c/devices/*-0066` path before the
downstream USB descriptor/composition work resumes.
