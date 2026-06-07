# Native Init Transport Contract Plan

## Summary

This plan defines the host-device transport contract for native-init validation.
The goal is to stop every runner from re-discovering bridge, NCM, tcpctl, and
artifact-upload behavior independently.

The standing boot-image plus communication contract is maintained in
`docs/operations/NATIVE_INIT_BOOT_TRANSPORT_CONTRACT.md`. This plan records the
implementation phases for that contract.

Design rule: serial remains the recovery-safe control channel; NCM/tcpctl becomes
the fast data channel once readiness is proven by a stable, machine-readable
contract.

## Current Baseline

- Host serial bridge script: `workspace/public/src/scripts/revalidation/serial_tcp_bridge.py`.
- Host command wrapper: `workspace/public/src/scripts/revalidation/a90ctl.py`.
- Fasttransport boot baseline: `v725-fasttransport` and later Wi-Fi baselines.
- Current device baseline: `v2169-transport-contract`.
- Serial command protocol: `cmdv1` / `cmdv1x` with `A90P1 BEGIN` and `A90P1 END` framing.
- NCM/tcpctl exists, but scripts still make ad-hoc readiness and fallback decisions.

## Problem

The project now has three overlapping transport surfaces:

1. USB CDC ACM serial bridge for initial control and recovery.
2. `cmdv1` / `cmdv1x` for framed native-init commands over the bridge.
3. USB NCM + `tcpctl` / netcat for fast commands, helper staging, and artifact upload.

The surfaces are useful, but their contract is not centralized. That causes:

- broken operator commands when source paths move;
- duplicate readiness checks across runners;
- stale bridge processes and ambiguous USB ACM re-enumeration;
- inconsistent serial fallback behavior;
- slow or oversized serial artifact pulls where NCM upload should be used;
- uncertainty about which state belongs to host, bridge, device, or NCM.

## Non-goals

- Do not replace the existing `cmdv1` wire protocol.
- Do not expose bridge, tcpctl, NCM, or rshell outside the trusted USB-local boundary.
- Do not make Wi-Fi scan/connect/DHCP/ping part of transport validation.
- Do not require boot partition changes for the host wrapper phase.
- Do not make `netservice` globally auto-start without an explicit baseline decision.

## Transport Roles

| Layer | Owner | Role | Required property |
| --- | --- | --- | --- |
| USB ACM serial | device kernel + native init | bootstrap and recovery control | available first, safe fallback |
| `serial_tcp_bridge.py` | host | localhost TCP to serial forwarding | stable path, pinned identity, capture |
| `cmdv1` / `cmdv1x` | device + host | framed command execution | parseable rc/status/duration |
| NCM | device + host OS | high-speed link-local data path | readiness based on link-local reachability |
| `tcpctl` | device helper + host | fast command/control path | token-gated, USB-local only |
| FastUploadSession | host + device tools | artifact/log upload | archive manifest, secret scan, serial fallback |

## Contract v1

### Host Bridge Contract

A new host wrapper should provide one stable entrypoint around the existing
bridge script:

```text
python3 workspace/public/src/scripts/revalidation/a90_bridge.py ensure
python3 workspace/public/src/scripts/revalidation/a90_bridge.py status --json
python3 workspace/public/src/scripts/revalidation/a90_bridge.py doctor --json
python3 workspace/public/src/scripts/revalidation/a90_bridge.py repair-dirs
python3 workspace/public/src/scripts/revalidation/a90_bridge.py stop
python3 workspace/public/src/scripts/revalidation/a90_bridge.py restart
python3 workspace/public/src/scripts/revalidation/a90_bridge.py preflight --json
```

Required behavior:

- Resolve the bridge script from the repository root, not from the caller's cwd.
- Report `wrapper_contract=1` in text and JSON status output.
- Default listener stays `127.0.0.1:54321`.
- Default capture path is private: `workspace/private/logs/bridge/bridge-<timestamp>.log`.
- Print Samsung ACM candidates, selected path, selected realpath, and ambiguity state.
- Refuse ambiguous auto matches unless explicitly overridden.
- Detect whether port `54321` is already owned by a bridge process.
- Never silently kill an unrelated process.
- Prefer explicit `--device /dev/ttyACM0` when requested by the operator.
- Support opt-in `--pin-selected-realpath` when the operator wants the selected
  serial node passed through as `--expect-realpath`.
