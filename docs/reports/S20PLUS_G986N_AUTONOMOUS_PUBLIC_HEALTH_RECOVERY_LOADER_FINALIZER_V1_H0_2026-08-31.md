# S20+ autonomous public-health recovery loader/finalizer v1 H0 qualification

Date: 2026-08-31

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2`)

Status: **PASS_GO_NOT_ACTIVE — exact inactive H0 loader/finalizer subset only**

## Objective and scope

Close the next host-only recovery prerequisite without changing the qualified
recovery-v1 store/scanner bytes. This unit adds one versioned public loader and
one self-contained private-core candidate that can deterministically finish an
already consumed ordinal-1 public-health journal using retained bytes only.

It does not install a private bundle, create an attended opening, bind a future
runner, accept the future `opening-v1` or `campaign-binding.json` namespace,
execute a command, contact a device, or activate recovery authority.

The exact sources and focused tests are:

- `workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_recovery_loader_v1_h0.py`;
- `workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_recovery_v1_finalizer_h0.py`;
- `tests/test_s20plus_g986n_autonomous_public_health_recovery_loader_v1_h0.py`;
- `tests/test_s20plus_g986n_autonomous_public_health_recovery_v1_finalizer_h0.py`.

The predecessor
`workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_recovery_v1.py`
remains exactly 133,053 bytes at SHA-256
`6186221593b3778475bf3b1ac4bd28bfe013534793eca4ce5fbe0007be8eb0c3`.

## Exact reviewed identities

After the reviewed status-only rotation, the closure is:

- loader: 35,315 bytes, SHA-256
  `a210944447dc33b7593b42ba5c46cde9561c9449e8981523b468a4121c4284cc`,
  activation-normalized SHA-256
  `8df4dc534a1d4e9ac1a73867151e4bfcf2450a52283a281c7091d9c47e1e09cc`;
- finalizer/private-core candidate: 162,875 bytes, SHA-256
  `94f6022aebcdc63bcad08757f493349d2e4b198610a367e72181a65694321f0b`,
  activation-normalized SHA-256
  `38cb154e526e8a1a3ad38f8c857f03668f92fedced786745f5e8e85d91e21dac`;
- derived unbound manifest: 7,669 bytes, SHA-256
  `51931dd9a084e1c7ae8d674681d34be7bd2f50b32d8c0b84b2842d51749df593`;
- loader test: 17,766 bytes, SHA-256
  `f766ab0a52ebc222f5b2d4c14378d61cb04c8a7546bbff0b8572e1ea24579050`;
- finalizer test: 31,556 bytes, SHA-256
  `7fa998f513d5b76fbf545e1724f3d24ce40f3622d9df2fc86644d436605350a4`.

Focused validation passed 47/47: 21 loader and 26 finalizer tests. The
canonical eight-suite S20+ autonomous H0 aggregate passed 263/263.
`py_compile`, both render plans, canonical JSON parsing, and scoped
`git diff --check` passed.

Independent post-rotation review returned `PASS_GO` with HIGH/MEDIUM/LOW
`0/0/0`. It reverse-substituted the two status strings, dependent loader pins,
and test literals to reproduce the previously reviewed candidate bytes exactly.
A separate hostile finalizer-cut review also returned `PASS_GO` with
HIGH/MEDIUM/LOW `0/0/0` for the unchanged logic.

## Trust and identity chain

The intended future trust chain is finite:

```text
binding target contract
  -> exact versioned public loader
  -> exact private manifest and full private-core hash
  -> allowed finalizer normalized identity
  -> bound future-runner normalized identity
  -> retained three-root journal
```

The loader opens only the three fixed private roots and the fixed
`recovery-v1/{recovery-core.py,manifest.json}` names. Direct core paths,
caller roots, IDs, versions, commands, times, callbacks, and backends are not
inputs. It requires current owner/group, mode `0700` directories, mode `0400`
single-link regular bundle files, an exact mode `0600` zero-byte coordinator
lock, and held no-follow directory handles. Core and manifest full identities
must match the loader constants before already verified core bytes are parsed,
compiled, and given a fresh process-local object capability.

The loader reopens all fixed roots and the recovery directory after a
successful operation. Its own source read is bounded at 64 KiB before identity
normalization. Full hashes reject a self-consistent rogue core/manifest pair
and status/boolean-only core mutations even where the reviewed normalized
identity intentionally remains stable.

The loader normalized identity masks only the status, operational gates, and
exact core/manifest identity literals that must rotate together later. This
breaks a future loader/core hash cycle. The activation order remains:

1. retain the qualified finalizer normalized identity;
2. retain the qualified loader normalized identity;
3. bind that loader identity into the private core's single future-runner
   binding literal;
4. derive the bound core full identity and manifest full identity;
5. rotate the loader's exact full-identity pins; and
6. independently review every activation atom before use.

No such binding or rotation exists in this unit.

## Self-contained finalizer

The finalizer embeds the exact target, schemas, parsers, lineage validators,
six-command transcript, evidence grammar, caps, and no-replace publisher. It
does not reopen the public coordinator, observer, evidence-owner, inventory,
or predecessor recovery source at runtime. Direct import or pathname execution
receives no loader capability and cannot reach an operational entrypoint.

The complete lineage is revalidated on every invocation:

```text
guard -> campaign opening -> session opening -> accounting opening
      -> ordinal-1 lease -> exact mirror -> retained command receipts
      -> derived health -> deterministic result -> parked completion
