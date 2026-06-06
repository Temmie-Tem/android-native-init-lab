# Wi-Fi V317 Approval and Sudo Matrix

## Current Gate

- latest host-only gate: `V357 Pre-Approval Audit`
- latest decision: `v317-preapproval-audit-awaiting-approval`
- remaining blocker: `exact-v317-approval-phrase`
- live proof status: not executed
- daemon start / scan / connect / link-up status: not executed

## Exact Approval Phrase

The V317 live proof must not run until the user provides this exact phrase:

```text
approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up
```

This phrase approves only the bounded V317 minimal private property namespace
proof. It does not approve Wi-Fi daemon start, scan, connect, DHCP, routing,
boot partition write, reboot, rollback, or broad device mutation.

## Command Classes

| Class | Examples | Needs sudo | Needs approval | Notes |
| --- | --- | --- | --- | --- |
| Host-only read/check | `py_compile`, `git diff --check`, V349/V350/V357 audits, manifest reads | no | no | Safe to run during planning/validation. |
| Host serial bridge | `sudo python3 scripts/revalidation/serial_tcp_bridge.py --port 54321 --device /dev/ttyACM0` | usually yes | no live approval | Opens host access to the existing ACM console; user may need to run it. |
| Host NCM setup | `sudo ip addr replace 192.168.7.1/24 dev <enx...>`, `sudo ip link set <enx...> up` | yes | no live approval if NCM already enabled | Changes host interface state only. |
| Device read-only via bridge | `a90ctl version`, `status`, `bootstatus`, `selftest`, V357 audit subchecks | no, if bridge is up | no | Must remain read-only. |
| V351 executor plan | `wifi_v317_live_executor.py plan` | no | no | Must not execute live proof or cleanup. |
| V351 executor run | `wifi_v317_live_executor.py ... run` | no host sudo by default | exact phrase + `--allow-device-mutation` + `--assume-yes` | Bounded V317 live proof only. |
| V351 executor cleanup | `wifi_v317_live_executor.py ... cleanup` | no host sudo by default | exact phrase + `--allow-device-mutation` + `--assume-yes` | Device mutation cleanup path; not a generic rollback approval. |
| Boot image write/reboot/rollback | fastboot/boot partition write, reboot to recovery/native, rollback flash | often yes | separate explicit approval | Not covered by V317 exact phrase. |
| Wi-Fi bring-up | daemon start, scan, connect, credential use, DHCP, routing, link-up | maybe | separate explicit approval | Not covered by V317 exact phrase. |
| Namespace/global property mutation | global `/dev/__properties__` bind, persistent property changes, Android runtime mutation | maybe | separate explicit approval | V317 only allows minimal private namespace proof. |

## Allowed Without Further Approval

These are allowed while waiting for the exact V317 phrase:

```bash
python3 scripts/revalidation/wifi_v317_preapproval_audit.py \
  --out-dir tmp/wifi/v357-v317-preapproval-audit \
  check

python3 scripts/revalidation/wifi_v317_live_executor.py \
  --out-dir tmp/wifi/v351-v317-live-executor \
  plan
```

The following host-side actions are allowed only if the user runs or confirms
the necessary `sudo` command on the host:

```bash
sudo python3 ./scripts/revalidation/serial_tcp_bridge.py \
  --port 54321 \
  --device /dev/ttyACM0

sudo ip addr replace 192.168.7.1/24 dev <current-ncm-enx>
sudo ip link set <current-ncm-enx> up
```

## Blocked Until Exact Phrase

Do not run this command class until the exact V317 phrase is present:

```bash
python3 scripts/revalidation/wifi_v317_live_executor.py \
  --out-dir tmp/wifi/v351-v317-live-executor \
  --approval-phrase "approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up" \
  --allow-device-mutation \
  --assume-yes \
  run
```

The executor guard must reject:

- missing phrase;
- shortened or wrong phrase;
- phrase without `--allow-device-mutation`;
- phrase without `--assume-yes`;
- flags without phrase.

## Still Separate After V317

Even after V317 live proof passes, these need separate planning and approval:

- starting Wi-Fi daemon for real operation;
- scan/connect/credential/DHCP/routing;
- persistent service enablement;
- boot image or boot partition writes;
- reboot/rollback;
- global property namespace changes;
- exposing network control outside the USB-local lab path.

## Operator Rule

If a command can change device state, assume it is blocked until the matching
approval text and matching plan are both present. Host `sudo` is an execution
permission; it is not device-mutation approval.
