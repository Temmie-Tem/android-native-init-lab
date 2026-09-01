# A90 visual evidence

Photographs of the operator-owned Samsung Galaxy A90 5G (`SM-A908N`) running
this project's native PID 1 and, in one run, Debian as PID 1 on the phone's own
vendor kernel.

Everything below was recorded on the physical A90 — photographs, one boot
sequence and one screen-capture clip. The captions separate what is visible in
the frame from the stronger claims established by linked run evidence. Device-reported numbers are labelled as such. Frames are from
different runs and are never presented as one continuous sequence.

Some linked reports sit under `docs/archive/`. Those are historical records
only and carry no current authority, matching the repository's own archive
rule; they are cited here as lineage, not as live proof.

The A90's display panel is physically damaged from a drop. The vertical banding
visible in several frames is panel damage, not a rendering fault, and has no
bearing on headless operation.

**English** · [한국어](A90_VISUAL_EVIDENCE.ko.md)

---

## Debian as PID 1

![Debian 12.14 running as PID 1 on the A90](../images/a90/01-debian-pid1-appliance.jpg)

**What it shows** — Debian 12.14 with `/usr/sbin/init` as PID 1, an ext4 root on
`/dev/block/a90-userdata`, key-only Dropbear SSH and a loopback HTTP service.
288 MB of 5,375 MB used, 37 minutes uptime, battery full.

**Technical context** — this was a switch-root handoff into Debian with
`/usr/sbin/init` as PID 1 on Samsung's vendor kernel. It is not a chroot under a
running Android framework, and not a virtual machine. Native init performed the
vendor-kernel and hardware bring-up, then handed the root over.

**Evidence boundary** — SSH was reachable on the local USB-NCM link
(`192.168.7.2:2222`), not through the tunnel. Public exposure was limited to the
loopback-only HTTP smoke service (`127.0.0.1:8080`) reached through an
accountless outbound Cloudflare quick Tunnel; the run records
`public_exposure=outbound-tunnel-only`. This frame shows one run, not a
continuously operated service.

**Related evidence** —
[`SERVER_DISTRO_DPUBLIC_LIVE_PUBLISH_2026-07-04.md`](../reports/SERVER_DISTRO_DPUBLIC_LIVE_PUBLISH_2026-07-04.md),
[`SERVER_DISTRO_DPUBLIC_BOOT_VISUAL_HUD_2026-07-04.md`](../reports/SERVER_DISTRO_DPUBLIC_BOOT_VISUAL_HUD_2026-07-04.md)

---

## Native init boot sequence

![A90 native init booting on the stock Linux 4.14 vendor kernel](../images/a90/boot-sequence.gif)

**What it shows** — a cold boot recorded on the device: the Samsung splash with
its unlocked-bootloader warning, then native init taking over on the same kernel
those screens just loaded. The serial line resolves across three states —
`USB ACM STARTING`, `ACM GADGET OK`, `TTYGS0 READY` — and the clip ends with the
HUD up, reporting `BOOT OK WIFI-V641- 4.8S`, 276 MB of 5,375 MB and a live log
tail. Build `0.12.008 / H41-BADAPPLE-VIDEO-DEMO-V2`.

**Technical context** — the unlock warning and the Samsung splash are produced by
the stock boot chain, so this is a real cold boot and not a resumed session.
Native init replaces only what runs after them, on the vendor kernel those
screens just loaded.

**Evidence boundary** — a 7-second excerpt of one boot, resampled to 8 frames per
second and denoised for size. It shows the bring-up order this build reports on
its own console; it does not establish timing accuracy, and the later runtime
stack is not in frame. This is a different run and a different build from the
still below.

---

## Native init on the stock vendor kernel

![A90 native init boot screen reporting stock Linux 4.14](../images/a90/02-native-init-stock-kernel.jpg)

**What it shows** — the native init's own boot screen: `KERNEL STOCK LINUX 4.14`,
cache and SD read/write checks, `SERIAL TTYGS0 READY`, HUD menu loading.

**Technical context** — the kernel binary itself remains Samsung's stock 4.14
vendor kernel; the boot ramdisk and userspace are custom, with a static `/init`
taking PID 1. This retains the vendor kernel's device-specific hardware support
instead of reimplementing that support in a mainline port.

**Evidence boundary** — this is the native supervisor, not Debian. It shows the
entry point, not the runtime stack above it.

**Historical identity note** — this photograph predates the promoted V726
baseline and displays `0.9.245 / V726-WIFI-LIFECYCLE`. The later promoted V726
baseline is documented as `0.9.246`. This frame is retained as a historical
snapshot, not as the authoritative V726 artifact identity.

