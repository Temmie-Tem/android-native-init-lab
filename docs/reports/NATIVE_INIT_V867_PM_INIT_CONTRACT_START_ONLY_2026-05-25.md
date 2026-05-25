# Native Init V867 PeripheralManager Init Contract Start-Only Report

## Result

V867 produced a bounded live blocker, not a clean pass.

| Unit | Evidence | Decision |
|---|---|---|
| plan | `tmp/wifi/v867-pm-init-contract-plan/manifest.json` | `v867-pm-init-contract-plan-ready` |
| live r2 | `tmp/wifi/v867-pm-init-contract-live-r2/manifest.json` | superseded by r3 post-actor parsing |
| live r3 | `tmp/wifi/v867-pm-init-contract-live-r3/manifest.json` | `v867-residual-actor-cleanup-required` |
| reboot cleanup | `tmp/wifi/v867-reboot-cleanup/` | v724/selftest/actor-clean restored |

## Findings

The helper mode executed and reached the intended PM init-contract surface:

| Field | Value |
|---|---|
| mode | `wifi-companion-peripheral-manager-init-contract-start-only` |
| child_started | `6` |
| init_contract | `1` |
| `per_proxy_helper` oneshot marker | `1` |
| `per_mgr` ioprio marker | `1` |
| `per_mgr` ioprio result | `ok=1 errno=0` |
| `per_proxy` lifecycle gate | `init.svc.vendor.per_mgr=running`, open `1` |
| shutdown-stop model marker | `1` |

Runtime classification from r3:

| Child | Target context | Runtime attr/current | Exit | FD result |
|---|---|---|---|---|
| `per_proxy_helper` | `u:r:per_proxy_helper:s0` | `kernel` | still running, `Ds` | no subsystem fd; cleanup unsafe |
| `per_mgr` | `u:r:vendor_per_mgr:s0` | `kernel` | exit `0` | no fd retained |
| `per_proxy` | `u:r:vendor_per_mgr:s0` | `kernel` | exit `1` | vndbinder/socket only |

The important blocker is cleanup/lifetime, not the basic mode construction:

- helper markers, ioprio, lifecycle gate, and private node parity all executed;
- `per_mgr` still ran with runtime `attr/current=kernel` despite accepted target
  context;
- `per_mgr` still did not hold `/dev/subsys_esoc0` or `/dev/subsys_modem`;
- `pm_proxy_helper` remained in D-state (`Ds`) after the helper cleanup window;
- bounded `kill -9` cleanup did not clear the D-state during r3;
- native reboot was required to restore a clean actor surface.

## Cleanup

Manual recovery after r3:

```bash
python3 scripts/revalidation/a90ctl.py --timeout 5 --allow-error reboot
```

Post-reboot verification:

- version: `A90 Linux init 0.9.68 (v724)`
- selftest: `pass=11 warn=1 fail=0`
- gated actor process count: `0`

## Guardrails Held

- No `mdm_helper` or `ks` start.
- No CNSS, Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect/link-up,
  credentials, DHCP/routes, or external ping.
- No raw eSoC ioctl, GPIO/sysfs/debugfs/subsystem state write, module
  load/unload, boot image write, or partition write.
- The only recovery action beyond the PM start-only proof was native reboot to
  clear the unkillable `pm_proxy_helper` D-state.

## Next

Do not proceed to `mdm_helper`, `ks`, HAL, or Wi-Fi bring-up from this state.
The next cycle should be V868 host-only/read-only classification of
`pm_proxy_helper` behavior and SELinux transition semantics:

1. classify why `setexeccon` target is accepted but runtime `attr/current`
   remains `kernel`;
2. inspect `pm_proxy_helper` expected inputs and why it blocks in native;
3. decide whether to suppress `pm_proxy_helper`, shorten its window, or model it
   differently before another live PM proof.
