# S22+ UFS V13 with the MAX77705 USB route

Status: **REVIEW_GATED_CAPABILITY** (code and contract review PASS_GO; the
capability record and candidate need their own owner review)

On 2026-11-27 the operator approved the common-contract delegation for this
scope ("그렇게 승인할게 진행해"). The approved summary listed four differing
inputs. The module turned out byte-identical, so the delegation lists three,
which is narrower. Adoption still needs independent review.

This scope runs the adopted report-v13 late-UFS experiment
([capability V2](S22PLUS_MAINLINE_UFS_CAPABILITY_V2.md)) without a USB
replug. It adds the adopted Stage 2 MAX77705 route write
([route policy](S22PLUS_MAINLINE_MAX77705_ROUTE_V1.md)) to the V13 guest, so
that USB enumerates without physical action. The rest of V13 is unchanged.

## Why

ML051 and ML052 used V13 but never reached the module. Every mainline USB
first response since ML021 needed a physical replug:
- in ML051 the cue was refused as too late;
- in ML052 the replug worked, but the cue resolution was recorded after the
  window.

One gated `CONTROL1_W(COM_USB)` removed the replug in seven consecutive boots,
with the cable untouched. The seventh is
[route-timer run 6](../reports/S22PLUS_MAINLINE_MAX77705_ROUTE_TIMER_RUN6_2026-11-27.md).

## What differs from the adopted V13 capability

Only these three inputs differ. Each comes from an adopted artifact or the
adopted source with one stated change.

| Input | Adopted V13 | This scope |
| --- | --- | --- |
| Kernel Image | ML035 transport Image `c4f8d9b0…`, configuration `342fc571…` | `fb1fc155…`, configuration `881e450e…`: the same patched source and configuration with only `CONFIG_I2C_QCOM_GENI=y` (`m` before). No other configuration line changes. The exported symbol versions (`vmlinux.symvers` `fb83fba4…`) are byte-identical. |
| DT | Reduced no-display DT `f918d309…` | The same DT with QUP0 (`/soc@0/geniqup@9c0000`) and its SE5 I2C (`i2c@994000`) set to `okay`, and the SE5 `pinctrl-names` and `pinctrl-0` removed (`51b58a40…`). This is the DT of the adopted MAX77705 observation. TLMM and `gpi_dma0` stay disabled. |
| Guest observer | V13 observer | The V13 observer with the Stage 2 route observer's reads and gated write added, as described below. |

The fixed V13 module `5628f299…` is unchanged. Its rebuild from the V13
component inputs against the new kernel build is byte-identical, with the
same vermagic.

The four-package RAM userspace, the network template, the authenticated
protocol and response layout, the timer child and the producer toolchain are
unchanged.

## Guest composition

Both observers are built from the same canary `init.c`. The composition
applies the V13 insertions first:
- the result digest;
- the dwell and witness;
- the timer child arm before `G0Q_RAM_PID1_BEGIN`.

It then applies the route observer's three sampling insertions, unchanged:
- `mx_begin()` at `G0Q_RAM_PID1_BEGIN`, after the timer child is armed;
- `mx_tick()` every 200 ms while the gadget is bound and the first request is
  awaited, but only while at least one second of the 120-second window
  remains;
- the 200 ms bounded poll that replaces the single wait for the first
  connection.

The composition renders `max77705-usb-route.h` into the observer source. The
shared header file is unchanged. The rendered copy is the adopted header byte
for byte, plus one check placed directly before the write's dispatch. The
write is refused when the dispatch clock read failed or falls at or after
the end of the 120-second window. Candidate reproduction compares the whole
generated source, including the rendered header. The gate and bus effects
are otherwise those of the adopted route observer:
- MAX77705 status reads, which clear the read-to-clear `UIC_INT` and `CC_INT`
  latches;
- `CONTROL1_R` mailbox commands with their mailbox start strobes;
- at most one `CONTROL1_W(COM_USB)` with its strobe, after the gadget is
  bound, only when VBUS, a CC sink, an SDP or CDP charger type and a fresh
  open switch read all hold. It is never retried.

The read commands and the write share one budget of 32 mailbox commands.

No register value is written to the PMIC or FSA4480.

The route record is not appended to the response. The V13 response layout,
its authentication and the host's V13 parser stay exactly as adopted. Two
facts evidence the route:
- an authenticated V13 first response, which requires the enumerated gadget;
- the operator's statement that the cable was not touched.

The write gate code is the adopted one. No record shows whether the write ran
in a given boot. That limitation is accepted, because this scope's question
is the UFS link result, not the route.

## No attach cue

This scope has no attach cue. The cue tool refuses this image. USB must
enumerate without physical action. If no authenticated first response
arrives in the original 120-second window, the run issues no module permit.
The V13 timer child then attempts Download, and the original
owner transfers original A through the existing automatic or attended path.
The existing V13 attach closure already accepts an unissued cue.

## Unchanged

Everything else in V13 is unchanged:
- the one link attempt;
- the late-hardware predicates and the held-USB SH1/CN0 confirmation;
- the 256-byte report envelope;
- the 120/300/540/15-second limits;
- the timer child and its 555-to-570-second Download slot;
- the N-launch-plus-660-second original-owner return;
- one N and one original A;
- no replay;
- the physical fallback, the health-only continuation and final rooted
  Android health.

## Hazards specific to the composition

- **SE5 and QUP0 in the UFS boot.** The I2C GENI driver now probes SE5 at
  boot, and QUP0 votes on its own interconnect paths. In the retained SM8450
  topology, the SE5 configuration and memory paths do not include SH1 or CN0
  members. The voter is shared, though. Commits by other clients, including
  an already pending protected entry, can change the confirmation history.
  Before the overlay, the module requires:
  - the held USB path;
  - an empty commit list;
  - exactly confirmed SH1 and CN0 bucket values.

  A different commit history can change whether that gate passes. No
  predicate is bypassed: a failed gate is a pre-effect refusal, which means
  `NO_PROOF` and a normal return. The adopted MAX77705 observation ran this
  exact DT with USB enumerating normally.
- **Bus sharing.** SE5 serves only the MAX77705 PMIC, USBC and FSA4480. The
  route observer stops sampling once the first connection is accepted, before
  the request is read. It issues no I2C transfer during the dwell, witness or
  module stage.
- **Window end.** No tick starts in the last second of the 120-second window,
  and the write itself is refused at dispatch at or after the window's end,
  or on a failed clock read. A tick that started in time but was delayed,
  by the scheduler or by slow I2C, therefore cannot write late.
- **Module.** The module is the adopted byte-identical V13 module. The new
  kernel exports the same symbol versions.

## Evidence and claims

A completed run can claim:
- the V13 link result, with its usual classes;
- an authenticated USB first response with no physical action.

It does not claim:
- that the route write ran;
- that SE5 sharing had no effect on UFS beyond the module's own report;
- recovery from a hung kernel.

## Authority

This draft grants nothing. Adoption needs:
- the operator's approval of the common-contract delegation text;
- the target paragraph;
- an independent review of the exact capability record, the observer
  composition and the host changes;
- a fresh qualified key-only candidate.

Each run then needs:
- current D0;
- one exact returned one-operation 1800-second approval;
- the operator's attendance, with no action requested;
- usable physical Download;
- a validated prior healthy closure.

Conditional Autonomous F1 remains inactive.
