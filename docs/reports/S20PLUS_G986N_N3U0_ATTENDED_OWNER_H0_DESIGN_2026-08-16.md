# S20+ G986N N3-U0 attended owner H0 design

Date: 2026-08-16

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `device=y2q` /
`product=y2qksx` / `G986NKSS8IYC2`)

Status: **PASS_GO - H0 DESIGN ONLY - NOT ACTIVE**

## Scope

This unit defines the binding model for a future attended boot-only N3-U0
owner. It validates the exact reviewed candidate, exact known-good resident
Magisk rollback, dormant USB observer, witness/builder, prior combined review,
and shared transport source. It exposes only `--render-plan`.

It does not implement prepare, approval issuance, ADB, Download entry, Odin,
USB observation, rollback, final health, or a durable run journal. No device,
USB endpoint, network, reboot, or partition transfer was contacted.

## Frozen public H0 model

| Input | Size | SHA-256 |
|---|---:|---|
| `workspace/public/src/scripts/revalidation/s20plus_n3u0_attended_owner_h0.py` | 14,125 | `db1b282e33218ea9f7a48b8b90b28b50a121dab3429b3f642ebf0e90ff940eca` |
| `tests/test_s20plus_n3u0_attended_owner_h0.py` | 14,281 | `a590b2bee99e0aa10fc74d6fb730118a0d3b2a4cb4fdcf4970447c4b1fa432f1` |

The deterministic model binding SHA-256 is
`860d7970b0b841d1fccdaa27c59ec0d56060294f566c0d4844f484593f5fffbc`.
`OWNER_ACTIVE` is false, `live_authority` is false, and the reserved approval
prefix is reported but no token is generated.

## Exact candidate and rollback

| Role | AP size | AP SHA-256 | boot SHA-256 |
|---|---:|---|---|
| temporary N3-U0 candidate | 26,112,041 | `3aad497979cfa0f247aef68f50ea792f40127afa037c134eeb0d2e96798ca7af` | `7024d206453dbd82f04187b7a3ccb6042aef7e2e20ed9660a67b47ecf19206eb` |
| known-good resident Magisk rollback | 25,835,561 | `1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2` | `d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc` |

Each AP is a TAR+MD5 archive with exactly one canonical regular
`boot.img.lz4` member. The H0 owner rejects symlinks, hardlinks, size/hash
drift, invalid MD5 trailers, extra members, and noncanonical member metadata.
The rollback is the boot already underlying the healthy resident Magisk state,
not stock root-absent boot. Therefore terminal health requires resident Magisk
root again after rollback.

## Selected future state machine

The future executable owner must implement this exact order:

1. start from fresh exact healthy rooted Android, bind its current boot ID in
   the approval, and acquire one shared S20+ guard;
2. bind an empty Download baseline and durably record intent before one Android
   to Download reboot;
3. bind the sole exact Download arrival and only then emit a fresh approval;
4. durably record candidate intent before one boot-only candidate transfer;
5. treat that attempt as consumed regardless of a missing or uncertain result;
6. observe the same prepared physical topology for the bounded exact N3-U0
   product/banner, then record the distinct candidate Android boot ID when an
   Android return is available;
7. regardless of banner acceptance, enter the mandatory resident rollback
   lane through at most one intented Android rollback-mode reboot or one
   separately intented attended physical Download handoff;
8. durably record rollback intent before one resident-boot transfer; and
9. publish terminal only after completed rollback transfer and a fresh exact
   target Android observation whose boot ID differs from the prepared boot and
   every durable candidate/rollback-mode observation, plus resident Magisk root
   proof; then release the guard.

The banner is candidate evidence, never terminal success. Missing, malformed,
or consumed-by-another-reader banner evidence means `candidate-outcome-unproved`
and still requires rollback; it never permits candidate replay.

## Cut and replay rules

| Durable cut | Permitted continuation |
|---|---|
| before candidate intent | zero-candidate abort only after exact current health or reviewed payload-free Download return |
| candidate intent, result absent/partial/uncertain | no candidate replay; bounded observation and rollback only |
| banner accepted or Android returned without banner | mandatory rollback; neither is terminal |
| rollback-mode reboot intent, result/arrival uncertain | no reboot replay; read-only observation or attended recovery only |
| physical rollback intent/arm | never repeat the physical action; one exact current arrival observation only |
| rollback intent, result absent/partial/uncertain | no Odin replay; retain guard and observe health/recovery only |
| rollback completed but terminal/report missing | read-only exact final-health resume; no repeated transfer |

Foreign/ambiguous endpoints, changed target topology, artifact/helper drift,
malformed journal, or absent recovery retain the guard and stop.

## Host validation

The focused suite passes **13/13**. It proves:

- the exact target map and dormant/no-action surface;
- deterministic binding of witness, builder, observer, shared transport, and
  the independent combined-review receipt;
- distinct exact candidate and resident rollback identities;
- canonical one-member boot-only AP structure and MD5 trailer;
- symlink, hardlink, hash drift, invalid MD5 trailer, extra-member,
  noncanonical metadata, and member size/hash rejection;
- one-shot candidate/rollback budgets and mandatory rollback; and
- banner-as-proof-only plus resident rooted terminal requirements; and
- prepared/candidate/rollback-mode/final boot-ID validation, completed rollback
  binding, rejection of missing mandatory prepared/final IDs, and rejection of
  unchanged or reused terminal boot IDs.

## Remaining gates

This model is not an F1 runner. Before live consideration, a later unit must:

1. implement atomic no-clobber strict-typed journal receipts and shared-guard
   ownership for every cut above;
2. integrate the reviewed S20+ Download attribution and exact Odin transport
   without inheriting authority from the currently active hardcoded runners;
3. integrate the dormant N3-U0 observer under the same prepared topology and
   durable candidate observation;
4. implement the automated and physical rollback branches, final rooted health,
   and reporting-cut resume with hostile fixtures;
5. obtain independent review of that complete executable closure; and
6. amend the binding S20+ target contract and mechanically activate only after
   that review.

No existing bootstrap/resident F1, R1 approval, combined H0 `PASS_GO`, or this
design grants a run, approval, reboot, USB open, Odin transfer, or rollback.

## Independent review

Independent blocker-first review initially returned `NO_GO` because terminal
health did not mechanically bind a fresh non-reused post-rollback boot ID and
the AP parser's hostile fixtures did not cover every stated rejection. A
second review found that mandatory prepared/final boot IDs still admitted
runtime `None` despite their type hints. The final closure requires both IDs as
lowercase 64-hex strings, requires literal rollback completion, rejects reuse
across every present durable boot ID, and includes the missing AP fixtures.

Fresh final review returned `PASS_GO` for this exact dormant H0 closure. It
re-ran focused 13/13, N3 combined 38/38, S20+ aggregate 328/328, `py_compile`,
and scoped diff checks. It performed no device, USB, ADB, `su`, Odin, or
network action. This verdict qualifies only the host model and grants no live
N3-U0 authority.
