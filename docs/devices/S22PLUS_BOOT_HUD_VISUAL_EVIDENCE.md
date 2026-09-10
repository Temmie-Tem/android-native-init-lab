# S22+ boot HUD visual evidence

Physical-panel records of the operator-owned Samsung Galaxy S22+ 5G
(`SM-S906N`, FYG8) booting a custom static `/init` as PID 1 and painting its own
status text on the panel, with no Android framework, SurfaceFlinger or Zygote in
the picture.

**This page collects more than one attended run.** Every asset here is a camera
pointed at a physical panel: none of it is a pixel readback, and none of it is
machine-authenticated. Beyond that shared floor, **each run's binding and
evidence boundary are independent.** What one run's recording carries on screen,
another's does not; what one recording fails to capture, another may show. Each
section below states its own scope, its own agreement with the machine record
and its own limits, and none of those transfer between runs.

| Run | Candidate | Recorded | What its recording adds |
| --- | --- | --- | --- |
| [P376](#p376--first-native-boot-hud) | v0.1.0 boot HUD | 2026-09-09 | the first native frame, and an uptime counter advancing on its own schedule |
| [P384](#p384--live-gauge-hud-and-the-native-to-download-transition) | v0.2.0-rc.2 | 2026-09-10 | populated gauge fields changing across HUD states, and a native-to-Download transition with nothing entering the frame |

This is not an overview of the S22+ target. The write-combine/cached buffer
comparison from the P353-P361 display series is a separate page,
[S22+ display visual evidence](S22PLUS_DISPLAY_VISUAL_EVIDENCE.md); the kernel
rebuild, native PID 1 and USB results live in [`S22PLUS.md`](S22PLUS.md).

**English** · [한국어](S22PLUS_BOOT_HUD_VISUAL_EVIDENCE.ko.md)

---

# P376 — first native boot HUD

Recorded 2026-09-09. This is the on-screen half of the native console line —
P375 gave PID 1 an authenticated root console, and P376 added a separate text
HUD child beside it.

P376 was a single attended boot-only transfer that ended in an exact Magisk
rollback and a verified healthy rooted FYG8 return. It is closed, and neither the
candidate nor the observation is replayable.

**Every P376 image below comes from one continuous camera recording**, and
**nothing on the P376 panel identifies the running image**: the state snapshots
PID 1 sends the HUD carry a run identifier, but this renderer never paints it,
so the clip cannot, on its own, bind this boot to the P376 candidate.

## The boot chain in one take

![P376: the unlocked-bootloader warning, the Samsung splash under a red unofficial-software banner, then five lines of native init text whose uptime counter advances once a second](../images/s22plus-native-runtime/05-boot-to-native-hud.gif)

**Full clip** — [▶ `05-boot-to-native-hud.mp4`](../images/s22plus-native-runtime/05-boot-to-native-hud.mp4)

**What it shows** — the last 22.5 seconds of a 31.1-second continuous handheld
recording: the unlocked-bootloader warning screen, then the Samsung Galaxy
splash under a red banner stating that the installed software is not official
Samsung software, then the splash replaced by five lines of white bitmap text on
black whose `UPTIME` value advances once a second until the recording stops.

**Why the single take matters** — the vendor boot chain handing the panel over
to native init is inside the same unbroken shot as the counter that follows it.
The panel is never out of frame and the recording is never cut, so the ordering
of the three screens is a property of the recording itself rather than of how
the assets were assembled.

**Measured from the recording** — the warning screen holds until t≈9.8 s; the
splash runs from t≈9.8 s to t≈20.0 s; the first native frame appears at
t≈20.0 s and the panel shows native output for the remaining 11.1 s.

## What the stock chain says before native init runs

![P376: the unlocked-bootloader warning screen](../images/s22plus-native-runtime/01-bootloader-unlocked-warning.jpg)

![P376: the Samsung Galaxy splash under a red banner stating the installed software is not official Samsung software](../images/s22plus-native-runtime/02-not-official-software-splash.jpg)

**What they show** — the stock unlocked-bootloader warning, then the Samsung
Galaxy boot splash with a red banner across the top reading, in Korean, that
official Samsung software is not currently installed on this phone, that
function or security may be affected, and that software updates will not be
installed.

**Why they are on the page** — this is the stock chain's own statement, made
before any code from this project runs, that the image about to boot is not
Samsung's. It is a provenance signal, not an authentication: it establishes that
*an* unofficial image is installed, and says nothing about *which* one.

## The first native frame

![P376: five lines of white bitmap text on black - NATIVE INIT, PID1: RUNNING, UPTIME: 000003 S, CONSOLE: READY, STATUS AT LAST UPDATE](../images/s22plus-native-runtime/03-first-native-frame.jpg)

**What it shows** — five lines of white bitmap text on black: `NATIVE INIT`,
`PID1: RUNNING`, `UPTIME: 000003 S`, `CONSOLE: READY`, and `STATUS AT LAST
UPDATE`. The rest of the panel is black. `STATUS AT LAST UPDATE` is only a
label in the current renderer — no associated value or detail line is painted
beneath it — so the blank area below it is expected, not a missing update.

**Technical context** — the HUD is a separate child of PID 1 that receives fixed
nonblocking state snapshots over a run-bound `SOCK_SEQPACKET` channel. PID 1
remains the sole console owner; the HUD renders what it is handed. `CONSOLE:
READY` is therefore PID 1's own reported console state at the moment of that
snapshot, not an independent measurement of the console.

**Evidence boundary** — a photograph of a panel is not a readback. This frame
shows that text of this shape was on the screen; the byte-exactness of what the
renderer *paints* is established host-side in the run's own H0 evidence, not
here.

## Twelve consecutive states

![P376: the UPTIME and CONSOLE lines sampled once a second, showing 000003 through 000014 with CONSOLE READY on the first and BUSY on the rest](../images/s22plus-native-runtime/04-uptime-filmstrip.jpg)

**What it shows** — the `UPTIME` and `CONSOLE` lines, cropped from the same
recording once per second and stacked in order: twelve consecutive integer
values, `000003` through `000014`, with no skipped and no repeated value.
`CONSOLE` reads `READY` on the first and `BUSY` on the remaining eleven.

**Measured from the recording** — sampled at 2 fps across the visible window,
every displayed value appears in exactly two consecutive samples: eleven
increments across 11.0 s of recorded time. The counter on the panel and the
recording's own clock agree to the sampling resolution. This measurement is
self-contained — it needs nothing outside the clip.

**What that is, and is not** — this is the first S22+ asset in which the panel
changes on its own schedule rather than holding a frame that was painted before
the commit. It is not a liveness result for the system: it shows one counter
advancing for eleven seconds, and says nothing about what else was running, or
about anything after the recording stopped.

**Technical context** — each visible update is not a repaint. P376 allocates a
fresh, non-imported GEM buffer per frame and paints it once before its first
scanout mapping; one atomic commit is in flight at a time; an exact
`FLIP_COMPLETE` event is required before the previous buffer is retired, and at
most two framebuffers are held. The display page's limit therefore still stands:
there is still no in-place redraw of an existing buffer, and no compositor.

## Where the P376 clip meets the machine record

The run's machine evidence and this recording are different classes of evidence,
and neither authenticates the other.

**What the machine retained** — the initial HUD proof retains three matched
frames, sequence 1 through 3, uptime 3,802 to 5,815 ms, with two `BUSY` console
snapshots. A later plan command confirmed further frames after a ten-second wait
and emitted `HUD_STILL_UPDATING`; its last retained frame is sequence 19 at
uptime 21,941 ms. The run report states plainly that a matched flip event does
not prove physical pixels, and that intermediate frame retention and continuous
liveness are not claimed.

**What the recording shows in that visible range** — displayed values 3, 4 and
5, with `READY` on 3 and `BUSY` on 4 and 5. The renderer formats whole seconds,
so a retained uptime of 3,802 ms is displayed as `000003`. The recording ends
at displayed value 14, well before the machine's last retained frame at
21.9 s.

**What that agreement is worth** — it is a check that could have failed and did
not. It is not proof in either direction. The camera cannot authenticate the
journal, and the journal cannot authenticate the camera; read the two as
independent records that did not contradict each other.

**The operator's own answer is recorded separately.** During the run the operator
was asked whether `NATIVE INIT` text and an increasing `UPTIME` were visible on
the physical screen, and answered that they were. That response is retained in
the private run directory, classified as an operator-reported observation with
`machine_pixel_proof: false`. This recording is the material behind that answer.
It was not merged into the sealed run record and changes no machine verdict.

**The time binding is circumstantial.** The clip's container timestamps fall
inside the run's live-session window, but they are written by the recording
handset, they are not authenticated, and they are not self-consistent — the
container and stream creation times differ by about four minutes, which is what
re-containering on transfer looks like. Nothing in the clip carries a signed or
kernel-assigned time.

## What the P376 recording does not show

**The rest of that run is not in this shot.** CONTROL acceptance, the Download
endpoint, the exact rollback and the final health verification each have their
own separate evidence and none of it is visible here. The observer's ACK-only
`software_download_arrival=UNPROVED` and the supplemental stock
`p376_proof_class=NO_PROOF_OBSERVER` are unchanged; a successful console and HUD
qualification does not promote either.

---

# P384 — live gauge HUD and the native-to-Download transition

Recorded 2026-09-10, one day and eight candidates after P376. Between them the
HUD gained system-status fields (v0.1.1), then gauge telemetry that took five
candidates to confirm (v0.1.2), and the run itself is no
longer boot-only: P384 is the attended native roundtrip, which installs the
native image, returns to Download from inside the native runtime, restores the
same image once more, and then cleans up to Android.

P384's original invocation completed `PASS_F1_V2_P384_ROOT_CONSOLE_AND_ROLLED_BACK`,
CLOSED/19, with one N installation, one exceptional same-N restoration and one
exact Android cleanup. It is consumed and not replayable. The device is in
healthy Android and this transaction retains no running native baseline.

**Unlike the P376 HUD, this renderer visibly carries the candidate label
`V0.2.0-RC.2`.** That strongly narrows the visual identity, but a camera-visible
label is still self-reported presentation, not cryptographic artifact
authentication.

## The complete take

**Full clip** — [▶ `06-p384-native-to-download.mp4`](../images/s22plus-native-runtime/06-p384-native-to-download.mp4)

**What it shows** — 23.5 seconds, one continuous shot, from the stock
unlocked-bootloader warning through to Download mode: the warning screen, the
Samsung Galaxy splash, the red unofficial-software banner joining it, the
`NATIVE INIT` gauge status HUD labelled `V0.2.0-RC.2`, a dark panel, and then
the Download screen reading `Downloading…` / `Do not turn off target`.

**Measured from the recording** — 705 decoded frames across 23.51 s with no
presentation-timestamp gap above 50 ms, so the take is unbroken and uncut. The
warning screen holds to t≈2.2 s; the splash runs from t≈2.2 s, with the red
banner joining at t≈7.8 s; the first native frame appears at t≈12.42 s; the last
native frame is at t≈17.35 s; the panel is dark from t≈17.40 s to t≈20.95 s;
Download-mode text is legible from t≈21.7 s to the end of the take.

**Why the single take matters here** — the same reason it mattered for P376, and
one more: the native HUD, the dark interval and the Download screen are all
inside one shot in which the device never moves and nothing is added to the
scene. The ordering *and the absence of intervening physical action* are both
properties of the recording rather than of assembly.

## Gauge fields becoming populated

![P384: six HUD states stacked in order. The first two show UPTIME 000003 with WAITING FOR AUTH then CONSOLE READY, and gauge SOC, voltage and current all reading N/A. The remaining four show CONSOLE BUSY at UPTIME 000004 through 000007 with gauge SOC 99.4% and voltage and current values that change between states](../images/s22plus-native-runtime/07-p384-gauge-activation-filmstrip.jpg)

**What it shows** — six displayed HUD states in order, each row pairing the
`UPTIME`/console lines with the `GAUGE SOC`/`VOLTAGE`/`CURRENT` lines from the
same frame. The first two rows have every gauge field at `N/A`. The last four
carry populated values.

**The recording independently shows the displayed gauge fields becoming
populated and changing across successive HUD states.** Getting values onto those
lines took five candidates. v0.1.2-rc.1 and rc.2 both closed with every gauge
field reading `N/A` on the panel, and rc.2's added diagnostics localized that to
a device-tree root-model allowlist rejecting the driver before any bus read.
rc.3 and rc.4 did display values but closed NO_PROOF on console output loss and
a host journal-size overrun respectively. rc.5 was the first to close with gauge
proof.

**Measured from the recording** — the HUD's first painted state, at t≈12.42 s,
reads `UPTIME: 000003 S` / `WAITING FOR AUTH` with all gauge fields `N/A`. It
becomes `CONSOLE: READY` at t≈12.55 s, still `N/A`. At t≈13.42 s a single
combined update changes `UPTIME` to `000004`, the console line to `BUSY`, `MEM`
from `1026/7002` to `1052/7024 MIB`, `CPU` from `N/A` to `1.8%`, and every gauge
field from `N/A` to a value. Four distinct populated states follow, each holding
about a second:

| Displayed from | `GAUGE SOC` | `VOLTAGE` | `CURRENT` |
| ---: | ---: | ---: | ---: |
| t≈13.42 s | 99.4% | 4.337 V | +424.2 mA |
| t≈14.5 s | 99.4% | 4.335 V | +436.7 mA |
| t≈15.4 s | 99.4% | 4.338 V | +401.5 mA |
| t≈16.5 s | 99.4% | 4.337 V | +444.5 mA |

`SAMPLE AGE` and `GAUGE AGE` both read `0.2 S` in every populated frame, and
`BATT TEMP` and `CHARGE` stay `N/A` throughout — those two are not derived from
current direction and are not claimed.

**What that is, and is not** — it shows that the panel displayed changing
battery-gauge values, on its own schedule, during a native boot. It is not a
measurement of the battery: the accuracy of any displayed value, and its
correspondence to a particular authenticated sample, are not established here.
Gauge SOC is a fuel-gauge reading and is not Android's battery-policy
percentage.

## Native HUD to Download, with nothing entering the frame

![P384: eight frames of the whole scene in order. The first shows the native HUD at UPTIME 000007 with populated gauge fields and the V0.2.0-RC.2 label, the next three show a dark panel, then a white screen, then three frames of the teal Download mode screen. The phone lies in the same position in every frame and nothing else is in the shot](../images/s22plus-native-runtime/08-p384-native-to-download-filmstrip.jpg)

**What it shows** — eight whole frames from the same take, in order and
uncropped: the native HUD, three frames of dark panel, the bright transition,
and three frames of Download mode.

**During the continuous recording, the device transitions from the native HUD to
Download mode with no visible physical contact or object entering the frame.**
The phone lies in the same position in every one of the take's 705 frames, and a
sweep of the complete take at 5 fps shows no hand, finger, cable movement or
other object at any point — including the opening warning screen, which reads
"press the power button to continue" and advances at t≈2.2 s untouched.

**This visually excludes a visible button press during the recorded transition;
it does not establish software-causal attribution.** The P384 records themselves
mark physical intervention `UNOBSERVED` rather than proving its absence, and
this recording is observational evidence of the same kind — stronger than a
still, and still not causal proof. Entering Download mode by button requires a
key combination held on this device; no such action is visible.

**Measured from the recording** — mean panel luminance holds steady while the
HUD is up, drops sharply between t≈17.35 s and t≈17.40 s, stays low for
3.55 s while the camera's own exposure adapts, and jumps at t≈20.95 s to the
bright screen that resolves into Download mode. The gradual brightening across
the dark interval is the camera, not the panel.

## Where the P384 clip meets the machine record

**What the machine retained** — each of the two native arrivals produced an
optional HUD log with five valid frames, three fresh gauge samples, three fresh
memory/CPU samples and a matched flip observation. Neither log proves physical
pixels, uninterrupted liveness or pre-authentication display timing. The
separately validated return records prove exact Download arrival inside each
original 30-second CONTROL window, with window-close intervals of 7.381595 s and
8.245343 s after the respective CONTROL intent. CONTROL ACK remains acceptance
only, and software-causal attribution remains UNPROVED.

**What the recording shows in that range** — a HUD whose gauge fields are
populated and changing, and a transition into Download. The recording's four
distinct populated gauge states and the log's three fresh gauge samples are
different counts of different things — displayed states versus retained samples
— and are not put into correspondence here.

**The recording does not span a whole arrival.** Its native window is about five
seconds, from `UPTIME: 000003 S` to `000007`. Each arrival's observation ran
considerably longer, 27.493317 s and 15.654757 s respectively.

**The clip records a P384-labelled native HUD followed by Download. It does not
independently establish whether this is the first or the restored native
arrival.** Both arrivals boot the same N image and would show the same stock
chain, and the camera clock cannot resolve between them.

**The time binding is circumstantial.** The take falls inside the run's
live-session window of 11:50:28.633772Z to 11:52:48.608832Z, but its container
timestamps are written by the recording handset, are not authenticated, and are
not self-consistent — the container and stream creation times differ by about a
minute. The on-screen `V0.2.0-RC.2` label is the stronger of the two bindings,
and it is still self-reported presentation.

## What the P384 recording does not show

**The roundtrip's return leg is not in this shot.** The take ends in Download
mode. The restoration transfer, the second native arrival, the exact Android
cleanup and the final health verification each have their own evidence and none
of it is visible here.

**Supplemental stock carrier evidence is unchanged.** It remains
`P320_STOCK_WITNESS_BASE_SHAPE_FAILURE` / `NO_PROOF_OBSERVER`, and neither this
recording nor the run's own console result promotes it.

---

# Asset handling

Stills were cropped only to remove unrelated room and background content around
the phone, using a fixed crop per run. Nothing inside any panel was retouched,
masked, denoised, or colour- or exposure-adjusted. Both clips were transcoded
from HEVC to H.264 for playback here, scaled down, and stripped of the recording
handset's container metadata. Neither was cut, and each is the complete take. No
device-screen content, frame order or visible event sequence was altered in
either. Neither original carries an audio stream or location metadata; the
originals are retained byte-for-byte in their own private run directories.

For P376, the inline GIF is a presentation copy, resized and resampled to 4 fps.
Its start is trimmed into the static warning screen at t≈8.6 s so that both
screen transitions remain inside it; **no interval between display updates is
removed**. The twelve-row filmstrip is cropped from the same clip, one second
apart, in order.

For P384 there is no GIF: the full clip is 23.5 seconds and is the primary
evidence. Its two filmstrips are drawn from that clip. The gauge filmstrip's six
rows are separate displayed HUD states, each row pairing two crops taken from
one frame, with the unchanged `MEM`/`AVAILABLE`/`CPU` block between them omitted
for legibility. The transition filmstrip's eight frames are whole frames,
uncropped, so that the scene around the device is visible.

Every measurement quoted on this page is derived from the full-length H.264 clip
of the run in question, which stays linked in that run's section.

Two things visible in the stills are not panel content. The dark rectangle low on
the screen is the recording handset reflected in the S22+'s glossy panel, and
the chipped area at the top-left corner is physical wear on the device.

The clips were recorded on the operator's own separate handset, which is not a
target of this project and appears nowhere in the binding target registry. It is
the camera, not a device under test.

---

# What no asset on this page shows

**No frame here is a readback.** Every image on this page is a camera pointed at
a screen. The byte-exact evidence for each run is host-side and lives in that
run's report.

**This is not a standalone boot UI.** The HUD starts after authenticated native
console preparation. It is not an unauthenticated screen that any boot of these
images would produce.

**This is not a display runtime.** What exists is a per-frame allocate, paint,
commit and retire cycle driving a fixed text layout. There is no compositor, no
input, no in-place redraw, and no proof of general or long-running display
operation.

**Nothing here transfers to another target.** The A90 and S20+ received no
command from either run, and results, artifacts and authority never move between
devices.

**Nothing here creates authority.** Both runs are consumed and closed. No asset
on this page grants a device grant, a native lease, a replay, or a standing
native baseline.

---

# Related evidence

- [`S22PLUS_FYG8_NATIVE_ROUNDTRIP_FOLLOWUP_V2_H0_2026-09-10.md`](../reports/S22PLUS_FYG8_NATIVE_ROUNDTRIP_FOLLOWUP_V2_H0_2026-09-10.md)
- [`S22PLUS_FYG8_LOCAL_DISPLAY_ADOPTION_H0_2026-09-10.md`](../reports/S22PLUS_FYG8_LOCAL_DISPLAY_ADOPTION_H0_2026-09-10.md)
- [`S22PLUS_FYG8_P376_BOOT_HUD_H0_2026-09-09.md`](../reports/S22PLUS_FYG8_P376_BOOT_HUD_H0_2026-09-09.md)
- [`S22PLUS_FYG8_P375_ROOT_CONSOLE_H0_2026-09-09.md`](../reports/S22PLUS_FYG8_P375_ROOT_CONSOLE_H0_2026-09-09.md)
- [Boot HUD capability contract](../operations/S22PLUS_FYG8_BOOT_HUD_V1.md)
- [Root console capability contract](../operations/S22PLUS_FYG8_ROOT_CONSOLE_V1.md)
- [S22+ target contract](../operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md)
