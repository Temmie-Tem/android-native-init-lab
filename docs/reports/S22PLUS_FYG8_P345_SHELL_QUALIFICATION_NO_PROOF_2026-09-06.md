# P345 shell qualification: incomplete observation, healthy rollback

Run: `p345-ready2-prepared-20260906-2`. Candidate is consumed and must never
be replayed. Exact candidate AP `28631081B/7ee59a13` and Magisk rollback
`23367721B/d2373bf8` each completed once. Journal is CLOSED with 19 records;
final rooted FYG8 health, original boot/supporting hashes and absent Download
are verified. No more device effect is required for reporting.

Canonical journal timeline (UTC; event names do not promote candidate proof):

| Event | Time on 2026-09-05 |
| --- | --- |
| live_session_start | 18:25:38.423490Z |
| candidate_flash_start | 18:25:57.005361Z |
| candidate_flash_done | 18:25:58.629020Z |
| candidate_boot_ready | 18:27:02.714349Z |
| rollback_flash_start | 18:27:06.885714Z |
| rollback_flash_done | 18:27:08.424276Z |
| rollback_boot_ready | 18:27:50.110011Z |
| live_session_end | 18:27:50.131409Z |

The five-session qualification did not pass. The first readonly-canary session
stopped at `exec-read`; zero complete sessions were accepted. The retained
670-byte stream contains framed sequence-4 output reporting UID/GID65534,
uptime, an EPERM probe-creation failure, probe-absent and canary markers, then
EXIT0 and sequence-5 output/EXIT. This is partial evidence, not completed
qualification or a comprehensive device isolation proof. No DONE frame was
present in this bounded stream. The underlying termination cause is not yet
established.

Two distinct host reporting errors occurred:

1. After preserving the observer receipt, `observe_candidate` selected a
   generic P328 projection and raised `KeyError: hmac_authenticated` for the
   P345 receipt. This does not explain the earlier incomplete exchange.
2. Journal-only recovery completed exact rollback and final health, but final
   result validation raised `live result does not reopen against durable
   state`. At this record's publication, `live-result.json` is absent; do not
   invent a published terminal verdict or repeat a device transition to fix it.

Retained private evidence under the run directory:

- `candidate-observer.json`: 9840B, SHA256
  `f8ee7fcfab414f0e697c0e6b6491af5af6a94d2ca9e44ae8765049129319d210`.
- `candidate-observer.raw`: 670B, SHA256
  `a8d28dc66cd333ef1c9b65817f4a28b8f467840fca63fd91f04cd8a891462b60`.
- `live-state.json`: 13005B, SHA256
  `d09dd61ee24246589c4494d01cb02cd43123b2a2f90ee01464e2f872507584b7`.
- `transaction/journal-head.json`: 276B, SHA256
  `a968c1628191978f0b97202b13e30432e5d17fad491074e2ad431c666e2acf42`.

The next work is host-only diagnosis and independently reviewed minimal
reporting repair using retained evidence. No protocol redesign, new gate,
candidate replay or wider shell authority follows from these errors.

Host-only rederivation isolated the finalizer discrepancy to two P345 metadata
representations: integer diagnostic-map keys versus JSON string keys, and a
header-stage tuple versus a JSON list. Changing only the isolated in-memory
variant to the stored JSON representations passes full `validate_live_result`.
The source, prepared binding, CLOSED journal, live state and raw evidence stay
unchanged. The resulting verdict remains
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, outcome
`p345_readonly_research_shell_unproved_rollback_verified`, with
`recovery_required=false`.

After independent review, terminal-only publication completed using the
original ready2/source binding and existing no-clobber writer. The landed
`live-result.json` is 15689B, mode0400, SHA256
`039bcb3fad8bdea1d3336961793751e01fa6d5163e202a61c38667c832261fac`.
It records CLOSED and the NO_PROOF verdict/outcome above. The earlier missing
file statements describe the incident before this repair, not the final state.
No source, journal, live state, prepared record or raw capture was rewritten;
no device command was repeated. The legacy P328 host projection still needs
its scoped P345 exclusion and partial-receipt regression before another run.


## H0 exchange and projection repair, 2026-09-06

Current-source inspection against the preserved stream identifies the parent
witness rejection: sequence 3 reports numeric UID/GID zero without NSS names,
while both the exchange and semantic validator required `(root)`. The exchange
checks that witness after sequence 5 and before sending CLOSE; this explains
the retained complete command EXITs without a DONE. The child also reports a
GID immediately followed by the denied supplementary-group lookup warning.
That output would fail the previous canary regex after the parent fix.

The bounded repair shares one numeric parent-ID predicate, requests child
`id -u` and `id -g` under distinct exact numeric markers, constructs P345
metadata with JSON string keys/lists, and excludes P345 from the incompatible
P328 result projection. The syscall filter and device C sources are unchanged.
Wrong/missing/duplicate numeric IDs still reject. The five expected outcomes,
authentication, raw capture, limits, exact target and mandatory rollback checks
remain required. Exit 126/127 classification is unchanged and outside this unit.

Validation: P345 suite 43/46 passed, including actual C/Python same-descriptor
normal, exit-7, cancellation, timeout and subsequent command execution with a
numeric-only parent witness. The three historical stock-build reopening tests
reject `p345-observer.py identity differs`: the consumed build pins old source
bytes. Those pins and artifacts were preserved. Shared exchange tests passed
8/8; child tests passed 9/9 after adding numeric BusyBox identity queries under
the actual host-mapped seccomp filter; common F1 live tests passed 74/74.
Touched Python compiles and scoped diff whitespace checks pass. These are host
checks, not a fresh target isolation or five-session device proof.

Independent changed-path review returned PASS for bounded H0 code repair only
and independently passed the three P345 live-observer tests. Reviewed source
SHA-256 values:

- exchange: `ac3b47884ed29404b5afc047557486b5c90ece2e85dc799123d100a7238df2c3`;
- P345 observer: `7d24a1ae005ef07235a45a8c24256ae3fcf1ba4972620868730318b6b51a1b12`;
- F1 live: `26a9633fc23ee45e14f27bc41b17897ead6b4bcc65a1c184e776505734aa7915`.

This changes the working H0 source closure, not the consumed P345 evidence or
ready declaration. Historical raw-first source pins remain unchanged and will
reject these new bytes. A successor needs its fresh identity and source/artifact
qualification, reviewed matching audit pins and execution closure, a new ready
declaration, ordinary preparation and attended F1 approval. No existing run is
replayed or reclassified; no device command or other-target edit occurred.
