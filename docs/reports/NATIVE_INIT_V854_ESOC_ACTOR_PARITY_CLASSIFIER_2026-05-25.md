# Native Init V854 eSoC Actor Parity Classifier Report

## Result

- decision: `v854-esoc-actor-parity-selects-node-contract-preflight`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_esoc_actor_parity_classifier_v854.py`
- evidence: `tmp/wifi/v854-esoc-actor-parity-classifier/`
- next: V855 native Android eSoC/subsys node parity preflight; no actor
  open/ioctl yet

## Scope

V854 is host-only. It did not contact the bridge, ADB, QRTR, or the device. It
did not create/open/ioctl nodes, start services, write GPIO/sysfs/debugfs,
write subsystem state, load/unload modules, write boot/partition data, start
Wi-Fi HAL, scan/connect, use credentials, run DHCP/routes, or ping externally.

## Checks

| Check | Result | Meaning |
| --- | --- | --- |
| V853 input | pass | Android actor handoff result is present and passed |
| Android node contract | pass | `/dev/esoc-0`, `/dev/subsys_esoc0`, `/dev/subsys_modem`, `/dev/wlan` captured |
| Android holder contract | pass | `mdm_helper`/`ks` hold `/dev/esoc-0`; `pm-service` holds both subsystem nodes |
| Android policy contract | pass | ueventd mode/owner and SELinux contexts captured |
| Prior retry closures | pass | V849, V840, and V764 non-progress paths are accounted for |

## Candidate Matrix

| Candidate | Classification | Reason |
| --- | --- | --- |
| repeat manual `/dev/subsys_esoc0` open | reject | V849 already blocks in `mdm_subsys_powerup`; Android uses a broader actor contract |
| repeat `mdm_helper` alone | reject | V764/V746 already start it without mdm3/WLFW progress; V853 shows child `ks` and `/dev/esoc-0` contract |
| repeat provider-first PeripheralManager without node parity | reject | V840 still had WLAN-PD `UNINIT`; V853 proves exact node/FD contract is the missing discriminator |
| native Android node/ueventd parity preflight | select-next | Match Android node metadata first, without actor open/ioctl |
| `pm-service` start-only with Android node parity | prepare-after-next | Justified only after node parity passes without side effects |
| `mdm_helper` + `ks` eSoC contract replay | prepare-after-pm | Comes after subsystem/PeripheralManager parity |
| GPIO 135 / PMIC GPIO 9 direct manipulation | forbidden-now | Actor parity remains lower risk than GPIO/sysfs/debugfs writes |

## Selected V855 Gate

V855 should implement a bounded native preflight that:

1. reads the native `subsys` and `esoc` major/minor availability,
2. computes Android-equivalent node targets:
   - `/dev/esoc-0` char `484:0`, mode `0660`, owner `root:radio`,
   - `/dev/subsys_esoc0` char `236:9`, mode `0640`, owner `system:system`,
   - `/dev/subsys_modem` char `236:0`, mode `0640`, owner `system:system`,
3. verifies required vendor binaries and init-rule source paths are visible,
4. optionally materializes nodes in a bounded live proof,
5. does not open/ioctl those nodes and does not start actors yet,
6. cleans up any created nodes and verifies native health.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_esoc_actor_parity_classifier_v854.py
python3 scripts/revalidation/native_wifi_esoc_actor_parity_classifier_v854.py \
  --out-dir tmp/wifi/v854-esoc-actor-parity-plan plan
python3 scripts/revalidation/native_wifi_esoc_actor_parity_classifier_v854.py \
  --out-dir tmp/wifi/v854-esoc-actor-parity-classifier run
git diff --check
```

Result:

```text
decision: v854-esoc-actor-parity-selects-node-contract-preflight
pass: True
device_commands_executed: False
device_mutations: False
raw_esoc_open_executed: False
subsys_char_open_executed: False
wifi_bringup_executed: False
external_ping_executed: False
```

## Next Gate

V855 should be the first native live step after V853/V854, but it should remain
below actor replay. The goal is node/ueventd parity and cleanup proof only. Do
not start `pm-service`, `mdm_helper`, `ks`, Wi-Fi HAL, scan/connect,
DHCP/routes, external ping, raw eSoC ioctl, GPIO/sysfs/debugfs write,
subsystem state write, module load/unload, or boot-image changes in V855.
