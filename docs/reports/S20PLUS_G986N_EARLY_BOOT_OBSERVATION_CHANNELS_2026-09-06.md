# S20+ early-boot observation: three refuted channels and what replaced them

Date: 2026-09-06. Target: `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`.
Status: **NO DEVICE ACTION TAKEN. ALL CANDIDATE EVIDENCE CHANNELS REFUTED BEFORE
USE; THE LANE NOW MEASURES THE RECORD FORMAT IT HAD BEEN ASSUMING**.
Device reboots, mode transitions, partition operations, consumed candidates and
S22+/A90/other-target commands in this work: **0**.

## The problem this lane has

Three P0 native-PID1 F1 candidates are consumed. Every one completed its full
180-second observation window and emitted no banner, so "PID1 never ran" and
"PID1 ran and nothing reached the host" were never separated. The lane does not
lack candidates. It lacks a channel that can tell those two apart.

Everything below is about finding one, and about three attempts that looked like
one and were not.

## Channel 1: the ACM banner (consumed, three times)

The candidate brought up configfs, a USB gadget, a UDC binding and `ttyGS0`, then
wrote a banner over ACM. To create its own node it first had to read
`/sys/class/tty/ttyGS0/dev` for the major and minor, so the banner could only
appear once the entire chain had bound.

Refuted by its own results. A silent failure anywhere in that chain produces
exactly the observation seen three times: a completed window with no banner,
indistinguishable from `/init` never running.

## Channel 2: Download-mode arrival (refuted at review, never fired)

The replacement candidate requested Samsung download mode from PID1 and treated
Download-mode enumeration as the proof. It needed no gadget, no serial I/O and
no buffer surviving a reboot, and the technique was taken from the S22+ lane
where a raw PID1 with zero modules and an immediate download reboot did reach
Download.

Independent review refuted it, and the source agrees:

- the transfer command carries its own `--reboot`
  (`s22plus_boot_only_f1_transport.py:217-228`);
- `identify_download` records no provenance
  (`s20plus_g986n_boot_recovery_canary_b0_f1.py:1440-1477`);
- two Download topologies are allowlisted (`:60-64`), so an arrival need not even
  be this run's endpoint;
- `wait_download` returns on the first single endpoint with no departure proof
  and no minimum absence (`:1490-1511`).

A bootloader fallback, a watchdog or PMIC reset, an operator entry or a bare
reconnect all produce the same enumeration. The verdict would have been a false
`PROVED`, which is worse than the three `NO_PROOF` results already held.

The technique was imported from the S22+ lane without testing its causality
here, one day after this lane wrote down that S22+ observations are a hypothesis
source and not S20+ evidence.

## Channel 3: the `/dev/kmsg` banner (refuted at review, never fired)

The candidate's PID1 writes a fixed string to `/dev/kmsg` before requesting
download, and the sec_log window at `/proc/last_kmsg` was to be read for it after
the authorized rollback. The argument was that only that candidate's PID1 writes
that string, so it is self-authenticating.

Refuted on three counts. This device carries resident Magisk root, so anything
on it can write the same string. A ring buffer can retain a banner from an
earlier boot, and "exactly one occurrence" does not say which boot. And the
pattern carried no end anchor, so trailing text still matched - the same flaw
made `Power down soon` count as a terminal shutdown record.

## The pattern, which is the actual finding

Three channels, refuted for one reason each time: the token was **characteristic**
of the thing being proved, not **authenticated** as coming from it.

| Channel | What it actually proved |
|---|---|
| ACM banner | the whole gadget chain bound and something wrote a banner |
| Download arrival | the device is in Download mode |
| kmsg banner | that string is in the buffer |

None of the three excluded the other producers. A token only proves what
produced it if nothing else can produce it, and on a rooted device a fixed
string does not qualify.

The obvious next reach is a value unique to the run - generated on the host at
prepare time, baked into the candidate, kept only in the private run journal -
and it was available from the start and was not used. But review was right to
push back on how much it buys, and the correction matters more than the
omission. A per-run value establishes **freshness**, not origin. It excludes a
record retained from an earlier boot and it excludes a replay, which is real and
is exactly what the three refuted channels lacked. It does not exclude the
resident root on this device: once the value exists on the host it can be
written by anything running as root in that boot, and the ring retains it
identically. No in-band token closes that on a rooted device. So the remaining
producer has to be excluded operationally - by what is running during the window
- and any future proof has to say which producers its value excludes, which it
does not, and what condition covers the rest. Writing "unique per run" and
treating the question as closed would have been the same mistake one level up.

## What was actually established, and it is not nothing

All of this is host-only, from the retained artifacts and recorded evidence.

**The platform.** Qualcomm `kona` / QTI `SM8250`, Snapdragon 865, not Exynos.
The crippled classic fastboot - only `getvar` and `reboot-fastboot` - is Samsung
stripping a Qualcomm ABL, not an absent SoC feature.