---

## 60-second CPU stress snapshot

![Native CPU stress run with eight cores loaded](../images/a90/03-cpu-stress-60s.jpg)

**What it shows** — a 60-second native CPU-stress run with eight workers and all
eight cores online at 100%. The status screen reported cluster clocks of
1.8 GHz (cores 0-3), 2.4 GHz (cores 4-6) and 2.84 GHz (core 7), CPU 69.7 °C,
load 3.24, 253 MB of 5,375 MB, and about 1.2 W.

**Technical context** — the workload, the thermal and clock readout and the power
figure are all produced by the native runtime's own tooling, with no Android
services running.

**Evidence boundary** — this is a single frame from one run. It shows the reported
values at that instant and does not by itself establish sustained clock
behaviour over the full test. The power figure is device-reported, not measured
with an external meter. The linked formal run used a 10-second test; this
photograph is a later 60-second snapshot and is not that run.

**Related evidence** —
[`NATIVE_INIT_V62_CPUSTRESS_2026-04-26.md`](../archive/legacy/reports/NATIVE_INIT_V62_CPUSTRESS_2026-04-26.md)
(archived)

---

## Idle supervisor and serial control

![Native init HUD reporting 0.3 W idle](../images/a90/04-native-init-hud.jpg)

**What it shows** — native PID 1 idle: reported 0.3 W (0.4 W average), CPU 36.1 °C,
GPU 34.0 °C, 252 MB of 5,375 MB, boot to shell in 3 s, and a live tail of
command and console events.

**Technical context** — the supervisor takes commands over the USB serial console.
The `MENU: HIDE REQUESTED BY SERIAL WORD HIDE` line is a host-issued command
taking effect, and the `CMD: START` / `CMD: END ... RC 0` pairs are the
supervisor's own command accounting.

**Evidence boundary** — idle figures, device-reported, from one session. No formal
run of the same ordinal is claimed for this frame.

---

## DSP firmware sequence and USB networking

![Wi-Fi lifecycle log showing remote processors started and NCM spawned](../images/a90/05-wifi-remoteproc-ncm.jpg)

**What it shows** — 4.6 s after boot: ADSP, CDSP and SLPI remote processors
started with status `0x0`,
`SIBLING FWSSCTL PROOF COMPLETE FAILURES 0 TIMEOUTS 0`, then
`RUN: A90 USBNET NCM SPAWNED PID 570`.

**Technical context** — on this A90 / SM8150 stack, the WLAN path depends on
vendor firmware subsystems being brought up before the interface becomes
usable. Driving that sequence from native init is one of the device-specific
hardware bring-up tasks this project preserves through the vendor-kernel
approach.

**Evidence boundary** — this frame shows the DSP/firmware prerequisite sequence
and the NCM helper launch. It does not by itself establish Wi-Fi association,
throughput, link stability, or sustained operation. The frame also shows a
`CDSP MDT MISSING` condition that the sequence then recovered from, with CDSP
reporting status `0x0` immediately after.

**Related evidence** (lineage) —
[`NATIVE_INIT_V657_SERVICE74_V106_REPLAY_LIVE_2026-05-23.md`](../archive/legacy/reports/NATIVE_INIT_V657_SERVICE74_V106_REPLAY_LIVE_2026-05-23.md),
[`NATIVE_INIT_V726_WIFI_LIFECYCLE_BASELINE_PROMOTION_2026-06-07.md`](../archive/legacy/reports/NATIVE_INIT_V726_WIFI_LIFECYCLE_BASELINE_PROMOTION_2026-06-07.md)
(both archived)

---

## DOOM on the native runtime

![DOOM running with a live dashboard on the native runtime](../images/a90/06-doom-native-runtime.jpg)

**What it shows** — DOOM running under the native runtime with a live dashboard:
native-init `0.10.85`, 640×400 scaled to 960×600, 30.3 FPS target, serial
"doompad" input driven from the host, alongside the usual system readout.

**Technical context** — rendered through the native display and input runtime
after Android userspace removal, with the host driving input over the serial
link.

**Evidence boundary** — this is **not** GPU-accelerated rendering. GPU
acceleration is not supported or proven in this project. This is a
software-rendered workload exercising the display and input paths, and it is
included because it demonstrates those paths end to end, not because it
demonstrates graphics performance.

**Related evidence** —
[`NATIVE_INIT_V3054_DOOMGENERIC_AUDIO_CORUN_LIVE_2026-06-22.md`](../reports/NATIVE_INIT_V3054_DOOMGENERIC_AUDIO_CORUN_LIVE_2026-06-22.md)
— installed init `0.10.85` (`v3053-doomgeneric-audio-corun`), continuous DOOM
loop PASS, native speaker co-run PASS, final health PASS.

