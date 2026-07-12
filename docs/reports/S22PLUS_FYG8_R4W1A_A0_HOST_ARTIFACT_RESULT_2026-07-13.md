# S22+ FYG8 R4W1-A A0 Host Artifact Result

Date: 2026-07-13 KST

Verdict: `PASS_R4W1A_A0_HOST_ARTIFACTS; A1_HIGH_RISK_UNRESOLVED; NO_LIVE_AUTHORIZATION`

## Scope

This unit implemented only the host-side A0 contract. It added a dedicated
candidate builder, independent static checker, overwrite-budget analyzer, and
negative tests. There was no device contact, USB enumeration, connected dry
run, candidate flash, rollback flash, A1 helper, or policy exception.

## Implementation

| Item | SHA256 |
| --- | --- |
| `build_s22plus_fyg8_r4w1a_candidate.py` | `081d608ef54ddd171aaa2013c5b06eb33b72aba760192e66ac023dc2f23e759f` |
| `s22plus_fyg8_r4w1a_static_checker.py` | `cb2fb233370463135d6f8a26c2fbd93fb3404c973aa5b326a94c6ec149c2f711` |
| `s22plus_fyg8_r4w1a_overwrite_budget.py` | `f15cf921cc7991ce05576d2eff7ea48fabc6a5c8e86200e0d15750e563ecbd2b` |

The builder starts from exact R3C0 raw boot
`384efeb0f81534cbfaf3643f42e34fb6e01fe6f0b6bf80139a047a1f9a71f29f`
and inserts exact R4W1 Image
`9552653de86dbdc2f1abd919b4d7b0d3f365fc878a56ed5ae09c82d0d81d844c`
only at `[4096,41495040)`. It preserves every byte outside that interval.
The strict LZ4 and parse-only Odin programs execute from private staged copies
whose bytes are revalidated before execution. Odin receives only fixed
nonexistent path `/dev/bus/usb/999/999` and must fail before device open.

The checker does not import the builder. It independently reconstructs the
candidate from pinned inputs, validates exact boot geometry and preserved
regions, parses the one-member AP and LZ4, confirms stale AVB payload semantics,
and rehashes the full extracted six-file FYG8 firmware evidence plus Magisk and
stock boot-only rollback chains. It also verifies the patch has one successful
ramdisk `/init` exec predicate, exact PID 1 guard, and one record call after the
success condition.

## Reproduction

Final checked source generated reproductions A, B, and C. All four generated
files are byte-identical across the three outputs.

| Artifact | Size | SHA256 |
| --- | ---: | --- |
| raw `boot.img` | 100,663,296 | `a2bba0ef907af14e57508ca55d247d571c3f89936dd7020293e51ebfa8f8d133` |
| `boot.img.lz4` | 27,716,775 | `0bf83af2bb7167aae4a57be1686599aa99fe9e75ccd7aa89128da799a4c14a99` |
| `AP.tar.md5` | 27,719,721 | `cb2c078f001af6e263dc3f533a2efe3294a5c80201f50952a45bb88254e4d895` |
| `manifest.json` | 3,398 | `3b9b5c0f0d3bac818a010cb7682e1146eaa50d5feec8a16324a039bbd5d2f85b` |

The independent checker returned
`PASS_R4W1A_THREE_REPRO_STATIC_CONTRACT`. Its private result is 26,014 bytes,
SHA256 `fc528ba9c8acce18a636d398a13add42a7882e7bfd505e82d63ff861e0963a0b`.
It reports three byte-identical candidates, independent reconstruction, and
zero outside-kernel changed bytes.

## Overwrite Budget

The analyzer validated three exact 2,097,136-byte captures:

| Capture | Oldest timestamp | Latest timestamp | Visible span |
| --- | ---: | ---: | ---: |
| O11 post-rollback stock | 3.541924 | 35.415962 | 31.874038 |
| V3437 candidate | 3.453647 | 33.253545 | 29.799898 |
| V3439 first stock boot | 3.342527 | 27.748355 | 24.405828 |

The result is `HIGH_RISK_UNRESOLVED`, `a1_ready=false`. These full payload
snapshots do not reveal exact wrap count or bytes written since the early
witness, and their missing prefixes mean rollback-time marker absence cannot
prove `/init` rejection. The private result is 2,318 bytes, SHA256
`ec6052c0165e17f202a103bae7ee376c873f0aefcf72f3a86370fdc821711301`.

## Validation

- 16 new focused tests passed.
- 72 related R3/R4 tests passed.
- Python bytecode compilation passed.
- `git diff --check` passed.
- `ruff` was unavailable on this host and was not installed during this unit.
- Opus implementation review returned `GO` with no commit blocker and agreed
  that A1 remains blocked. Its low tool-TOCTOU note was subsequently closed by
  staged exact tool execution, and its test naming note was corrected. A final
  delta recheck was attempted but the existing session had reached its usage
  limit; local tests and independent artifact checks were rerun after the fixes.

## Boundary

A0 proves deterministic construction and the static host contract only. It
does not prove that the candidate boots, that Android reaches a milestone, or
that the marker survives until any candidate or rollback observation. No A1
implementation, connected dry-run, `AGENTS.md` exception, device action, or
flash is authorized by this result.