- Keep managed metadata and capture files under `workspace/private/`.
- Diagnose root-owned private bridge dirs and provide a bounded `repair-dirs`
  command for `workspace/private/logs/bridge/` and `workspace/private/run/`.

`status --json` should report at least:

```json
{
  "wrapper_contract": 1,
  "wrapper_name": "a90_bridge",
  "bridge_process": "running|stopped|unknown",
  "listen_host": "127.0.0.1",
  "listen_port": 54321,
  "port_listening": true,
  "port_pids": [12345],
  "port_pid_source": "fd|cmdline-fallback|unresolved",
  "port_pid_inaccessible_fd_dirs": 0,
  "serial_candidates": ["/dev/serial/by-id/..."],
  "selected_device": "/dev/ttyACM0",
  "selected_realpath": "/dev/ttyACM0",
  "ambiguous": false,
  "capture_path": "workspace/private/logs/bridge/...log"
}
```

### Device Serial Command Contract

The device must continue to support the existing minimal serial control commands:

- `version`
- `status`
- `selftest`
- `hide`
- `recovery`

`cmdv1` remains the authoritative serial command envelope. Host code should not
parse ad-hoc raw shell text when `A90P1` framing is available.

`cmdv1` success criteria:

- `A90P1 END` is present.
- `rc=0`.
- `status=ok`.
- For selftest, text contains `fail=0`.

### Device Transport Readiness Contract

Add or standardize transport fields in `status` without changing legacy lines.
New fields should be simple `key=value` lines so existing parsers can keep using
line-oriented parsing.

Required fields:

```text
transport.contract=1
transport.serial=ready
transport.bridge_endpoint=127.0.0.1:54321
transport.ncm=absent|present|starting|ready|degraded|stopped
transport.ncm.ifname=<device-ifname-or->
transport.ncm.ipv4=<addr-or->
transport.ncm.ipv6_ll=<addr-or->
transport.tcpctl=stopped|starting|ready|degraded
transport.tcpctl.port=<port-or->
transport.upload=serial-only|ncm-ready|tcpctl-ready
transport.preferred=serial|ncm|tcpctl
transport.reason=<short-label>
```

Host readiness should be based on both sides:

- device says NCM/tcpctl is ready;
- host sees the matching Samsung NCM interface;
- host has IPv6 link-local on that interface;
- host can reach the device over the selected fast path.

### Host Transport Selection Contract

Every revalidation runner should use one shared selector:

1. Ensure bridge is running or report a clear bridge preflight failure.
2. Run `cmdv1 version` and `cmdv1 status` over serial.
3. Parse `transport.contract` and transport fields.
4. If device and host NCM readiness pass, use NCM/tcpctl/FastUpload.
5. If fast path fails, downgrade once to serial fallback with a recorded reason.
6. Never retry unsafe commands automatically unless the caller explicitly opts in.

Selection output should be saved in the run manifest:

```json
{
  "selector_contract": 1,
  "transport_contract": 1,
  "bridge_wrapper_contract": 1,
  "bridge_device": "/dev/ttyACM0",
  "serial_bridge": "ready",
  "device_status": "ready",
  "ncm_host": "ready|not-ready|not-tested",
  "tcpctl": "ready|not-ready|not-tested",
  "selected": "serial|ncm|tcpctl",
  "fallback_reason": null
}
```

### Artifact Upload Contract

Fast artifact collection should use `FastUploadSession` semantics:

- collect only whitelisted logs/artifacts into a temp directory;
- exclude connection configs, secret files, raw `wpa_supplicant.conf`, and credential env files;
- create tar via BusyBox `tar -cf -`, then pipe to BusyBox `gzip -c`;
- upload over NCM TCP when ready;
- host verifies tar listing and SHA256;
- host scans archive bytes for configured secret values when provided;
- if NCM upload fails, fallback to serial only for small bounded summaries.

## Implementation Phases

### Phase 1: Host Wrapper Only

