# Native Init V1136 Post-PM eSoC/MDM2AP Gate Plan

Date: `2026-05-27`

## Goal

Design the next gate after V1135:

```text
V1134 upper PM/CNSS success
  -> preserve post-policy provider/CNSS path
  -> add the smallest safe mdm_helper/eSoC/MDM2AP observer or state-machine gate
  -> look for service69/WLFW/BDF/wlan0 readiness
```

This is still not a Wi-Fi connect gate. It is the lower bring-up gate needed
before any scan/connect/DHCP/external ping can be meaningful.

## Current Facts

V1134 established:

- global firmware mounts are available;
- outer `/dev/subsys_modem` holder opens;
- `mss` reaches `ONLINE`;
- `cnss-daemon` reaches PeripheralManager;
- PM client/server register/connect return paths are hit;
- `per_mgr` and `pm_proxy_helper` hold `/dev/subsys_modem`;
- no helper-private modem pre-holder is used.

V1134 also established the remaining blocker:

- `mdm3` remains `OFFLINING`;
- QRTR services `69`, `74`, and `180` remain absent;
- no WLFW, BDF, MHI, QCA6390, or `wlan0` marker appears.

V1135 classified this as a lower eSoC/MDM2AP/WLFW publication gap, not a PM
provider or CNSS PM client gap.

## Relevant Prior Evidence

| Evidence | Finding | Impact |
| --- | --- | --- |
| V1024 | Android early window has `pm-service`/`pm_proxy_helper` on `/dev/subsys_modem` and `mdm_helper` on `/dev/esoc-0` | V1134 now reproduces the PM side; mdm_helper/eSoC side remains |
| V908 | repaired native runtime lets `mdm_helper` reach `/dev/esoc-0` | direct mdm_helper start is no longer totally blind |
| V911 | `mdm_helper` worker blocks in `ESOC_WAIT_FOR_REQ` | a powerup/request event is missing |
| V940 | SDX50M queue input contract is the likely lower input gap | property-only fixes are not enough |
| V960 | full provider/CNSS surface still lacks MHI/WLFW/wlan0 | upper userspace alone is insufficient |
| V1134 | PM register/connect succeeds but service69 remains absent | current retry target must be below PM |

## Candidate Gate

The next useful unit is a **post-PM mdm_helper/eSoC observer** that reuses the
V1134 prerequisite and then observes the lower path.

Preferred shape:

```text
1. Refresh current boot preconditions:
   - native health;
   - mountsystem ro;
   - V401 selinuxfs;
   - V490 policy-load;
   - helper v213+ readiness.

2. Run V1134 upper sequence:
   - global firmware mounts;
   - outer /dev/subsys_modem holder;
   - wait for mss ONLINE / QRTR RX;
   - service-manager + PM provider + CNSS PM register/connect.

3. Add only mdm_helper/eSoC observation:
   - start or observe mdm_helper through the repaired runtime-contract path;
   - confirm /dev/esoc-0 fd;
   - confirm ESOC_WAIT_FOR_REQ or queue transition;
   - sample GPIO142/MDM2AP IRQ count;
   - sample mdm3 state, QRTR services 69/74/180, WLFW/BDF/MHI/wlan0.

4. Cleanup:
   - terminate helper actors if safe;
   - otherwise bounded reboot cleanup;
   - verify v724/selftest fail=0.
```

## What Not To Do

Do not start with any of these:

- Wi-Fi HAL start;
- scan/connect/link-up;
- SSID/password use;
- DHCP/route changes;
- external ping;
- boot image write or flash;
- blind `/dev/subsys_esoc0` longer-hold retry;
- raw GPIO/sysfs/debugfs writes;
- property-context override as the first response.

## Success Criteria

V1136 itself is a plan/preflight unit. It passes if it identifies a single
bounded next live command with:

- explicit prerequisite evidence;
- exact helper mode and allow flags;
- timeout and cleanup boundary;
- postflight native health checks;
- expected positive markers;
- fail-closed interpretation for each likely outcome.

The eventual live gate succeeds if it captures at least one lower advancement:

- `mdm3` moves away from stable `OFFLINING`;
- GPIO142/MDM2AP IRQ count changes;
- QRTR service `69`, `74`, or `180` appears;
- WLFW/BDF/MHI marker appears;
- `wlan0` appears.

## Failure Classes

| Result | Meaning | Next |
| --- | --- | --- |
| PM path regresses | V1134 precondition not reproduced | repair precondition first |
| mdm_helper never reaches `/dev/esoc-0` | runtime-contract regression | return to V908/V911 surface |
| mdm_helper waits in `ESOC_WAIT_FOR_REQ` only | no lower powerup/request event | design a stricter eSoC trigger gate |
| request/IMG appears but GPIO142 stays zero | SDX50M/MDM2AP readiness blocker | classify power/reset/firmware response |
| service69 appears | WLFW publication achieved | plan Wi-Fi runtime/HAL readiness gate |
| wlan0 appears | lower bring-up achieved | only then plan controlled scan/connect |

## Validation

V1136 should begin as host-only/static work:

```bash
python3 -m py_compile <new v1136 script>
python3 <new v1136 script>
git diff --check
```

No live actor should run until the command line and cleanup plan are fixed in a
report.