**The retention channel is Samsung sec_log, not ramoops.** Every
`/sys/fs/pstore/*-ramoops-0` record read `unavailable` while the ramoops node is
enabled, bound and fully configured, so the S22+ `status=disabled` explanation
does not apply here. `CONFIG_SEC_LOG_BUF` with `CONFIG_SEC_LOG_BUF_NO_CONSOLE`
detaches the log from console drivers, leaving the pstore console buffer nothing
to persist. `/proc/last_kmsg` is a readable regular file of 2,097,136 bytes =
2 MiB - 16, matching the vendor `struct sec_log_buf` header of `magic`, `idx`,
`prev_idx` and `boot_cnt`. That arithmetic is confirmation against vendor source
for this SoC family, not inference from configuration alone.

**The UART route is compiled shut.** `CONFIG_SERIAL_MSM_GENI=y` and
`CONFIG_MUIC_SUPPORT_UART_SEL=y` - the same Max77705 MUIC the S22+ lane's live
hypothesis concerns - but `# CONFIG_SERIAL_MSM_GENI_CONSOLE is not set`,
`CONFIG_SEC_LOG_BUF_NO_CONSOLE=y` and an empty `CONFIG_CMDLINE`. A resistor jig
would mux the port to a UART with nothing printing on it.

**The S22+ watchdog wall does not transfer.** There, a native PID1 dwelling 90
seconds hit a PMIC reset because the watchdog driver had been blocklisted and
nothing petted an XBL-armed watchdog. Here `CONFIG_QCOM_WATCHDOG_V2=y` is built
in, registers at `pure_initcall`, defaults to enabled, and is petted by a kernel
thread needing no userspace, so a dwelling PID1 does not starve it. The three
consumed `NO_PROOF` results are therefore **not** explained by a ~30-second
watchdog bite, and their cause remains unexplained.

**The P0 F1 owner was already broken.** Its activation-document semantics pin
the AGENTS registry table verbatim; a docs commit trimmed the header and
reformatted the separator without updating this owner, and later row edits
drifted the cell. It failed closed at the activation gate, silently, because it
is dormant. Repaired, and a drift guard now enumerates the pins mechanically -
verified to fail on the header trim, the separator reformat and a row edit.

**The activation review gate did not match its suites.** It required 74 and 179
tests against real counts that the rebinding had moved. Activation would have
failed at that gate with the private records already written.

## Where the lane is now

The `/proc/last_kmsg` capability was reduced from asserting to measuring. It
counts five candidate prefix shapes plus `unclassified`, and derives nothing:
`retention_proved`, `boot_identified` and `content_interpreted` are all false,
and no verdict names a boot or interprets content. A Samsung sec_log
cpu/comm/pid field after the timestamp carries the finding, because it would
invalidate any anchor expecting the message immediately after it; `unclassified`
carries the rest, being the continuation and wrapped records an anchor would
miss along with any prefix this lane did not anticipate.

The shapes are a partition rather than an overlapping candidate set, and that
is an integrity requirement, not presentation. Independent review refuted the
first version of this capability on exactly that point: each shape is a separate
`grep` pass over the node, so a short read or a `grep` failure masked by the
fallback zero silently lowered one count with nothing to check it against, and
the "no record prefix" counter was not the complement of the others - an
unrecognized line beginning with `<` or `[` matched no shape and no complement
either. The class a wrong format guess lands in was the one class the
measurement could not see. Under a partition the counts must sum to the measured
line total, and the host refuses the transcript when they do not. Verified
against the target's own toybox `grep` under qemu across 7,475 generated lines:
no line counted twice, no line counted zero times, sum equal to the total.

That is the honest next step, because **no byte of this node has ever been read
on this target**. Every predicate written against it so far was anchored to an
inferred format.

Ordering, which changed twice and is now this:

1. clear the record-format D0's own review, then activate it; one read
   establishes the format. Its first review returned blocking findings and the
   capability stayed dormant - the measurement defects are described above;
2. design the proof predicate on the measured format, carrying a per-run value
   for freshness and stating explicitly what that value does not exclude;
3. rebuild the candidate with that value, re-review the F1, then one attended
   transaction.

Nothing is activated. The P0 F1 owner, the minimal candidate, the record-format
D0 and the shelved PMSG marker D1 are all dormant. The only active capability on
this target remains the pstore readiness D0.

## Evidence

Private H0 notes:
`workspace/private/work/s20plus-proc-self-class-audit-h0-20260905/AUDIT.md` and
`workspace/private/work/s20plus-v4-kmsg-groundwork-h0-20260905/NOTE.md`.
Design: `docs/plans/S20PLUS_G986N_LAST_KMSG_OBSERVATION_DESIGN_2026-09-05.md`.
PMSG closure: `docs/reports/S20PLUS_G986N_PMSG_WARM_REBOOT_D1_TRIAL_FAILURE_2026-09-05.md`.
No firmware, raw device logs or identifiers are included.
