# NATIVE_INIT V2398 — Audio Magisk module strategy

## Scope

Host-only strategy note. No Android boot, ADB command, Magisk install, native speaker write,
`/dev/snd` open, mixer write, playback, or ACDB ioctl ran in this unit.

The user pointed out that the Wi-Fi work used Magisk-style Android handoffs effectively. This report
locks the equivalent audio policy before any AUD-5A live run.

## Decision

Magisk is useful for audio, but only as an Android-side measurement and delivery capsule. It must not
become a native-init runtime dependency.

Current V2397 stays on the lowest-risk tier:

- transient Magisk-root helper staged under `/data/local/tmp/a90-audio-acdb-v2396`;
- invoked manually through `su -c`;
- no persistent `magisk --install-module`;
- raw logs and generated module artifacts remain under `workspace/private`;
- cleanup and rollback to V2321 are mandatory.

This matches the Wi-Fi precedent: use Android/Magisk to observe the stock Android-good path, extract
the bounded sequence, then port only the necessary native-safe pieces into native init.

## Module tiers

| Tier | Use | Audio trigger | Allowed by default |
| --- | --- | --- | --- |
| M0 transient helper | Stage scripts/tools and run them with `su -c` after Android ADB/root is ready | V2397 ACDB/App Type baseline/active/post probes | yes |
| M1 temporary boot module | `post-fs-data.sh`/`service.sh` sampler for events that happen before ADB/root attach | only if V2397 misses early ACDB/App Type edges | no; needs a new exact gate |
| M2 vendor overlay/wrapper | Magisk overlay around a vendor binary for syscall-level capture | only if a specific vendor process must be wrapped | no; last resort |
| Runtime dependency | Require Magisk/Android services for native speaker playback | never; this means HAL-dependent closure, not native success | no |

## Escalation criteria

Stay at M0 if V2397 captures any of these with enough ordering detail:

- `Audio Stream 0 App Type Cfg` / app-type mixer values;
- `ACDB`/`acdb_loader`/`msm_audio_cal` markers;
- `send_afe_cal` / `q6asm_send_cal` / `adm_open` success or failure transitions;
- baseline → active → post deltas that map to a bounded native-init sequence.

Escalate to M1 only if the V2397 artifacts prove that the relevant ACDB/App Type work happens before
ADB/root staging can observe it. M1 must be temporary, rollbackable, and auto-cleaning; it needs a
fresh exact approval phrase because it changes Android boot-time behavior.

Escalate to M2 only if host analysis identifies one concrete vendor process and one concrete syscall
or file-open edge that cannot be captured by logcat, tinymix snapshots, dmesg, or M1 sampling. M2 must
include a non-recursive original-path guard and must not write vendor partitions.

## Consequences for the next unit

The next live-capable unit remains AUD-5A/V2397: run the current transient Magisk-root measurement
only after the exact phrase is supplied.

After live artifacts exist, the next host-only unit should parse the private capture and classify:

- `bounded-native-acdb-candidate` — a small ACDB/App Type sequence can be replicated natively;
- `hal-dependent-or-opaque` — the stock HAL path is too broad to reimplement safely under native init;
- `capture-incomplete` — measurement failed or missed the timing window, in which case M1 may be
  designed as a follow-up.

## Validation

Host-only checks:

```text
git diff --check
```

No live command was run.