No boot image change.

Deliverables:

- Add `a90_bridge.py` wrapper.
- Add `ensure`, `start`, `stop`, `restart`, `status`, `doctor`, `repair-dirs`, and `preflight` subcommands.
- Default capture path under `workspace/private/logs/bridge/`.
- Update live operations docs to use the wrapper command.
- Add py_compile validation.

Acceptance:

- Wrapper starts the existing bridge from any cwd.
- `status --json` distinguishes stopped, listening, serial missing, and serial connected.
- Existing `a90ctl.py version` works after wrapper `start`.
- No boot image or device command behavior changes.

### Phase 2: Shared Host Transport Selector

No boot image change unless required by missing status lines.

Deliverables:

- Add a shared Python helper for bridge + serial + NCM readiness selection.
- Migrate one low-risk smoke script to use it.
- Persist selector result into the run output directory.
- First target: `a90_ncm_transport_smoke.py` imports `a90_transport.py`
  for bridge ensure, `cmdv1` version/status, host NCM snapshot, and manifest
  selection fields. The first selector schema is `selector_contract=1`.

Acceptance:

- Same runner can operate with NCM ready and with NCM absent.
- Serial fallback is explicit and recorded.
- Unsafe command replay remains blocked by default.

### Phase 3: Device Status Contract

Requires a test boot image.

Deliverables:

- Add `transport.contract=1` and related fields to native-init `status`.
- Keep existing `netservice` and `exposure` lines intact.
- Build a rollbackable test image above the current baseline.
- Flash, verify `version/status/selftest`, then roll back.

Acceptance:

- `status` includes all required `transport.*` fields.
- Old parsers still pass.
- Selftest remains `fail=0` before and after rollback.

### Phase 4: Fast Upload Default for Heavy Artifacts

Requires host runner changes only if boot already provides required tools.

Deliverables:

- Centralize FastUploadSession.
- Migrate Wi-Fi/revalidation scripts that currently pull large logs via serial.
- Add manifest fields for upload method, tar SHA256, byte count, and secret scan.

Acceptance:

- Heavy log upload uses NCM when ready.
- Serial upload remains bounded fallback.
- Secret-value scan reports `secret_values_logged=0` or fails closed.

### Phase 5: Baseline Promotion Decision

Requires one integrated test boot.

Deliverables:

- Build a candidate boot image with device status contract.
- Run bridge wrapper + selector + upload smoke.
- Run rollback selftest.
- Decide whether to promote as the next boot/init baseline.

Acceptance:

- Bridge start/status/restart works.
- Serial command path works.
- NCM readiness is detected deterministically.
- Fast upload succeeds or cleanly falls back.
- Rollback to current baseline succeeds with `selftest fail=0`.

## Safety Scope

Allowed:

- Host bridge process management.
- Host NCM readiness inspection.
- USB-local serial/NCM traffic.
- Rollbackable test boot images during Phase 3+.
- Private log/capture files under `workspace/private/`.

Blocked unless separately approved:

- External network exposure.
- Wi-Fi scan/connect/credentials/DHCP/routes/ping as part of transport tests.
- PMIC/GPIO/GDSC/regulator writes.
- eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind.
- Unbounded raw serial capture upload to public paths.
- Persisting real credentials or raw supplicant configs in git-tracked files.

## Versioning

Use separate axes:

- Host wrapper version: script feature version, not a boot baseline.
- Transport contract version: `transport.contract=1`.
- Boot/init baseline tag: e.g. `v2169-transport-contract`, future `v2170-<purpose>` if promoted.
- Validation run IDs: evidence/run numbers, not baseline names.

Do not use helper version, run ID, and boot baseline interchangeably.

## First Unit

Implement Phase 1 only:

1. Add `workspace/public/src/scripts/revalidation/a90_bridge.py`.
2. Make it repo-root aware.
3. Implement `preflight`, `status`, `start`, `stop`, `restart`, `doctor`, and `repair-dirs`.
4. Default capture to `workspace/private/logs/bridge/`.
5. Update only live operations docs, not historical reports.
6. Run py_compile and one host-only preflight/status.

No device flash is required for the first unit.
