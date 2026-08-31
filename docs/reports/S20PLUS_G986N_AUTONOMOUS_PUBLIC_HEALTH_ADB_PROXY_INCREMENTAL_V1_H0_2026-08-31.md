# S20+ G986N autonomous public-health ADB proxy incremental v1 H0

Date: 2026-08-31

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2`)

Status: **H0 MODEL PASS_GO_NOT_ACTIVE; NO SOCKET OR WIRE AUTHORITY**

## Outcome

The restricted-proxy post-run audit now has a separate fragmentation-safe pure
transcript model. It accepts only one exact immutable tuple of exact typed
downstream, upstream, EOF, and timeout fragments for one internally fixed
command ordinal. A caller can select that model transcript. Acceptance proves
only that the supplied bytes satisfy the deterministic model; it does not
authenticate a real socket, peer, ADB child, ADB server, target, or wire
observation.

The final design has no caller sink, callback, backend, service selector,
mutable ledger, reusable session, or import-visible reducer/emitter API. It
uses two passes:

1. validate the entire transcript using only scalar counters and immutable
   byte buffers, constructing no relay emission; and
2. only after complete acceptance, deterministically replay the already-valid
   transcript to derive a fresh frozen tuple of relay emissions and a frozen
   terminal result.

Therefore an incomplete or rejected prefix returns no result and exposes no
partial upstream relay object. A modeled upstream request is derived only
after its complete framed service is byte-identical to the ordinal closure.

This remains a pure H0 data model. It opens no socket or port, creates no
process, invokes no ADB, contacts no device, and performs no private write.
All 23 operational, proxy, seccomp, executor, journal, recovery, coordination,
contract, mechanical-activation, and live-authority gates remain false.

## Closed transcript

Ordinal 1 accepts only the empty transcript. Ordinals 2 through 6 contain two
connections in order:

- one local `host:version` request answered only by exact
  `OKAY00040029`, with zero upstream forwarding; then
- exactly one of:
  - ordinal 2 or 6: `host:devices-l`;
  - ordinal 3: `host-serial:<bound-serial>:get-devpath`; or
  - ordinal 4 or 5: `host:tport:serial:<bound-serial>`, exact `OKAY`, one
    nonzero little-endian 64-bit transport ID, then the exact fixed exec
    service and bounded output through EOF.

Request framing is four lowercase hexadecimal length bytes plus the exact
service. Every prefix is retained internally until equality with the complete
expected frame; a differing, overlong, pipelined, reordered, extra, or
reconnected frame fails before any modeled upstream emission. Query protocol
strings, status, transport IDs, output, fragment counts, byte caps, EOF, and
timeouts are bounded and ordered.

The fixed 1,472-byte Phase-A public snapshot has SHA-256
`a571dc5009eb57952a6230e3ecca8ad342627eb1bf9df38060886ee6382cd17a`.
Its exact ADB-constructed 1,523-byte exec service has SHA-256
`c3db3a45d41b3684316c2344c8dad45b23f61b40f03e3d43f6e00d565b9f781e`.

## Exact identities and validation

The qualified source is
`workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_adb_proxy_incremental_v1_h0.py`,
33,817 bytes at SHA-256
`f956bc65a5e7abedd2f57ab8fa723275be1e7d6fb2b4ae86295de947c42f3f05`.
Its normalized SHA-256 is
`ec1dcd8236f6778bdf6994b5d1a9a26132e95d92d9ce8955cfba08122c95a2cc`.
The 28,068-byte focused hostile test has SHA-256
`6786cda31d30813e6243ac8189a9f0802b455aa478656456a489f743e2c31cce`.

The model exact-pins the committed restricted-proxy audit at commit
`d561226f108869614128db9e46ea050c4a94b58c`, 46,477 bytes, SHA-256
`18993008de3c236211c11de2756dc9b05424d9704cfdcb9c02f3cf70e9e29d92`,
normalized SHA-256
`8878c5e39f2d34ea90707bf81697aed119db1fdf3141807b56c81480fbe1c8c9`.

`py_compile`, render validation, scoped diff checking, 33/33 focused tests,
and the 40/40 committed proxy-audit suite pass, for 73/73 combined tests. The
fragment corpus checks all 3,188 two-way splits of every allowed request frame
and proves that no modeled upstream frame exists before complete equality.

## Hostile review corrections

The first implementation received `NO_GO` because it accepted a caller-owned
mutable relay sink without proving that the sink was virgin and exclusive. A
prior `host:kill` emission could survive into an accepted ordinal-1 result.

The first correction also received `NO_GO`: caller-visible duplicate mutable
ledgers and an owner token could be changed together, allowing mirrored
injection, deletion, reset, sequential reuse, or interleaved reuse while the
two compromised ledgers still agreed.

The initial functional rewrite received a third `NO_GO` because an
import-visible stateful reducer still accepted arbitrary services and stored a
mutable emission list. A rejecting exception traceback could expose that
reducer and partial emissions despite the no-partial-result claim.

The final two-pass model removes every sink, owner, session, mutable emission
accumulator, and arbitrary service reducer. The only rejecting pass constructs
no `RelayEmission`; the success-only second pass returns immutable tuples.
Tests inspect failure traceback locals, module surfaces, old mutation/reset/
reuse shapes, and deterministic repeated/concurrent function calls.

Exact-byte independent review of the final two-pass source returned `PASS_GO`
with HIGH/MEDIUM/LOW `0/0/0`. A status-only rotation changed
`MODEL_REVIEW_PENDING_NOT_ACTIVE` to `MODEL_PASS_GO_NOT_ACTIVE`; it changed no
normalized source byte or operational gate.

## Claim and activation boundary

This qualification proves only the behavior of a caller-selected pure
transcript. It does not implement or prove:

- an AF_UNIX listener, peer credentials, or lifecycle;
- an authenticated incremental observation of real socket bytes;
- upstream ADB-server ownership, accepted-peer attribution, or relay writes;
- seccomp installation, the ADB child, exact executor-owned argv/environment,
  or process-death handling;
- durable evidence, intent/result ordering, reporting cuts, or recovery;
- same-process runtime/campaign handoff and the seven-runner cross-code
  new-start interlock; or
- target-contract activation, a campaign opening, or device authority.

A production proxy must reimplement the reviewed parser as a closed internal
wire owner and produce durable causal evidence; it cannot treat a
caller-selected transcript as wire proof. `MODEL_PASS_GO_NOT_ACTIVE` grants no
ADB command, no standing consent, and no S20+ contact.
