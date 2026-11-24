# S22+ mainline USB route intervention: design and H0 (Stage 2)

Date: 2026-11-25
Target: Galaxy S22+ `SM-S906N` / `g0q` / FYG8, Linux 7.2.11 mainline + Debian RAM PID1.
Scope: host-only design, build and qualification. No device contact. Nothing
here grants device authority; the [policy](../operations/S22PLUS_MAINLINE_MAX77705_ROUTE_V1.md)
does, after review and adoption.

## Why a write now

The [root-cause plan](S22PLUS_MAINLINE_REPLUG_DEPENDENCY_ROOT_CAUSE_H0_2026-11-22.md)
made Stage 2 conditional on Stage 1 reading `0x3f`. The
[Stage 1 run](S22PLUS_MAINLINE_MAX77705_USB_RUN_2026-11-25.md) read
`CONTROL1 = 0x3f` at 0.011 s and 10.020 s. At those times `BC_STATUS` was
`0x82` (VBUS present, ChgTyp 2 = CDP) and `CC_STATUS0` was `0xa1` (sink).
The host port watch saw no connect until the replug.

Two other facts shape the design:
- **BC1.2 had already run before the first read.** ChgTyp CDP means the port
  was classified, yet the switch stayed at explicit open.
- **The IC itself reset CONTROL1 on cable-out.** It changed from `0x3f` to
  `0x00`, which is also "open" per Samsung's header comment. There is still
  no sample of what the switch read while USB worked after the replug.

## Three-way design discussion

Claude, Codex `gpt-6.2-sol` and Gemini 4 Carbon (High) answered the same brief
independently. The record is in private
`outputs/s22plus-usb-route-discussion-20261125-1/`.

All three agreed on four points:
- **Run Stage 2 with Stage 1b's telemetry folded in.** A second read-only run
  cannot remove the replug, so it would force the write run anyway.
- **Write `0x09` (COM_USB, NoBCComp = 0).** This is what Samsung's FYG8 driver
  writes on USB and CDP attach, and what fixed the r0q/Tab S8+ port. `0x00`
  is "open", and `0x89` would change a second variable.
- **One attempt.** It is never retried, and it is skipped on any gate miss.
- **Move the fallback cue to W+45 s.** The cue tool needs more than 60 s left
  in the 120 s window.

Codex and Carbon moved the write after gadget bind; Claude's "before bind"
was withdrawn. Their reason: writing after bind, following a "not attached"
dwell, gives a same-boot control. Mainline 7.2.11 sets the gadget state to
`default` only from a bus reset (`usb_gadget_udc_reset`), so "not attached"
after bind means the host has not reset the device.

## Producer

[`max77705-usb-route.h`](../../workspace/public/src/mainline/s22plus_canary_h0/max77705-usb-route.h)
keeps every Stage 1 read and adds the following.

**Single write.** At most one `CONTROL1_W(COM_USB)` is sent, as Samsung's
bulk opcode write `[0x21, 0x06, 0x09]` followed by `0x00 → 0x41`. A separate
function allows it only once and only after the gate has passed.

**Gate.** Every condition below is evaluated once:
- the UDC has read "not attached" for a continuous 3 s;
- there has been no IC change and no failed read since boot;
- a fresh pre-read returns `0x3f`;
- a final re-sample, taken UDC first, then IC, then UDC again, shows no change;
- the UDC is "not attached" on both sides of that re-sample;
- VBUSDet is set, ChgTyp is SDP or CDP, and CCStat is sink;
- at most 50 ms pass between the start of the re-sample and the write. The
  same clock value is the write time.

**Telemetry.**
- The UDC state is sampled every 200 ms, before the IC, so any cable change
  completed before a `configured` sample lands on the same event or earlier.
- A read that was skipped because of the 1 s command spacing is made later as
  a deferred read.
- The write is read back.
- One read is taken at the authenticated request.
- A failed sample is kept as a `gap` event, with whatever interrupt flags it
  cleared.

**Record v2.** The record is 832 bytes, which brings the body to 1184 bytes.
It contains a 64-byte header with the gate, the write status and echo, the
dwell and write times, and 48 events of 16 bytes, each with the UDC state.

## Decoder and outcomes

[`max77705_route_record.py`](../../workspace/public/src/mainline/s22plus_canary_h0/max77705_route_record.py)
is embedded in the board verifier. The HMAC proves origin. The decoder also
rejects records the producer cannot emit:
- the UDC-event grammar, change events without a change, and status
  continuity;
- a non-final request read;
- write fields without a written gate;
- write events whose UDC state is not "not attached";
- more than one route write.

### Outcomes

| Verdict | Reading |
|---|---|
| `ROUTE_CONFIGURED_WITHOUT_REPLUG` | The write was acknowledged and read back as `0x09`. The UDC reached `configured` before any physical change, failed sample or reversion. With no cue issued before the response (binding module), the routing write removed the replug dependency for this boot. |
| `ROUTE_CONFIGURED_AFTER_REPLUG` | `0x09` held, but enumeration followed a cable change. Routing alone was not sufficient, so H4/PHY or another path leads. |
| `ROUTE_PARTIAL_ENUMERATION` | The UDC left "not attached" but never reached `configured`, which points to H2 / enumeration. |
| `ROUTE_WRITE_NOT_HELD` | A non-`0x09` read came before the first change. The IC overrides AP routing, and H1 is untested. |
| `ENUMERATED_BEFORE_WRITE` | The host reset the device before the write. That refutes H1 for this boot. |
| `SKIP_INITIAL_COM_USB`, `SKIP_PREWRITE_NOT_OPEN` | The switch was not at `0x3f`, which is a state finding. |
| `ROUTE_COVERAGE_GAP`, `ROUTE_WRITE_FAILED`, `EVENTS_DROPPED`, `SKIP_*` (other) | Inconclusive for the intervention. |

