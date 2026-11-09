# ML028–ML032 USB comparison and ML033 preparation

The retained host journal records ML032's exact candidate USB identity at
**N+180.621 seconds**, followed by NCM registration at +180.685 seconds.
Its first observation ended at +120.252 seconds. The absence of an authenticated
response in that window therefore does not establish that the candidate never
reached USB enumeration. The physical reconnect time and underlying Type-C
mechanism remain unknown. ML032 stays `NO_PROOF / ANDROID_CLOSED_HEALTHY`.

The next bounded unit is [ML033](../plans/S22PLUS_ML033_TIMED_ATTACH_DWELL_LINK_SCOPE_2026-11-10.md):
the same functional stack with fresh identities and prepared, timely use of
the existing single-replug cue. It retains all observation and effect limits.
This report records H0 preparation; execution requires separately reviewed
adoption and current finite attended approval.

## Actual retained differences

Comparison used the artifacts and source snapshots consumed by each run,
not today's development files. Target, physical lane and original A agree.

| Item | ML028 | ML030–ML032 |
| --- | --- | --- |
| Kernel Image | `c069a048…` | `19fc260f…` |
| Image file size | 43,969,024 bytes | 43,969,024 bytes |
| Kernel configuration and physical DTB | Same bytes | Same bytes |
| RAM archive | rc-managed SSH cycle, 7,923,106 bytes | Four-package observer and fixed late module, about 1,573,803 bytes |
| Packaged SysVinit, dynamic linker and common shared libraries | Same retained bytes | Same retained bytes |
| First authenticated base | +62.89 seconds | None in the original window |

ML028 to ML030 changes eight existing kernel files and adds the fixed g0q
header. The early marker is removed; other changes cover RPMh command data/RSC,
interconnect voting, RPMh clocks and the Qualcomm DWC3 helper. Ordinary deny
hooks are conditional on the late issuer. Some trace code runs during ordinary
boot, so absence of a module permit cannot exclude every kernel change from
pre-USB analysis. No defect in that path was demonstrated. Shared USB PHY,
DWC3 core, configfs and NCM source bytes match. Equal Image file size does not
imply equal contents or layout.

The producer inserts the five-minute witness after the first authenticated
response and FDT transfer. Module insertion requires the separate late permit.
Neither was reached in ML030–ML032. VM virtio networking does not qualify the
phone's physical USB path.

## Timing and passive host evidence

| Run | Cue issued | Operator completion record | Authenticated base |
| --- | ---: | ---: | ---: |
| ML028 | +23.81 s | +47.84 s | +62.89 s |
| ML030 | Not issued | None | None |
| ML031 | Not issued; caller refused | None | None |
| ML032 | +18.837 s | Resolved at +220.915 s, after expiry | None |

Times use each host N launch. ML032's resolution record is not a measured
cable-contact timestamp. These runs do not provide a controlled comparison
with equally timed physical reconnects.

The ML032 journal extraction used existing run-file time bounds, selected
topologies and the existing N-launch clock. The grant's host-boot digest matched
the current boot; BOOTTIME-minus-MONOTONIC was within one microsecond. The raw
journal supplies its boot and monotonic timestamps. The candidate serial was
privately compared with the manifest-derived value.

| Passive host event | Seconds after N launch |
| --- | ---: |
| Download device disconnect | 2.562 |
| High-speed USB connection | 180.483 |
| Candidate VID/PID descriptor | 180.620 |
| Exact candidate serial | 180.621 |
| NCM registration | 180.685 |
| Candidate disconnect | 242.719 |
| Physical Download descriptors | 254.310 |

These observations are consistent with a bound gadget, which remains bound
after the initial guest server times out or parks. They are not authenticated
PID1, listener, base, five-minute survival or UFS evidence. Late physical action
and delayed attachment remain distinguishable hypotheses, not measured causes.
Missing journal entries elsewhere would not establish absent device-side binding.

Raw selected journal SHA-256 is
`d4f038559c52272e520776d91e95755a483320621229498f901c77b066d6c161`.
The extractor, join metadata, raw and sanitized events remain in private output
`s22plus-ml033-usb-regression-discussion-h0-20261110-1`. The first query used a
boot digest as a journal boot ID and failed; its error was retained. The
corrected read checked the current boot digest first. No device acquisition
occurred.

## Argon and Opus discussion

Gemini 4 Argon High and Claude Opus 5.5 each received two fixed, sanitized
evidence rounds. The second supplied the late-enumeration record and challenged
the first round's explanations. Both supported a fresh candidate with unchanged
functional code and timely use of the existing cue. No concrete pre-USB software
defect was demonstrated in the supplied sources.

