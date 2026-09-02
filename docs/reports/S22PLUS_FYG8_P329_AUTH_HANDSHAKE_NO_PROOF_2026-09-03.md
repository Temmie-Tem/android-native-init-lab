# S22+ FYG8 P3.29 authenticated handshake no-proof

Date: 2026-09-03 KST

Target: `SM-S906N / g0q / S906NKSS7FYG8`

Tier: attended F1

Formal verdict: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`

Outcome: `p329_authenticated_framed_exec_unproved_rollback_verified`

## Outcome

P3.29 is closed and consumed. The exact boot-only candidate and exact Magisk
rollback each transferred once, the journal closed at 19 records, and final
rooted FYG8 health passed with `recovery_required=false`. There was no attempt
2 and P3.29 must never be replayed.

P3.29 repaired the P3.28 udev-readiness failure. The exact candidate appeared
as one `04e8:6861` CDC-ACM tty on `usb:3-1.3`; the Type-C partner remained
continuous, and both `ID_MM_DEVICE_IGNORE=1` and `ID_MM_PORT_IGNORE=1` were
present on the exact tty node. The raw-first observer then received the exact
49-byte P3.29 native PID1 banner.

The authenticated session did not advance to a CHALLENGE. No HMAC, BusyBox
command, framed close, host-to-device byte, interactive shell, resident
service, or Max77705 causal result is proved.

## Exact transfers and final state

- candidate AP: 28,631,081 bytes, SHA-256
  `7a83b7c32e52f13fb88ec3cc6d81671baf70f13c343f2e02b03a6d712ab494bf`;
- exact Magisk rollback AP: 23,367,721 bytes, SHA-256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`;
- candidate transfer result: 2,079 bytes, SHA-256
  `6616c363c184e08c08f1daf471020cf6c207d140aee862431689881caa384fdc`;
- rollback transfer result: 2,030 bytes, SHA-256
  `8f35f50a267f0fbdb9161753f441a62694a69f3f5afb3705f7b8e2dd689febcf`;
- final live state: 31,298 bytes, SHA-256
  `79a29d735e3a2438a43af063a19fa8773ceaeb47e625e5ceae0f3b2a018d3960`;
- final live result: 34,978 bytes, SHA-256
  `73a11e9b6a3f673ef405c0f7fb4430750f48244168f8f304a0efedaeeb3fee79`.

Final health proves boot completion, stopped boot animation, root, exact boot
and supporting-partition identities, and absent Download mode.

## Candidate observation

The retained candidate-side evidence is:

- raw banner: 49 bytes, SHA-256
  `0bd73a11de46dba960949ea4699cc5069d172b7eb800db02ba50e8894070ee17`;
- candidate observer JSON: 6,020 bytes, SHA-256
  `a3f126d5fe0c47575cee9c755298414746345eda39fe05d53dd0220be3a3d251`;
- lane receipt: 3,141 bytes, SHA-256
  `e31528894ac7f6056a86cfc66f74852855ba50ce8558f6939066681e953c4097`;
- first and second exact tty-property reads: 1,475 bytes each, both containing
  the two required ignore flags.

The host kernel saw the candidate USB device at 02:05:39.684 KST and bound
`ttyACM0` immediately. The first guard property receipt landed at 02:05:39.720,
the second at 02:05:39.744, and the raw banner at 02:05:39.764. This establishes
that the bounded settle crossed the P3.28 race and reached the exact tty.

The candidate observer finalized at 02:07:39.790 with
`classification=open-failed`; its raw-capture receipt measures 120,066 ms for
the exchange after endpoint selection. That duration matches the host
authenticated-exchange timeout after the banner read. The host wrapper stored
only the exception type in an in-memory `protocol_error`; it did not serialize
that field or the partial exchange audit. Consequently the raw file contains
the banner while the JSON `rx` projection is empty. Strict durable reopen
rejects this as `P328 rx/trailing accounting differs`, and the final result
reports `interrupted-before-receipt`.

## What remains unknown

The retained evidence cannot distinguish these two sides of the next boundary:

1. the host did not complete writing the 32-byte OPEN frame; or
2. the device accepted or rejected OPEN but produced no CHALLENGE.

The second is the leading source-level hypothesis, not a proved fact. After a
valid OPEN the device runtime calls 32-byte `getrandom` with `GRND_NONBLOCK`.
An early-boot `EAGAIN`, a frame rejection, or a challenge-write error returns
silently while PID1 keeps the tty open, which would leave the host waiting for
exactly the observed timeout. No durable host-TX or device pre-auth stage code
was retained, so P3.29 cannot choose among those cases.

## Proportional successor

A successor should stay at the OPEN/CHALLENGE boundary:

- durably retain partial host RX/TX progress and the exact exception class on
  every exchange exit, including `stage=challenge-read` for a timeout;
- keep the proven P3.29 udev settle, exact tty selection, rollback, and health
  sequence unchanged;
- do not add a broad selector, retry loop, interactive command surface, or new
  protocol feature.

The smallest device-side hypothesis test is a finite retry of `getrandom` only
when it returns `EAGAIN`, covered by an injected `EAGAIN`-then-success host
test. A returned CHALLENGE would support the early-entropy hypothesis; another
silence would move the fault back to OPEN transfer/frame validation. H0 tests
alone must not retroactively label P3.29 or authorize another device action.
