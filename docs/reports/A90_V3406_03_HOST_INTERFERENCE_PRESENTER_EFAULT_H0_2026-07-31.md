# A90 V3406-03 closed no-proof and host interference diagnosis

Date: 2026-07-31

Status: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`

H0 decision: `A90_V3406_03_HOST_INTERFERENCE_PRESENTER_EFAULT_H0_PASS`

## Closed transaction

Run `a90-v3406-debian-display-f1-20260731-03` consumed its exact F1 and
attended-continuation acknowledgements. It completed one checked boot-only
candidate transfer, one handoff, one exact V2321 rollback transfer, and final
V2321 health verification. Candidate replay and transfer uncertainty are both
false. No non-boot partition was written and no command was sent to the
separately connected S22+.

The durable result SHA256 is:

```text
7bfc8b707b8aacd6dd16acd999ffa1e1b08fa37799360ccdff3c860c9987efde
```

The first post-rollback health read encountered a corrupted native console
frame after `rollback-flashed` was already durable. Rollback-only recovery
resumed from that journal state, did not invoke another transfer, verified
exact V2321 version/build, selftest `fail=0`, and pstore `entries=0`, then
closed the canonical eight-event timeline.

## Valid subproofs and formal boundary

The handoff transcript proves exact source hashes through work-copy creation,
strict native display release, loop-root mount, executable Debian init, and
`exec_switch_root_now`. USB-local SSH then reached Dropbear and returned both:

```text
pid1_comm=init
proc1_exe=/usr/sbin/init
```

Each PID1 line occurs twice: once inside the framed D3 marker and once in the
explicit SSH tail. The observer incorrectly treated two identical occurrences
as ambiguous because it searched the complete response and required exactly
one match. H0 replay reproduces that classifier result. Parsing only the
framed D3 marker restores both independent facts without accepting presenter
log spoofing.

This is valid Debian PID1 and Dropbear mechanism evidence. It does not promote
the atomic F1 result because Debian display acquisition failed and the checked
candidate-return proof was not obtained.

## Presenter failure

The Debian presenter exhausted all three attempts with:

```text
stage=choose-connected-output errno=14 error=Bad address
```

The DRM card existed, DSI and Virtual connectors reported connected, native
release completed, and no native or other process retained a DRM descriptor.
The failure is therefore inside connector discovery, not DRM-master ownership.

The presenter performed the required two-call `DRM_IOCTL_MODE_GETCONNECTOR`
sequence but allocated only mode and encoder arrays. The DRM UAPI also requires
property-ID and property-value arrays for the second call. Nonzero
`count_props` with null `props_ptr` and `prop_values_ptr` explains the observed
kernel copy-to-user `EFAULT` exactly.

The H0 correction now allocates, binds, and frees both property arrays. The
presenter cross-compiles with the pinned AArch64 toolchain as a stripped static
ELF with no dynamic section or interpreter. The rootfs manifest binds the new
presenter source SHA256:

```text
98c65eceadaa8a35b35eabdedaa9edca2c37587bd344e021b1dd6be8d4b2e871
```

## Host USB interference

The candidate did return at the USB layer. Host kernel logs show an automatic
disconnect followed 21 seconds later by successful A90 `04e8:6861`
re-enumeration with both CDC ACM and CDC NCM registered. The host therefore did
not miss the return device.

Two host services then interfered:

- ModemManager classified the A90 ACM endpoint as a modem candidate, opened it,
  sent AT probes, attempted QCDM probing, and failed to create a generic modem.
  The probe interval overlaps the corrupted `cmdv1 versiATATAT` return frame.
- NetworkManager created a generic DHCP wired profile for the re-enumerated NCM
  interface instead of using the manifest-bound A90 profile. Two 45-second DHCP
  attempts failed before the operator physically reconnected the cable.

The operator's later physical disconnect was also reported by the host and was
followed by another successful enumeration. That action reset both ends and is
recovery context, not bounded candidate-return proof. xHCI emitted endpoint
state warnings at disconnect, but enumeration still completed; the direct
causal evidence for the frame corruption is the concurrent ModemManager AT
probe.

The physical disconnect notification narrows but does not eliminate the host
side. It proves that the PC controller observed the detach event; it does not
prove cable signal integrity under load, xHCI endpoint-state recovery, USB
autosuspend behavior, or exclusive ownership of the ACM and NCM functions.
Successful automatic re-enumeration makes a total host-controller or cable
failure less likely for this run. The xHCI warnings keep that class open as a
secondary possibility, while the timestamp-overlapping AT probe is the direct
explanation for the corrupted command frame.

## H0 corrections and next gate

Focused observer, presenter, and guard tests pass `155/155`. The presenter
passes target cross-compilation and static ELF inspection. The attended
display path now arms the bounded transient udev guard before durable handoff
intent. The rule is bound to the current A90 ACM character device, exact
`04e8:6861`, serial, USB topology, interface, and `cdc_acm` driver. The
returned generation must expose both ModemManager ignore properties before the
first native command. The guard is released before retained-pmsg collection; missing,
expired, mismatched, or non-exact release evidence refuses candidate-return
proof. It neither stops ModemManager globally nor writes a persistent udev
rule, and it cannot match the S22+ product ID.

The shared guard keeps its existing 360-second default. A90 alone supplies a
calculated lifetime covering the manifest handoff, SSH observation, return
epoch, and four bounded native commands plus margin; values above the reviewed
3600-second ceiling are rejected before handoff. On return, the runner
re-resolves and compares character-device numbers, driver, serial, interface,
topology, VID/PID, and both ignore properties, then rechecks guard liveness
immediately before its first native command. The helper's exact size and SHA256
are transitively pinned by the manifest-bound orchestrator.

Independent safety review returned `PASS` with no remaining High, Medium, or
Low finding. It verified the calculated lifetime and ceiling, both
pre-dispatch liveness gates, complete returned-endpoint identity,
first-command gate, release-before-pmsg ordering, crash/expiry cleanup,
transitive helper binding, D3-scoped PID1 classification, and all presenter
allocation/free paths.

No new rootfs image, boot image, device action, live authority, or approval
packet was created.

Before another live handoff:

1. bind the manifest-selected NCM profile after each USB generation rather
   than allowing generic DHCP;
2. rebuild an A/B-identical Debian image containing the property-array fix;
3. qualify the unchanged latest native boot as an experimental resident
   baseline before using reboot-only D1 handoff loops.

The V3406-03 candidate, approval, handoff, and rollback transitions are
consumed and non-reusable. No A90 live authority remains.