```

Strict canonical JSON rejects duplicate keys, nonfinite values, bool/integer
substitution, extra fields, malformed hashes, counter drift, target/source
drift, and predecessor mismatches. The eight structural nodes are checked both
against per-node limits and the actual 48-KiB aggregate. The 19-file evidence
proof remains bounded at 507,904 bytes inside its 512-KiB reservation.

The finalizer may publish at most one missing node per invocation:

1. with an exact lease and no descendants, publish only the exact mirror using
   `lease.issued_at`, then park;
2. with the exact 18 raw/receipt files, publish only derived `health.json`;
3. with all exact 19 evidence files, publish only the deterministic result;
4. with that result, publish only the permanently parked completion; or
5. with a complete fully revalidated chain, emit a sanitized terminal envelope
   without changing the filesystem.

Raw evidence without the mirror is rejected. An incomplete return prefix is
`uncertain-consumed` and receives no write, replay, refund, or next action.
The result uses command 6's `receipt_published_at` only as a deterministic
logical completion lower bound. `reporting_cut_at` remains `null` and
`reporting_after_expiry_or_drift` remains false because no retained byte proves
the later reporting-cut time, clock provenance, expiry, or source drift.

Each final publication uses the inherited held-dirfd `O_TMPFILE`, complete
bounded write, file `fsync`, `linkat(AT_EMPTY_PATH)` no-replace, directory
`fsync`, reopened inode/metadata, and exact reopened-byte checks. Exact existing
bytes converge idempotently; different bytes, symlinks, hardlinks, FIFOs,
special nodes, partial writes, fsync faults, and `EEXIST` mismatches stop.
After publication the full roots and ancestry are rescanned and must show the
single expected successor state.

## Terminal re-emission and privacy

Re-emission requires the exact completion and its complete ancestry. It emits
one canonical sanitized JSON envelope containing public target identity,
hashed campaign/session IDs, completion/result hashes, parked flags, and zero
device-command/effect counts. It emits no raw serial, topology, boot ID,
campaign ID, or session ID and creates no receipt file. Repeated output-loss
re-emission is byte-identical and performs zero filesystem writes.

## Storage closure

The private bundle shape remains unchanged:

```text
recovery-v1/
  recovery-core.py   <= 256 KiB
  manifest.json      <= 32 KiB
```

Its aggregate remains at most 288 KiB and two files. The future completed
campaign reservation remains 52 regular files and 1,441,792 bytes. These are
future closure reservations, not a claim that the current scanner accepts or
materializes `opening-v1` or `campaign-binding.json`. No private file was
created by this unit.

## Dormant boundary and remaining gates

The public CLI of both sources remains only `--render-plan`.
`SELF_CONTAINED_FINALIZER_IMPLEMENTED=true` is descriptive, not authority.
Every loader operational-qualification/identity/operation/future-binding/contract/
mechanical/live gate and every core qualification/scanner/bundle-writer/
finalizer-writer/finalizer/re-emission/manifest/contract/live gate remains
false. The embedded runner binding is exactly `UNBOUND_PLACEHOLDER` with the
zero hash.

Before any operational use, a later unit must implement and review the
attended opening and fixed six-command producer, rotate the scanner grammar for
the exact opening/campaign-binding namespace, construct and install the bound
private bundle before the opening, bind the immutable loader in the target
contract, and perform a combined independent activation review. Only a new
post-activation exact-target/current-boot attended opening may start the finite
read. Pre-activation consent is not bankable.

## Work performed

This unit adds two host-only sources, two hostile test suites, and this report.
It runs no ADB, USB, `su`, root, device network, reboot, Download, Odin,
payload, partition, R1, F1, campaign, private-bundle installation, or live
evidence action. The promotion is only `PASS_GO_NOT_ACTIVE` for the exact
loader/finalizer H0 subset. Whole recovery-v1 and autonomous live authority
remain false.
