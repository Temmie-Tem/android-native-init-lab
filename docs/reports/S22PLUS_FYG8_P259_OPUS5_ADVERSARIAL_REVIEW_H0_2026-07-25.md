# S22+ FYG8 P2.59 Opus 5 adversarial review reconciliation

Date: 2026-07-25 KST
Tier: H0
Status: `REVIEW_RECONCILED`
Device contacted: no
Build or image produced: no
Repository changes made by Claude: no

## Scope

Claude Opus 5 independently reviewed the committed P2.59 E3 ACM-banner
analysis and the exact execution-critical closure that it referenced. The
review reused persistent conversation
`da04d346-fe22-4754-b0a2-69d36bf1d207`, compacted that conversation in place,
and ran the substantive review at `xhigh` effort. It did not use
`--no-session-persistence`.

The review was deliberately limited to:

- the qualified P2.58A kernel/config/module and retained-contract evidence;
- generic configfs ACM and gadget-serial behavior;
- the FYG8 role-control path;
- Process v2 observation, verdict, persistence, and resume behavior; and
- the minimum design closure required before P2.60 implementation.

It did not authorize a build, device contact, candidate, or F1 action.

## External verdict

Claude returned:

```text
GO_WITH_MUST_FIX
```

It reported five MUST-FIX findings and six warnings. Independent Codex
reconciliation accepted four MUST-FIX findings, rejected one against stronger
exact-target evidence, accepted four implementation warnings, and narrowed
two warnings to avoid growing E3 into E4.

## Finding reconciliation

| External finding | Reconciliation | P2.60 consequence |
|---|---|---|
| Current verdict cannot express E3 `all_of` | `ACCEPT` | Add typed ACM acceptance to the PASS predicate and enumerate named diagnostic no-proof outcomes. |
| Driver owning `a600000.ssusb` is unresolved | `REJECT` | P2.58A already proved the exact `msm-dwc3/a600000.ssusb` driver-bind symlink; do not reopen driver selection. |
| Exact bytes lack gadget-side termios | `ACCEPT` | Set and verify raw termios on `ttyGS0` before writing. |
| Host observer lacks exclusivity/interference control | `ACCEPT` | Prevent ModemManager/other host opens before acquiring and exclusively owning the candidate TTY. |
| Resume destroys a durable E3 proof | `ACCEPT` | Flush a bound ACM receipt before `OBSERVED` and re-derive proof from it on resume. |
| E3 changes the kernel contract | `ACCEPT` | Require a new versioned descriptor, kernel, and reproducible Full-LTO A/B pair. |
| Seven stages are a hard cap | `ACCEPT IN PART` | Move terminal as needed and reserve one bounded post-bind diagnostic coordinate; do not add broad diagnostics. |
| Banner identity is inconsistent | `MODIFY` | Use one candidate/contract-bound banner and synthetic serial. Do not introduce an E4-style live nonce. |
| Open flags are unspecified | `ACCEPT` | Freeze `O_RDWR | O_NOCTTY | O_NONBLOCK` and keep the FD open through park. |
| Mode write needs idempotence and UDC recheck | `ACCEPT` | Read first, skip an already-peripheral write, then re-run exact UDC membership verification. |
| Semantic checks must exceed token presence | `ACCEPT AS TEST RULE` | Execute generated behavior and negative mutations; do not add a new policy layer. |

## Confirmed execution gaps

### 1. E2 PASS semantics would overclaim E3

The current finalizer declares PASS from:

```text
candidate_completed && marker_accepted
```

It does not consume host ACM evidence. The matching result validator also
requires only candidate completion, rollback/final health, and retained-marker
acceptance. Conversely, its generic no-proof branch rejects the combination
`candidate_completed && marker_accepted`.

Therefore simply adding an observer would be unsafe: retained E3 terminal
success with zero host bytes would still PASS, while attempting to demote that
combination to the existing no-proof verdict would fail result validation.
P2.60 must enumerate the verdict matrix rather than append one boolean.

The required success predicate is:

```text
candidate transfer
AND Download departure
AND exact candidate ACM endpoint
AND exact host bytes
AND retained E3 terminal
AND exact rollback
AND final health
```

Retained-only and ACM-only outcomes remain useful diagnostics, but neither is
E3 PASS.

### 2. The claimed SSUSB-driver ambiguity is false

The materialized P2.58A plan gates SSUSB on:

```text
/sys/bus/platform/drivers/msm-dwc3/a600000.ssusb
```

The public predecessor uses the same exact driver-bind path. The P2.57
contract maps that gate to stage `0x85`, index 9, and the accepted P2.58A
terminal record proves all prior gates passed. This is stronger than a generic
"some driver bound" observation: it proves the device appeared under
`msm-dwc3`.

The matching FYG8 vendor source also defines:

- `mode_show` and `mode_store`;
- `DEVICE_ATTR_RW(mode)`;
- inclusion of `mode` in `dwc3_msm_attrs`;
- compatible `qcom,dwc-usb3-msm`;
- driver name `msm-dwc3`; and
- `dev_groups = dwc3_msm_groups`.

