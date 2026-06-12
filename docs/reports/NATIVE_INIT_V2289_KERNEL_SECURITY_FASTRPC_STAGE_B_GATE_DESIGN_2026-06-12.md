# V2289 Kernel Security Recon: FastRPC Stage-B gate design

Date: 2026-06-12
Scope: host/web/source reasoning only. No device write, no flash, no reboot, no devnode creation, no ioctl, no `mmap(2)`, no DSP invoke, no payload, no exploit trigger.
Baseline: resident rollback checkpoint remains `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`.

## Executive decision

Stage B is the next technical boundary, but it is **not** an autonomous next action.

V2284-V2288 established:

- the public CVE-2024-43047 fix-side invariant is absent in the local 4.14 FastRPC tree;
- `adsprpc-smd` is registered and openable once a temporary devnode is materialized;
- the ioctl surface and avoid-list are known;
- the UAF-adjacent path is the invoke/map lifecycle, not a benign query path.

Public references raise the risk level rather than lowering it:

- Qualcomm's bulletin says CVE-2024-43047 affects the FastRPC driver and patches were provided to OEMs, with indications of limited targeted exploitation.
- NVD records the issue as memory corruption while maintaining HLOS memory maps, CWE-416, CVSS 7.8 with local low-privilege attack vector and high CIA impact, and CISA KEV status.
- Project Zero's public analysis is based on in-the-wild crash artifacts and repeatedly points to `fastrpc_mmap` lifecycle corruption around adsprpc ioctls.
- Qualcomm's own FastRPC architecture description confirms the kernel driver queues CPU-side remote invocations to the DSP and waits for responses; therefore invoke-path testing is not a local-only syscall check.

Therefore the correct next unit is a gate, not a trigger:

> `V2289 = B0 gate design`. `Stage B` execution requires a later, explicit human go/no-go with the exact approved scope.

## External references used

- Project Zero, "The Qualcomm DSP Driver - Unexpectedly Excavating an Exploit": `https://projectzero.google/2024/12/qualcomm-dsp-driver-unexpectedly-excavating-exploit.html`
- Qualcomm October 2024 Security Bulletin: `https://docs.qualcomm.com/product/publicresources/securitybulletin/october-2024-bulletin.html`
- NVD CVE-2024-43047 entry: `https://nvd.nist.gov/vuln/detail/cve-2024-43047`
- CVE record: `https://www.cve.org/CVERecord?id=CVE-2024-43047`
- Qualcomm FastRPC public architecture README: `https://github.com/qualcomm/fastrpc`

## Stage taxonomy

| Stage | Name | Device effect | Status after V2289 |
| --- | --- | --- | --- |
| B0 | Design gate | none | this report |
| B1 | Dispatch-only liveness | one temporary devnode, one invalid unknown ioctl only | allowed only if explicitly selected; not a UAF trigger |
| B2 | Crash-only trigger attempt | one bounded FastRPC vulnerable-path call sequence | requires exact human go; not autonomous |
| B3 | Exploit development | heap shaping, reclaim, arbitrary read/write, privilege escalation, persistence | out of scope for this project unless separately re-chartered |

The important split is B1 vs B2. B1 proves driver dispatch wiring. B2 enters the vulnerable command family. B1 does not justify B2 automatically.

## B1 dispatch-only liveness design

Purpose: prove `fastrpc_device_ioctl` default dispatch is reachable without invoking any real FastRPC command.

Allowed:

- preflight only: `a90ctl version`, `status`, `selftest verbose`;
- create temporary `/dev/adsprpc-smd` char node using major `480`, minor `0`;
- open `O_RDWR`;
- issue exactly one unknown invalid ioctl value that is not in the `FASTRPC_IOCTL_*` set;
- expect `-ENOTTY` or equivalent unknown-command failure;
- close fd;
- remove temp devnode;
- final `status` and `selftest verbose`.

Forbidden:

- any `FASTRPC_IOCTL_*` command;
- any `mmap(2)`;
- any DSP payload, fd-backed DMA-buf, invoke buffer, map, unmap, init, getinfo, or control subrequest;
- loops, retries, fuzzing, randomized ioctl numbers, or error spraying.

Implementation requirement if B1 is selected:

- If no existing on-device `ioctl` applet is present, use a tiny purpose-built helper stored under `workspace/private/` and transferred to `/cache/bin/` or `/cache/` for the run only.
- The helper must hardcode a single invalid-ioctl operation and then exit.
- The helper source and binary must not be committed if it contains any trigger-capable scaffolding. A metadata-only report is acceptable.

## B2 trigger gate

B2 is the first step that enters the UAF-adjacent command families from V2288.

Diagnosability correction:

- The stock config has `CONFIG_SLUB_DEBUG=y`, but `CONFIG_SLUB_DEBUG_ON` is not set.
- `CONFIG_KASAN` and `CONFIG_PAGE_POISONING` are not set.
- Therefore a naive crash-only B2 negative is low-information: `b2-returned-no-crash` means "not detected in this runtime configuration", not "not vulnerable".
- A positive B2 result still matters (`kernel-warning`, `panic`, or reboot), but a negative result is inconclusive unless a later diagnostic boot enables relevant allocator poisoning/debugging.

Allowed objective:

- **Crash-only / no-escalation classification**: return value, hang, kernel warning, panic, or no visible effect from one approved attempt.

Not allowed:

- arbitrary read/write;
- privilege escalation;
- heap spray or reclaim strategy;
- pipe/inotify/object spraying;
- repeated attempts for reliability;
- payload execution;
- RKP bypass;
- persistence;
- post-trigger exploitation.

