# S20+ G986N N3-U0 attended F1 journal H0 implementation

Date: 2026-08-16

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `device=y2q` /
`product=y2qksx` / `G986NKSS8IYC2`)

Status: **H0 PASS_GO - NOT ACTIVE**

## Scope

This unit implements the dormant strict one-shot journal core selected by the
reviewed N3-U0 attended-owner H0 model. It does not connect the journal to ADB,
Download enumeration, Odin, the USB observer, Android health, or root commands.
The only CLI is `--render-plan`; `F1_ACTIVE` and `live_authority` are false and
the rendered device-command and partition-transfer lists are empty.

The binding S20+ target contract still defines no N3-U0 F1. This implementation
therefore creates no prepare, approval, reboot, candidate transfer, rollback,
or recovery authority.

## Frozen implementation candidate

| Input | Size | SHA-256 |
|---|---:|---|
| `workspace/public/src/scripts/revalidation/s20plus_n3u0_attended_f1.py` | 55,803 | `2c4d7335211ade6c25540782148f44c309da6373d8ad495a5904d43714a01e86` |
| `tests/test_s20plus_n3u0_attended_f1.py` | 20,038 | `c78bf7315bc02d23539942c6942a9acf015410c768bc8c9eb958b0b759bb5e30` |

The deterministic journal binding is
`4695acca5c8d618eee7e16aaf665cbf66235a5a76aadc0a4322f490113cc2945`.
The runner's normalized source SHA-256 is
`74e2d7fc4effdaf25ee24a6b753919ebdde00b75a219f5ed2a6dee980fccbe7e`
and is part of that binding.
It pins the reviewed inactive owner model source SHA-256
`db1b282e33218ea9f7a48b8b90b28b50a121dab3429b3f642ebf0e90ff940eca`
and model binding
`860d7970b0b841d1fccdaa27c59ec0d56060294f566c0d4844f484593f5fffbc`.
Through that model it pins the exact N3-U0 candidate, resident Magisk rollback,
witness/builder/observer, shared transport, and prior combined review.

## Journal publication and grammar

Every final journal name is published from an `O_TMPFILE` inode only after all
bytes and the inode are fsynced. `linkat(AT_EMPTY_PATH)` publishes it without
replacement and the containing directory is then fsynced. Existing final names
are never overwritten.

Reads use `O_NOFOLLOW`, require one direct regular link, mode `0400`, and a
one-MiB bound. JSON must be canonical UTF-8 with exact keys and types. Duplicate
keys, non-finite numbers, semantic-but-noncanonical encodings, bool/integer
substitution, symlinks, hardlinks, special nodes, unknown names, and conflicting
recovery branches fail closed.

The shared `active.json` allocation guard binds one random 128-bit run ID, the
current journal binding, and the complete prepared value. It is acquired before
`prepared.json` publication, so no prepared orphan can later regain authority.
Re-entry may accept only the byte-equivalent owning guard. A foreign guard is
never removed. If publication stops between those two writes, only that current
guard may reconstruct its exact prepared receipt; it cannot create a new run.
Terminal publication precedes guard release; terminal-present/guard-present and
terminal-present/guard-absent cuts both resume without another device effect.

## One-shot state graph

1. `prepared.json` binds the exact target, prepared serial/topology/boot ID,
   empty Download baseline, candidate and rollback budgets, and no-replay.
2. `initial-download-intent.json` precedes the only initial Download reboot.
   Missing or uncertain result never permits another reboot intent.
3. An exact `initial-download-observation.json` binds the Download endpoint and
   arrival listing. Only then can the deterministic fresh per-run approval be
   derived from the random run ID, prepared boot, binding, endpoint, and exact
   candidate AP.
4. `candidate-intent.json` consumes the only candidate boot transfer before any
   result. A result may be complete, device-session unknown, or local-parse
   failure; none permits replay.
5. Candidate banner/Android observation is never terminal and always records
   rollback required. An Android identity, when present, must retain exact
   serial/topology and use a boot ID distinct from the prepared boot.
6. Recovery chooses exactly one branch: an intented automatic rollback-mode
   reboot from the exact returned Android identity, or an intented attended
   physical rollback entry bound to an empty baseline and one exact arrival.