The P2.60 primary role lever can therefore remain:

```text
/sys/devices/platform/soc/a600000.ssusb/mode
```

It still requires bounded existence/type checks, strict readback, no-op skip,
and post-operation UDC re-verification. It does not require another DT,
driver-match, or provider investigation.

### 3. Gadget-side raw mode is required

The exact matching source initializes gadget serial from `tty_std_termios`,
then changes only `c_cflag` and baud fields. The FYG8 `tty_std_termios` has:

```text
c_oflag = OPOST | ONLCR
c_lflag = ISIG | ICANON | ECHO | ...
```

`TTY_DRIVER_REAL_RAW` does not erase those initialized termios values.
Consequently an unconfigured gadget-side TTY can transform newline output and
echo host input. Full write count is not equivalent to exact wire bytes.

P2.60 must set raw termios on the owned `ttyGS0` FD before queueing the banner,
read it back where the ioctl contract allows, require the full exact write,
and keep that same FD open until terminal park.

### 4. Host interference is present, not hypothetical

On the review host, ModemManager is active and enabled, and the existing ACM
device is classified as a ModemManager candidate. A new candidate TTY can
therefore be opened or probed before the E3 observer wins a race.

P2.60 must define a bounded, restored host-interference control before the
candidate transfer and then acquire exclusive ownership of the exact new TTY.
The observer must also use a pre-transfer inventory, exact physical topology,
candidate-bound VID/PID/serial, a fixed read cap, exact byte equality, and a
no-extra-byte settle. Raw evidence remains private.

### 5. Resume must preserve proven ACM evidence

Current recovery normalization emits a resumed
`candidate_boot_ready {proof:false}` after an interrupted candidate
observation. For E2 this does not alter the retained-marker PASS predicate.
For E3 it would discard an exact ACM receipt that had already been flushed
before a later parser/report interruption.

P2.60 must:

1. write and fsync a manifest/candidate/observer-bound ACM receipt before the
   `OBSERVED` transition;
2. make that receipt immutable after acceptance;
3. validate and re-derive ACM acceptance from it on resume; and
4. never repeat candidate observation or transfer merely to recreate a
   timeline field.

## Narrow warning disposition

The versioned stage sequence is part of the in-kernel request validator.
Adding E3 coordinates therefore requires a new kernel and reproducible
Full-LTO A/B pair. This is not a userspace-only candidate.

`0x8f` is not a permanent terminal ceiling. P2.60 may move terminal and add one
post-bind diagnostic coordinate that distinguishes device-side bind/state
from host enumeration. It should not add a general USB trace framework.

The P2.59 wording alternated between profile-bound and run-bound identity.
P2.60 should instead use one candidate/contract-bound banner and synthetic USB
serial, with literals in private material and only non-sensitive hashes or
contract identifiers tracked. A host challenge/nonce remains E4.

## Minimal P2.60 design closure

P2.60 may proceed when its H0 design freezes:

1. one versioned E3 stage/detail descriptor and a moved terminal;
2. one bounded post-bind diagnostic coordinate;
3. raw gadget-side termios, exact open flags, one-FD lifetime, and one exact
   candidate-bound banner;
4. read-before-write role selection with no-op skip and exact UDC recheck;
5. a typed bounded ACM observer with pre-inventory, host-interference control,
   exact identity/topology, exclusive ownership, fixed cap, exact equality,
   and no-extra-byte settle;
6. a durable bound receipt and resume re-derivation;
7. an exhaustive `all_of`/diagnostic verdict matrix; and
8. one independent review of only the changed observer, manifest, receipt,
   resume, and verdict closure.

The existing 60-module provider plan, Odin transfer logic, rollback core,
final-health checks, and device boundaries remain unchanged.

## Final verdict

```text
GO_TO_P260_DESIGN_WITH_FOUR_MUST_FIX
```

The P2.59 direction is sound. The four accepted gaps are local to the E3
contract and Process v2 observation closure. The rejected driver-identity
finding must not trigger another provider or DT investigation. No additional
broad analysis, build, device action, or live approval is justified before
the bounded P2.60 design is complete.

## Review usage

The same persistent conversation was compacted and reused. The substantive
review ran on Claude Opus 5 at `xhigh` effort.

- usage before review: current session `3%`, weekly `54%`;
- usage after review: current session `24%`, weekly `56%`;
- context before: `967.8k` free (`96.8%`);
- context after: `867.9k` free (`86.8%`);
- Opus 5 direct output: `42.8k` tokens;
- Opus 5 direct cost shown by the CLI: `USD 3.70`;
- Opus 5 cache read: `2.7m` tokens;
- whole invocation totals including same-session compaction: API `14m 01s`,
  wall `18m 10s`, cost `USD 4.85`.

The initial `max` setting was reduced before the substantive review because it
expanded repository exploration without changing the decision quality.
`xhigh` is the retained default for this class of bounded adversarial review.