## Review

Codex reviewed the producer, decoder, fake device and tests over several
rounds. Each finding became a producer scenario in
[`max77705_route_fake.c`](../../workspace/public/src/mainline/s22plus_canary_h0/max77705_route_fake.c):
- **r1:** a stale gate after the pre-read; interrupt flags lost on a failed
  read; an impossible UDC flip;
- **r2:** an observed UDC departure on a failed tick; IC-then-UDC ordering;
  a non-final request;
- **r3:** a stale trailing UDC; a forged write UDC;
- **r4:** an unbounded gate age; a change event without a change;
- **r5:** a separate dispatch clock; a status-byte mismatch;
- **r6:** status continuity;
- **r7–r14:** pre-write edges seen by mailbox polls; ring-wrap PASS; status
  changes on gap events; blind gaps; session binding of readbacks, partial
  enumeration and after-replug evidence.

From r9 on, decoder-only forged-transcript flips were classed as
non-blocking, because the HMAC is the integrity boundary, as for Stage 1.
Blocking findings were limited to producer write safety, genuine producer
records that were rejected or misclassified, and usability. Before that
change, completion-time scheduling checks had rejected 14 genuine wrapped
records. Those checks were removed.

r15 returned `PRODUCER_PASS_GO` at `d57179f83f`. Codex's sweep covered 400
producer-generated schedules, 201 of them wrapped: every record decoded,
with no disallowed write and no repeated write. One non-blocking
classification fix followed in `39ff895323`. The producer files are on main
in `837ca61e0e`.

## Board package

Built in private `analysis/s22plus-max77705-route-board.IL8XkQTV/`. The build
copies the Stage 1 board build step for step and substitutes only the route
profile.

| Item | Value |
|---|---|
| AP | `edde39dd7f71569e388c807e6127e43d08bdaa4b074f22dae7d74e639d69b714`, 25,497,641 B; two independent packagings are byte-identical |
| boot v4 (96 MiB) | `75f36c5c…3dc4` |
| uniLoader | `dc09a43d…6523`, 45,729,888 B; placement guard passed, no fixed-reservation overlap |
| Image / DT | `d7df52a1…f609` / `51b58a40…8235`, the Stage 1 Image and DT unchanged |
| Board observer | `598268f4…9897`, 729,912 B. A rebuild from regenerated sources is byte-identical, and a VM-flag board build fails at `#error` |
| RAM archive | `4d0aa18f…6a8f`; versus ML022, only the observer member differs |
| Loader-handed DT | 500,000 B, `ad6c8eb3…0a68`. Compared with the Stage 1 candidate's, only `/chosen linux,initrd-end` differs |
| Board decoder | `2fb8cb9c…344f` (the route record decoder is embedded) |
| Qualification | `final-6oe6vxek/qualified-artifact.json`, `c0a0e3ec…8a0e` |

**Loader checks.** The unicorn qualification passed. A QEMU run with the
retained `gdb-multiarch` reached the relocated entry at EL1 and EL2 and was
rejected at EL3.

**Fixture responses.** The fixture records are not synthetic: the real route
producer on the simulated device produced them. An AArch64 codec built from
the shipped `protocol.h` signed them with a disjoint key, and the C and
Python HMACs agree. The board verifier read six verdicts:
`ROUTE_CONFIGURED_WITHOUT_REPLUG`, `ROUTE_CONFIGURED_AFTER_REPLUG`,
`SKIP_INITIAL_COM_USB`, `ROUTE_WRITE_NOT_HELD`, `ROUTE_COVERAGE_GAP` and
`NO_PROOF_IDENTITY_MISMATCH`. It rejected eleven cases:
- a non-handle input;
- a failed capture;
- the real candidate key;
- an old challenge;
- a VM claim;
- the gate changed after signing;
- a command overflow;
- a rejected-write count;
- a second route write;
- an added empty DT leaf;
- SE5 set back to `disabled`.

**VM integration** (private `analysis/s22plus-max77705-route-vm.C5Jqdr1F/`,
QEMU 10.2.1, the I2C GENI kernel):

| Case | Result |
|---|---|
| ok | `AUTHENTICATED_H0_MAX77705_ROUTE_OBSERVATION`, adapter absent, 0 commands, `NO_PROOF_ADAPTER_ABSENT` |
| bad key | 0 bytes; the observer parked with `EACCES` |

**Offline binding** (`bind_check.py`). The route module binds the real
qualification. Producer records signed with a fixture key and verified
through the session wire map as expected:

| Record | Cue | Verdict |
|---|---|---|
| `pass` | not issued | `ROUTE_CONFIGURED_WITHOUT_REPLUG` |
| `pass` | issued | `ROUTE_CONFIGURED_AFTER_CUE` |
| `nofix` | issued | `ROUTE_CONFIGURED_AFTER_REPLUG` |

Eight identity substitutions are rejected: the AP, the member, the key
commitment, the run ID, the decoder, the FDT, the qualification, and the
Stage 1 schema.
