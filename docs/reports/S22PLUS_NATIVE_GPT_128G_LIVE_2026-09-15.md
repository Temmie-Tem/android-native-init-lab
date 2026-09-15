# S22+ 128 GiB reservation and rooted Android — live result

The operator-owned `SM-S906N/g0q/S906NKSS7FYG8` now retains a 128 GiB native
partition alongside freshly initialized rooted Android. The final Android
reads prove the proposed GPT and reported filesystem capacity survived the
single planned ordinary reboot. A90 and S20+ received no command.

## Result and limits

| Item | Result |
| --- | --- |
| Native entry 41 | `native_data`, 137,438,953,472 bytes / 128 GiB; unformatted |
| Android userdata partition | 102,497,255,424 bytes / 95.4580078125 GiB |
| Android `/data` statfs total, both verified boots | 102,495,141,888 bytes; 25,023,228 blocks of 4096 bytes |
| Full GPT, both verified Android boots | Exact proposed 61,440 bytes, SHA-256 `c117445fd4a5cd9406e68ea22b14375d6a639c013371ca09a9540740713cbc10` |
| Other 39 entries | Original bytes preserved; existing duplicate GUIDs retained |
| Root, both verified Android boots | Numeric UID/GID 0; exact original Magisk A and supporting partition hashes |
| Operator UI observation | Device Care: 128 GB total, 99.6 GB available, 28.4 GB used |
| Final feature result | `RESERVED_ANDROID_REBOOT_VERIFIED` / `PASS_CHANGED_BOOT_GPT_CAPACITY_AND_ROOT` |
| Final owner terminal | `ANDROID_CLOSED_HEALTHY`, `recovered=true` |

UI labels are the operator photograph's observation; the post-reboot capacity
proof is the machine statfs/GPT comparison. Free space changed normally and was
not required to remain identical. The native partition has not been formatted,
mounted or qualified as a native filesystem. The geometry-only native F2FS
result remains distinct from the subsequent mounted Android health proof.

The original grant covered 7200 BOOTTIME seconds and two operations. It closed
after 3193.642 seconds with both operations consumed, no unused operation and
no F1 owner. There is no continuing grant. Source snapshots and old claims remain
immutable; neither review nor this result grants a future device action.

## Canonical timeline

Times are journal BOOTTIME seconds relative to opening the original grant.

| Seconds | Event |
| --- | --- |
| 23.403–108.188 | Fresh P396-origin health/CONTROL; two P397 installations and four healthy sessions; final complete original-GPT read admits P397 |
| 161.075–170.147 | One GPT apply; four synchronized block writes and exact complete proposed readback |
| 299.102–332.875 | Operator restart completion; different native boot proves proposed GPT and new userdata/native extents |
| 525.309–537.947 | Stock factory-reset completion and fresh native boot; proposed GPT and both F2FS geometry copies pass |
| 541.825–553.907 | Native CONTROL/Download and one exact original Magisk A transfer |
| 807.287 | Initial Android root read stops with completed missing-su rc127 |
| Setup interval | Operator performs app/setup work; later fixed rooted health passes with exact A; a changed boot is observed, cause unestablished |
| 2807.791 | Separately reviewed exact setup-read completion admitted in the same journal |
| 2816.650 | Full initial Android GPT/statfs/root bracket passes |
| 2826.207–2830.099 | Sole planned ordinary Android reboot intended and completed with measured departure |
| 2875.709 | Initial final-health read stops after ADB disappears before `get-devpath`; no root command or GPT read was reached |
| 3035.698–3042.877 | Existing health-only recovery selected; complete final GPT/statfs/root bracket and reboot-persistence proof pass |
| 3193.642 | Task grant closed; shared owner absent |

The metadata, stock reset and original A were not repeated. There were two
bootstrap N transfers, one A transfer, one four-block GPT apply, one stock
factory reset and one planned verification-reboot command. There was no GPT
restore, restorative factory reset or recovery transfer. The observed setup
boot change is not credited as the verification reboot.

## Read failures and completion

The first failure was a completed read returning rc127 and exact missing-su
stderr. It did not establish permission denial or failure of the proved A
transfer. Following operator setup, the existing seven-read Android health
profile proved root and exact A/supporting digests. The initial failed raw
capture and original journal rows 0–19 remain unchanged.

The [fixed setup completion](../operations/S22PLUS_NATIVE_GPT_SETUP_COMPLETION_V1.md)
received separate independent PASS_GO and nine focused tests. It retained the
original task, grant, 54 host/155 native source bindings, consumed operation and
owner. Its separately pinned admission allowed only fresh initial health, the
previously unissued ordinary reboot and final health. It introduced no image,
GPT, reset or repeated-control route. Original adapters and terminal validators
were reused; the new callback checked the deadline before and after intent
publication. H0 publication cuts and admission integrity were exercised.

After the reboot completed, the first final-health attempt observed boot-ready
Android, then `get-devpath` returned device-not-found. Its cause is unestablished.
The existing original-A recovery path performed only a new bounded final-health
read. It rederived the original A transfer instead of sending another payload.
That fresh result proved a different Android boot and identical GPT/capacity
with numeric root. The owner retains `recovered=true` to expose this health-only
recovery; the two failed reads remain failed records.

## Evidence and provenance

Private run evidence is under
`workspace/private/runs/s22plus-native-session-v3/p397-native-128g-20260915-1/`.
Firmware, metadata/identifiers, raw logs and operator photographs remain private.

| Record | SHA-256 |
| --- | --- |
| Original task | `a733a1c365113120fb39650bf25c4851db9cdb345865b08636110a324fc91661` |
| Task close | `ddfa4b31f8ce98327bd8a3acebe971b95d51ab49758cae671c01f2904bea6f58` |
| Final operation terminal | `796158d47ecbf492c874056dfc5597bf7c69170dfd47351ca470e8d4686fb7e5` |
| Original capability review | `5c58cfed21912c41e9ed2cfedcfc476a8a980b80f5a31833ae65d48bdd67866e` |
| Original source snapshot | `65587e35baf99ca67eddb70bc4690d957e509d45fa1a9dd1c9e362f34d3ab874` |
| Setup incident binding | `dd36cd75cde27e8b9ab622d0becd2d810b2e7cd35f36639fedcb6effcfbf178c` |
| Setup completion independent review | `c19edee95edcde5891b119af0440812e53f3b40c09611ec6ea0abf3bd62a1365` |
| Setup completion source snapshot | `e587d175c34e0b140ebdf13329177c139838e06d90176bb4871c09a884e60831` |
| Operator UI observation receipt | `c36c10d9c5fb3f5f27fe0599953a953ad8a029809b0b10d93c4b181fa8d11f8d` |

Original implementation commit: `26ce3b9ca9af5c392c984632ee3440d9f62777a0`.
Exact setup completion commit: `c451cd99a8f4d8a52dccaa792b463d202198548b`.
Raw-based feature/health results and final owner absence were rechecked before
publishing the task close. The prior H0 and historical census NO_PROOF results
retain their original meaning; this is separate actual G2 evidence.
