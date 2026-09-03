# S22+ FYG8 P3.34 first-read return-code design

Date: 2026-09-04 KST

Target: `SM-S906N / g0q / S906NKSS7FYG8`

Tier: H0, host only

Status: runtime transform implemented, packaging and independent review pending

## Combined P3.26-P3.33 evidence

| Campaign | Last proved boundary | Result relevant to the first OPEN |
|---|---|---|
| P3.26 | fixed bidirectional ACM plus BusyBox | host-to-device and device-to-host transport proved |
| P3.27 | framed three-command exchange | framing, execution and clean close proved |
| P3.28 | exact CDC-ACM endpoint only | pre-open udev-property race; zero RX/TX |
| P3.29 | exact banner | udev race repaired; host OPEN progress was not retained |
| P3.30 | authenticated commands | OPEN_PARSED, RNG, challenge, HMAC and three commands all passed |
| P3.31 | banner plus 32-byte host OPEN | first session stopped before OPEN_PARSED |
| P3.32 | same result with physical reconnect removed | reconnect was not the sole necessary cause |
| P3.33 | banner plus CRC-valid stage-0/code-0 | device reached the console call; first read/OPEN result remained unknown |

P3.33 therefore proves that the publisher called `p328_framed_console()` and
that its immediately preceding diagnostic reached the host. The exact host
OPEN write completed, but host completion does not prove receipt or parsing by
the device. The remaining boundary is the first `p328_read_frame()` plus the
immediate OPEN type, sequence, length and run-ID validation.

## Code-generation correction

The earlier P3.33 design text described both P3.31 and P3.32 as compiling the
console out of line. Final binary inspection corrects that statement:

- P3.30 contains `p318_run` and no independent `p328_framed_console` symbol;
- P3.31 likewise contains no independent console symbol; its resident loop and
  console were inlined into the final `p318_run`;
- P3.32 and P3.33 contain independent console symbols of `0x894` and `0x858`
  bytes respectively.

Thus out-of-line compilation alone cannot explain all three failures. The
common transition is the two-session publisher shape introduced after P3.30;
the exact device-side return remains the missing discriminator. This correction
does not change any consumed-run result or weaken the P3.33 stage-0 proof.

## P3.34 design

P3.34 retains the exact P3.33 console body, wire grammar, HMAC domains, three
commands, timeouts, two-session limit, same tty descriptor and zero reconnects.
It changes only two outer publisher anchors:

1. mark that the first console call was reached and retain its returned `long`;
2. after the existing stock envelope is encoded, replace only the checkpoint
   terminal `detail` with a bounded return-code receipt.

The receipt grammar is:

- `0xB000 | errno` for a called console returning `0` or `-1..-4094`;
- `0xBFFF` when the console was not called or the return is outside that domain.

Examples are `0xB000` for success, `0xB005` for `-EIO`, `0xB047` for
`-EPROTO`, and `0xB06E` for `-ETIMEDOUT`. The encoding is reversible and does
not add another checkpoint generation, tty response, retry, timeout, command,
protocol field or persistent write. Because it is written after the console
returns and recovered through the existing post-rollback raw capture, it does
not depend on the host keeping the candidate tty open.

The receipt is formally the first console call's return, not an unconditional
first-read receipt. It is attributed to the first read/OPEN boundary only when
the same run again proves stage `0` and retains no later diagnostic. If the
exchange advances, the existing host stage trace remains the locator.

## Interpretation

- `-ETIMEDOUT` supports no readable OPEN bytes before the device deadline;
- `-EIO` supports EOF/zero-progress behavior;
- `-EPROTO` places the failure in frame or immediate OPEN validation;
- `0` would show the device completed the first session despite the host-side
  observation failure;
- the sentinel keeps pre-console failures separate.

The exact errno may still require one later sub-classification if it is
`-EPROTO`, but P3.34 avoids changing the sensitive console body before that is
known.

## Current implementation boundary

`s22plus_fyg8_p334_first_read_rc_runtime.py` exact-loads the frozen P3.33
runtime source, applies only the two named outer anchors, and exposes a strict
host encoder/decoder. Four focused tests prove exact transform/restore,
reversible representative errno values, unchanged protocol constants and
hostile mutation rejection. The actual P3.33 474,779-byte runtime include
transforms to 475,102 bytes and validates under the fresh P3.34 run identity
`c334f1e0a90b5e6d7c8a9b0c1d2e3f6b`.

An exact-toolchain cross-compile of that transformed source produces a static
AArch64 ELF with no undefined symbols. Its `p328_framed_console` remains at
address `0x408250`, size `0x858`, and its complete `objdump` disassembly is
byte-for-byte identical to P3.33; only the outer `p318_run` grows.

No AP, ready manifest, D0 preparation, approval, F1 action or device contact
exists. Packaging must carry the compiled-console equality into its retained
result, then the complete changed closure requires independent review before
any live preparation.
