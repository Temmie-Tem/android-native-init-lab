# S20+ G986N Native-Canary R1 Install-Transcript Incident

Date: 2026-08-16

Target: operator-owned `SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2` only

Status: **CLOSED - INTENT-ONLY CANARY DISABLED ROOTED HEALTHY - INSTALL/REBOOT REPLAY FORBIDDEN**

## Outcome

One freshly prepared and attended R1 run durably published its install intent,
then the fixed Magisk v30.7 command returned rc `0`, empty stderr, and a
complete success transcript. The fixed install command's in-command tree
checks passed before its success sentinel, but no separate durable
post-install-audit command or journal node was published; no reboot intent or
reboot command had followed at that initial stop.
The exact private `install.stdout` is retained only in the private run; its
SHA-256 is
`a8127967c1e9ffbc12d32f6630ed0bdbc4c12237c009a4bf727e7348d0e7e5eb`.

The active host parser rejected that successful result because its closed
grammar began at the module title and omitted the preceding source-defined
line `- Device is system-as-root`. Official Magisk v30.7 commit
`e8a58776f1d7bdf852072ad0baa6eceb9a1e4aac` emits that line from
[`mount_partitions()` in `scripts/util_functions.sh`](https://github.com/topjohnwu/Magisk/blob/e8a58776f1d7bdf852072ad0baa6eceb9a1e4aac/scripts/util_functions.sh#L257-L305)
when `SYSTEM_AS_ROOT` is true, before the same `install_module()` path prints
the module title and extracts the module. The observed first line is therefore
legitimate v30.7 output for this target, not a second install, warning, or
foreign transcript.

## Stop and no-replay decision

The install intent consumes the sole installation attempt even though the
host parser failed after command return. Staging and installation must not be
repeated. At the initial stop the journal contained the exact prepared prefix, four
complete successful stage command tuples, one install intent/event, and one
complete successful install tuple; it contains no post-install audit, reboot,
disable, cleanup, stock handoff, or terminal node. Host-only validation of
that private journal reports 23 exact nodes and accepts the corrected whole
stdout grammar.

This is a host parser/reporting failure after a persistent effect. It is not a
reason to reinstall Magisk, restage the module, delete the guard, issue an
ad-hoc `su` command, or infer PASS. The run therefore remained stopped with its
guard held until the separately reviewed continuation became active.

## Exact reviewed continuation

The candidate adds one named `--resume-after-install --run-id <closed-id>`
entrypoint. It is restricted to the exact predecessor binding SHA-256
`89098a4190d3ab2a85ddf0efd8b12ffdd800f79cf4146b8302f8e23832cf1845`
and predecessor runner receipt: 213,403 bytes, SHA-256
`35dfc7557c5c9e9b3e62d4865e81122572c57d0464997f4e2a35904a0b15432f`,
normalized SHA-256
`6c64c8763fd0ab68fe2b88721f6d6d1f0f9c28f96b4595f028c0af7c143194ad`.
It accepts only the exact corrected install transcript and the exact
post-install/pre-continuation journal cut.

Before any connected read, the candidate atomically publishes a typed
predecessor-to-successor continuation receipt binding both runner identities,
the exact prepared binding, and the raw install result/stdout hashes. That
receipt records `device_effect_count=0` and
`install_replay_permitted=false`. It then requires the same prepared serial,
topology, and boot ID before any privileged read, revalidates the prepared
Magisk/helper bytes, performs only the existing read-only post-install tree
audit, and enters the already reviewed first/replay/disable/terminal chain.
It contains no call from the continuation entrypoint to staging or install.

Any missing, extra, indirect, duplicate-key, bool/integer-substituted,
wrong-binding, wrong-runner, changed transcript, foreign target, changed boot,
or changed helper evidence stops before the first reboot. Once the continuation
receipt exists, all later root/stock/finalizer cuts revalidate that exact
predecessor-to-successor receipt. Once a reboot intent exists, this special
entrypoint is no longer eligible; the ordinary no-replay recovery state
machine owns later cuts.

The self-blocked candidate is 223,363 bytes at SHA-256
`e2725e77dc552384eedc669902e35790af940d15fc786240171b50cc608ea420`,
normalized SHA-256
`39cdf9eda1eb4fa8240bab49c1a45fdf54b63431908fd6721cdde2453e77544c`.
Focused tests currently have 118 logic passes and one expected stale-identity
failure in the self-blocked candidate. Independent review returned `PASS_GO`
with no unresolved finding. The separate identity-only rotation produced the
active 223,363-byte runner at SHA-256
`63e58f99b06275ed0d1eeacc5d87dbb7fdc1a9f471fcd7645f447345b23a3b52`
and the same normalized SHA-256 above; post-rotation focused validation is
119/119 and the canonical eight-module S20+ aggregate is 281/281. This report
does not authorize installation replay or any action outside the exact guarded
run continuation.

## Live continuation and recovery result

The active continuation revalidated the exact 23-node predecessor cut,
published its zero-effect continuation receipt, rebound the same prepared
Android boot before root, and passed the separate read-only post-install tree
audit. It then issued the first ordinary reboot exactly once. The returned
exact rooted target passed the active-tree audit, and the canary had published
its canonical intent, but its result file was absent. The runner durably
published only `first-intent.raw`, stopped, and did not replay installation or
the first reboot.

The already-authorized Android-root recovery classified the live canary state
as `intent-only`, created the one module disable marker, and issued one recovery
reboot. Final evidence proves the exact target returned rooted healthy, the
module is disabled, the canary remains `intent-only`, owned staged inputs are
absent, stock/Odin attempts are zero, other-target command counts are zero,
and both install and reboot replay permissions are false. Terminal verdict is
`RECOVERED_S20PLUS_G986N_NATIVE_CANARY_N1_DISABLED_ROOTED_HEALTHY`; the shared
guard is released. Private terminal result SHA-256 is
`146230b0744b956bfa03c5088b7022ffe89be4d2596f0ebd3bb600eb495c7d66`.

This is a safe recovered result, not N1 canary PASS. Any future N1 candidate
must first explain why the native canary wrote intent but not result and must
use a fresh reviewed transaction; this closed run cannot be replayed.

No raw device identifier, private journal, module bytes, or raw command log is
included in this tracked report.