The synthesis excludes stronger model claims: descriptors are not authenticated
PID1 proof; one negative cannot establish deterministic regression; one positive
cannot prove historical cause; and +25 seconds cannot guarantee UDC readiness.
ML028's Image file size was not different. ML033 still needs exact adoption.
Additional old-run journal archaeology or a kernel/userspace cross is not a
prerequisite for this prospective unit.

Four calls completed without fallback or model tool execution. Private
before/after quota, provider tokens, prompts and responses are retained in the
existing external-model ledger. Account quota movement, token counts and CLI
list-price equivalents remain separate from actual subscription billing.

## Fresh candidate qualification

The unchanged producer generated new physical and VM keys, identities,
observers and canonical archives. Image, module, physical DTB and four signed
packages retain their original reviewed provenance. Both observers and archives
reproduced byte for byte. The new loader embeds those exact inputs, and two
packages agree with the single-member boot-only AP. The scope lists its hashes.

Actual ARM64 loader checks cover transfer, placement rejection, cache/MMU/endian
checks and 1,051 aligned-copy cases. Separate actual EL1/EL2/EL3 VM checks cover
entry. Four new guest cases cover early challenge refusal, invalid permit,
wrong-board rejection and modeled successful late return. The actual collector
measured 300.019 and 300.025 seconds from base sealing to challenge; guest uptime
advanced 300.162 and 300.156 seconds. Modeled power/UFS is not physical proof.

The H0 join rejects the new AP through the pre-adoption validator while raw
acquisition, processes and sockets are blocked. The fixture build initially
lacked its mode argument and failed before creation; the retained log precedes
the successful explicit `build` call. No replay or weakened assertion was used.

## Applicable failures and remaining frontier

ARTIFACT and WIRE are confirmed by producer reproduction, loader/AP inspection,
the real collector and raw guest cases. SEMANTIC and AUDIT keep descriptor timing,
authenticated protocol, physical action and cause distinct. ROUTE, HOST and
RETURN require prospective admission/owner review and current preparation;
recovery remains original A under the original durable owner. ABI and IO
machinery are unchanged and retain their review. PERSIST preserves old records
and fresh private outputs. DISPLAY is inapplicable; no display path changes.

The independent candidate review returned `PASS_GO` with no findings. It binds
input SHA-256 `1939dcab33c87019c708c038a8ffb627a15a1285a9950b9c2ad5103cfdb13a2c`;
its result SHA-256 is
`ead43fc443d190c8172acce60ca760e4674e5122edabec5d2fb3c8c3a24b8503`.
The reviewer rechecked both APs, embedded ELF inputs, actual exception levels,
producer reproduction, four guest cases and 32 sealed raw captures, and
independently rederived the host-journal identity and clock joins. The unchanged
cue's 26-test evidence was reused by exact source hash.

The prospective owner/adoption checks accepted four exact artifact bundles and
rejected 45 mixed or unknown variants. Four source-consistent adoption cases,
101 focused owner/return/bridge tests and four actual-Session cue-unavailable
recovery/health cases passed. The 101 tests and recovery fixtures precede the
declarative ML033 registration; their execution logic is unchanged, and the
new declaration is covered by the subsequent real admission/adoption checks.
The common mainline policy's old current-review literal was found during
independent review and aligned with the new selected receipt; no runtime
condition changed. The policy also now explicitly distinguishes unchanged
guest functional source from the new generated observer identity.

The final owner/adoption review returned `PASS_GO` with no open findings,
binding input SHA-256
`236efc354defa97421643b76157333d47bdb020c13bb4a3a516b50234e629b38`.
Its result SHA-256 is
`f273fd16eed47c9db22eb58a0c598c338eb30f9070833dc92920e99720320de8`.
It covers 55 mainline sources and 51 bridge sources; seven bridge paths changed
and none were removed. All prior candidate declarations and dedicated policies
remain unchanged. Both stable worker sources are unchanged. The new mainline
capability and immutable V37 backend review were published after exact hash
verification and no-owner checks under the existing locks. The selector was
updated atomically, and the connected worker reported the exact V37 review.

The exact task and connector preparation bind ML032's healthy closure and
original A. The cue CLI is preloaded and its operation-specific raw capture
commands are prepared. One foreground fixed D0 invocation completed and its
raw Android health and readiness were revalidated successfully. That observation
is separate from this H0 qualification and from the still-required returned finite
approval and current attendance/Download recovery. No old consumed permission
or readiness result supplies that approval.

No new grant, control or partition transfer has occurred in this H0 unit.
A90, S20+ and unrelated boot-journal work remain untouched.