7. `rollback-intent.json` consumes the only resident Magisk boot transfer and
   must reuse the selected branch's exact endpoint. Missing, partial, uncertain,
   or locally unparseable rollback evidence never permits Odin replay.
8. `final-health.json` is allowed only after completed rollback classification.
   It binds a fresh exact serial/topology identity, a boot ID not reused from
   prepared/candidate durable observations, an exact Android-health receipt,
   and an exact positive resident-root receipt.
9. `terminal-result.json` reports only resident restoration; candidate evidence
   cannot become terminal. The shared guard is released last.

## Hostile coverage

The focused suite passes **23/23**. It covers both complete automatic and
physical rollback graphs plus these cuts and attacks:

- prepared/guard resume and atomic no-clobber publication;
- the allocation-guard-written/prepared-missing cut without creating a second
  run, and stale prepared-orphan rejection after a newer terminal run;
- missing guard rejection at initial, candidate, both recovery, rollback, and
  final-health boundaries, plus foreign-guard rejection;
- normalized runner-source binding and source-drift rejection;
- initial Download, candidate, physical recovery, and rollback intent replay;
- candidate intent with no result reaching only recovery;
- stale approval and endpoint substitution;
- automatic/physical branch conflict;
- uncertain rollback retaining the guard and blocking terminal;
- reused/foreign final boot identity and forged root-attempt type;
- duplicate/non-finite JSON and bool/integer substitution;
- unknown, symlink, and hardlink journal nodes;
- missing predecessor and foreign guard rejection; and
- terminal/guard reporting-cut resume without another effect.

## Remaining gates

This is a journal core, not a live F1 runner. Before activation consideration,
a later unit must:

1. bind the exact current Android/Download/Odin/USB/root helper closure;
2. connect each journal intent to one fixed reviewed device effect and publish
   bounded raw receipts/classification from the actual consumer;
3. implement bounded N3-U0 observation and exact automated/physical rollback
   continuation for every reporting cut;
4. add end-to-end fake-device hostile fixtures proving command counts and
   intent-before-effect ordering at each cut;
5. obtain independent review of this journal candidate and the later integrated
   executable closure;
6. amend the binding S20+ target contract; and
7. perform a separately reviewed mechanical activation and fresh connected
   prepare/approval only after all earlier gates pass.

No device, USB endpoint, ADB, `su`, Odin, network, private run, reboot, or
partition transfer was contacted by this H0 unit.

## Independent review disposition

The first independent review returned `NO_GO`. It demonstrated that state
writers could publish effect intents with a missing or foreign shared guard,
because the generic prefix validator deliberately skipped guard validation.
It also found that the journal binding pinned the owner model but omitted this
execution-critical runner's own bytes.

The second review confirmed those fixes but returned `NO_GO` for a new stale
prepared-orphan path: because prepared publication preceded guard creation, an
old orphan could be reactivated after a newer run completed.

The third review found that the generic first-allocation guard publisher could
still be called with an old prepared value after its guard was lost. The
publisher did not distinguish a new empty allocation directory from an older
prepared run.

The latest rotated candidate now requires the exact owning guard in every
pre-terminal state mutation. Only terminal/guard reporting-cut resume may use
the explicit no-guard validation scope. Allocation guard publication now
precedes prepared publication and embeds the complete prepared value. The
first-allocation publisher accepts only a direct empty run directory and never
accepts an already published prepared node; matching existing guards use the
separate read-only validator. Its only recovery function reconstructs that
same prepared receipt while the exact owning guard remains current. A
guardless stale prepared run therefore cannot reacquire ownership through
either publisher. The binding includes a normalized self receipt, so any other
source-byte change expires it. Hostile fixtures exercise the reported
missing/foreign-guard, stale-generation, generic-publisher, and source-drift
cases. Fresh independent review returned `PASS_GO` on the immediately prior
frozen candidate. This table is the mechanical status/identity rotation that
records that verdict. Narrow post-rotation review independently reproduced the
prior bytes by reversing only the status/identity assertion and returned
`PASS_GO`. The verdict qualifies only this dormant public H0 journal core and
creates no live authority or connected execution surface.