---

## Input stack and menu navigation

[▶ `a90-input-stack-demo.mp4`](../images/a90/a90-input-stack-demo.mp4) — 10 s, 1.3 MB

**What it shows** — menu navigation driven from the physical volume and power
keys. The selection moves APPS → POWER → DEMO while the lower panel switches
between `TOOLS AND VIEWERS`, `REBOOT OPTIONS` and `PLAYER HUD DEMOS`, with the
uptime counter advancing from 4.02 s to 10.93 s.

**Technical context** — button events are decoded and surfaced by the custom
input and UI layer running on the stock vendor kernel. This is an interactive
state machine responding to hardware keys, not console output scrolling past.

**Evidence boundary** — this clip demonstrates interactive input handling and
menu state only. No workload is running behind the menu, and it establishes
nothing about service availability. It is the continuation of the same recording
as the boot sequence above.

---

## Native Wi-Fi ownership

![Wi-Fi status screen with the supplicant control socket owned by PID 1](../images/a90/07-wifi-status-supplicant.jpg)

**What it shows** — `wlan0` present, operational, carrier up, with an associated
profile and the supplicant control socket owned by PID 1.

**Technical context** — this belongs to the later native-owned WLAN path, not to
the Debian PID-1 run shown above. A full switch-root was separately observed to
leave `wlan0` visible while the vendor WLAN control plane went down; keeping
native PID 1 alive preserved that control plane, with Debian running as a
chrooted service consumer over USB/NCM.

**Evidence boundary** — the SSID and the address and link-rate fields are masked
in this frame. Association state is shown; throughput is not.

**Related evidence** —
[`NATIVE_INIT_V2177_WIFI_HOLD_RECONNECT_LIVE_VALIDATION_2026-06-09.md`](../archive/legacy/reports/NATIVE_INIT_V2177_WIFI_HOLD_RECONNECT_LIVE_VALIDATION_2026-06-09.md)
(archived),
[`SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA19_NATIVE_OWNED_CHROOT_WIFI_PASS_2026-07-04.md`](../reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA19_NATIVE_OWNED_CHROOT_WIFI_PASS_2026-07-04.md),
[`A90_NATIVE_WIFI_OWNERSHIP_PERMANENCE_EVIDENCE_H0_2026-08-15.md`](../reports/A90_NATIVE_WIFI_OWNERSHIP_PERMANENCE_EVIDENCE_H0_2026-08-15.md)

---

## What these do not show

These photographs are all from the **A90**, which is the only target with the
broader runtime stack.

**They are separate runs.** No two frames on this page are presented as one
continuous session, and none of them should be read as a single end-to-end
demonstration.

**Other targets are at different stages.** The S22+ (`SM-S906N`, GKI kernel
5.10) has a separate host-visible native-PID-1 result, and the kind of proof
changed between its two runs. The earlier P3.25 run proved arrival: the exact
candidate enumerated as `04e8:6861` / `cdc_acm` and an exact 49-byte banner was
retained. The later P3.26 run extended that into a bounded bidirectional control
exchange — host-to-device and device-to-host traffic through the fixed ACM
channel, a run-bound PID 1 `PONG`, and a static BusyBox `ash` `SHELL-OK` reply,
with `pid1_bidirectional_proof` and `busybox_shell_roundtrip_proof` both true and
zero trailing bytes. Both runs closed with the required rollback and a healthy
rooted Android return. The BusyBox child exits after its fixed reply, so this is
a fixed exchange rather than a general interactive shell. The S20+
(`SM-G986N`) has a deterministic PID-1 candidate but no live PID-1 proof yet.
Neither target has the A90's broader runtime stack, and authority, artifacts and
evidence never transfer between targets.

**The pictured Debian run is not the final architecture.** It is a real PID 1 /
switch-root handoff, but it is weaker than the isolation this project has
selected as its target. The intended namespace-isolated successor — Debian as
PID 1 inside separate PID, mount, IPC, UTS and network namespaces, with a
`pivot_root` and a reviewed veth network boundary — remains unproved end to end.
The stock A90 kernel has `CONFIG_VETH=n`, which blocks the selected veth-based
boundary, and the design explicitly does not accept a shared network namespace,
a chroot, or a userspace proxy as a fallback. That unit is paused rather than
downgraded.

**Numbers on screen are device-reported.** Power, temperature and clock figures
come from the device's own tooling and have not been cross-checked against
external instrumentation.

**GPU acceleration is not supported or proven**, and nothing on this page should
be read as evidence of it.