Required explicit approval phrase:

> `Stage B go: FastRPC one-shot crash-only trigger on v2237, no heap spray, no privilege escalation, no retry`

Any weaker approval is insufficient. "Proceed", "continue", or "do next" must be treated as insufficient for B2.

## Mandatory B2 preconditions

All must be true immediately before B2:

1. Human is present and explicitly watching the run.
2. Serial bridge is up at `127.0.0.1:54321`.
3. Resident image reports `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`.
4. `status` and `selftest verbose` report `fail=0`.
5. Battery/thermal state is normal enough to tolerate a crash/reboot.
6. Known-good boot images are present:
   - `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`
   - `workspace/private/inputs/boot_images/boot_linux_v48.img`
7. TWRP/recovery access remains available.
8. Pre-run pstore/kmsg state is snapshotted, or explicitly noted empty/unmounted.
9. Output directory under `workspace/private/runs/security/` exists.
10. The exact helper SHA256 is recorded before transfer.
11. The temporary devnode cleanup command is prepared.
12. The rollback command path is prepared, but not run unless needed.

Failure of any precondition is a hard stop.

## B2 helper design constraints

The helper may only exist in private workspace/run artifacts. It must not be committed.

Required properties:

- one process, one target device, one open fd;
- no threads;
- no loops;
- no retry;
- no heap spray;
- no object reclaim;
- no privilege check beyond recording current uid/gid;
- no network;
- no filesystem writes except its own redacted result file under `/cache/` or stdout over serial;
- cleanup path closes fd before exit when possible;
- bounded wall time enforced by the host runner;
- input is fixed at build time or provided via a small explicit config file kept under `workspace/private/`, never interactive fuzzing.

Reportable metadata:

- helper SHA256;
- target node major/minor;
- command-family classification, not runnable argument details;
- return code/errno;
- elapsed time;
- kernel log markers;
- pstore presence;
- final `version/status/selftest`.

Do not report:

- raw exploit payloads;
- fd values chosen for vulnerable matching;
- heap layout attempts;
- reclaim object recipes;
- kernel addresses unless already part of the existing symbolization reports and redacted as metadata.

## Observability plan

Before B2:

- capture `version`, `status`, `selftest verbose`;
- snapshot `/proc/devices`, `/sys/class/fastrpc/*/dev`, and target `/dev` existence;
- snapshot pstore directory state;
- start a bounded `/dev/kmsg` or `dmesg -w` capture to a private file if available without destabilizing the device.

During B2:

- run one helper invocation only;
- host wall-time cap: short enough to avoid indefinite shell blocking;
- if the command hangs, send serial cancel once and stop;
- do not retry.

After B2:

- remove the temp devnode and helper if the device remains reachable;
- capture `status` and `selftest verbose`;
- if the device rebooted, collect pstore/last_kmsg where available;
- if native init fails to return, use the preplanned rollback path and then stop.

## Abort conditions

Abort before issuing any vulnerable-path call if:

- bridge is unstable;
- selftest has any new fail;
- `adsprpc-smd` major/minor differ from V2286/V2287 without explanation;
- temporary devnode open hangs or fails unexpectedly;
- pstore already contains uncollected crash evidence;
- helper SHA256 is not recorded;
- wrong baseline is resident;
- operator is not actively watching.

Abort during/after the attempt if:

- a single cancel is needed;
- a hang occurs;
- a panic/reboot occurs;
- any unplanned ioctl path is reached;
- cleanup cannot remove temporary artifacts;
- final selftest is not `fail=0`.

Every abort path ends the unit. No second attempt in the same iteration.

## Outcome classification

| Outcome | Meaning | Next action |
| --- | --- | --- |
| `b2-not-run` | gate not approved | stop |
| `b2-preflight-fail` | safety precondition failed | stop and report |
| `b2-invalid-helper-or-scope` | helper or plan violates constraints | stop and redesign |
| `b2-returned-no-crash` | one shot returned without visible kernel fault | report as inconclusive under stock config; no retry |
| `b2-hung-cancelled` | command hung and was cancelled | report; no retry |
| `b2-kernel-warning` | warning/oops but device alive | collect logs; stop |
| `b2-panic-reboot` | kernel panic/reboot observed | collect pstore; rollback if needed; stop |
| `b2-device-unreachable` | native init did not recover | rollback path; stop whole loop if rollback fails |

## Security posture

The correct engineering boundary is:

- B0/B1 can be planned and run as recon.
- B2 is a risky vulnerability trigger and must be treated as a crash-only experiment.
- B3 is exploit development and remains out of scope.

The public sources support taking the bug seriously, not skipping gates. CVE-2024-43047 is a local UAF class with known exploitation reports and high impact. The local device is owned and rollbackable, but the driver path crosses CPU/DSP interaction and kernel memory-map lifecycle state. That makes one-shot, watched, non-retry execution the maximum acceptable B2 shape.

## Decision

V2289 does not authorize Stage B execution.

Approved next choices are:

1. **B1 dispatch-only liveness**: implement/run one invalid-ioctl helper with no real FastRPC command.
2. **B2 go/no-go meeting**: operator explicitly approves the exact phrase above, after which a private one-shot crash-only runner can be designed.
3. **Stop FastRPC trigger path**: keep V2284-V2289 as recon evidence and pivot to another non-exploit unit.

Default if no exact approval is given: stop at B0/B1 and do not enter the vulnerable command families.
