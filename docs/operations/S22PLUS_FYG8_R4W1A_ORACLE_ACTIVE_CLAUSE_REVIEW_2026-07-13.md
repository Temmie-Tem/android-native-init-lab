# S22+ FYG8 R4W1-A Oracle ACTIVE Clause Review Source

State: `REVIEW_COMPLETE_BINDING_COPY_ACTIVE`

This file preserves the exact text reviewed for binding `AGENTS.md`. This
source file is not itself policy authority. Its proposed text has now been
copied into binding `AGENTS.md`; execution remains blocked until that binding
change is committed and the operator supplies the exact fresh acknowledgement.
The retained-PID1 candidate policy remains inactive.

## Proposed Binding Text

**Narrow operator-authorized exception (2026-07-13, S22+ FYG8 R4W1-A
zero-flash bugreport oracle dry-run):** This clause may be activated only for
Samsung S22+ `SM-S906N` / `g0q` / `S906NKSS7FYG8`. Policy marker:
`S22+ FYG8 R4W1-A bugreport oracle dry-run live gate`.

`S22PLUS_FYG8_R4W1A_ORACLE_DRY_POLICY_STATE=ACTIVE`

The only executable helper is
`workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1a_live_gate.py`
SHA256
`d541397c823b7c6311dbec950dd3a82dc6a5881984b45838c99ffedebc2d3d14`.
Its focused test source SHA256 is
`314b3efc9fec555b31bf6b926bcdbe4b34ebe75ad17bf1172d0e3027e52bf145`.
The required acknowledgement is
`S22PLUS-FYG8-R4W1A-BUGREPORT-ORACLE-DRY-RUN` and must be supplied fresh by the
attending operator after this exact clause is reviewed and committed.

Before device contact, the helper must rerun its full offline artifact gate and
require exact candidate boot SHA256
`a2bba0ef907af14e57508ca55d247d571c3f89936dd7020293e51ebfa8f8d133`,
boot-only candidate AP SHA256
`cb2c078f001af6e263dc3f533a2efe3294a5c80201f50952a45bb88254e4d895`,
marker-oracle source SHA256
`bfc7a8d76892931ff7faed25606cc7c7c92cf6ef3f67357316ee25b0fa887462`,
and Magisk rollback AP SHA256
`d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.
These boot artifacts are identity/precondition pins only; this exception
authorizes no transfer or flash.

The helper must validate promotion record
`workspace/private/state/s22plus_fyg8_r4w1a_connected_dry_run_pass_v3.json`
SHA256
`6b78cfb646432bb2dcb8f65a47a7e547d4b8a3862c72cb0ada2cc6237f2c4084`,
reopen its named result SHA256
`5e54811e8e3363fa372ca65e2938565e7465511b6b0e5bbe0754679ef7a5c5d3`,
and prove schema `s22plus_fyg8_r4w1a_connected_pass_v3`, current helper SHA,
exact target, read-only mode, PASS verdict, and `device_writes=false`.

Connected preflight must start from exactly one normal Android target with
completed boot, stopped boot animation, orange verified-boot state, Magisk
`uid=0(root)`, exact known Magisk boot, stock DTBO and recovery, no Odin
endpoint, live `sec_log_buf`, exact bind
`/sys/bus/platform/drivers/samsung,kernel_log_buf/8.samsung,kernel_log_buf`,
both proc observers readable to EOF, no R4W1 marker contamination, and both
`/sys/fs/pstore/console-ramoops` and `console-ramoops-0` absent. Any mismatch
stops before the one-shot state or capture.

Immediately before capture, the helper must durably and exclusively create
`workspace/private/state/s22plus_fyg8_r4w1a_oracle_dry_run_consumed.json`.
Creation consumes this exception regardless of result. The helper may then:

1. inventory direct `/bugreports` entries through non-root shell;
2. execute exactly one bounded `adb exec-out bugreportz -s` capture;
3. require every preexisting entry unchanged and exactly one new direct,
   non-symlink regular file;
4. require exact size and SHA256 equality across remote file, original host
   stream, and parser input;
5. parse one complete CRC-valid ZIP and require marker-family absence in the
   exact `LAST KMSG (/proc/last_kmsg)` section and complete archive;
6. only after remote/stream identity is proven, remove that exact run-created
   path through non-root shell while rechecking path, stat tuple, SHA256, and
   final baseline inventory; and
7. revalidate exact Android/Magisk health and no Odin endpoint.

The capture is bounded by the helper's fixed 600-second and 2-GiB limits. A
timeout, malformed ZIP, stderr, multiple or unsafe new paths, preexisting-entry
change, host/remote/parser mismatch, cleanup failure, transport ambiguity, or
any gate error is non-PASS and does not authorize retry. Parser failure after
remote/stream identity proof may still perform only the exact cleanup above.
No wildcard, recursive deletion, root deletion, or deletion of a preexisting
or identity-mismatched path is allowed.

PASS is only `PASS_R4W1A_ORACLE_DRY_RUN_EXACT_ZIP_AND_CLEANUP`. It may create
`workspace/private/state/s22plus_fyg8_r4w1a_oracle_dry_run_pass.json` only after
capture success, parser/stream identity match, marker absence, and verified
cleanup. Timeline output must use only the canonical eight
`events:[{name,timestamp_utc}]` phases with explicit zero-flash semantics.

This exception authorizes exactly one run-created bugreport file creation and
its exact cleanup. It authorizes no reboot, Download transition, Odin transfer,
candidate or rollback flash, raw host `dd`, fastboot, partition write, Magisk
module, panic, SysRq, RDX/S-Boot command, RAM dump, qdl/Sahara/Firehose,
EUD/UART write, format, userdata cleanup beyond the exact run-created file,
or A90 action. It does not activate the retained-PID1 candidate policy. The
operator must provide a separate fresh approval before the capture starts.

## Activation Verification

The binding copy was validated without device contact after insertion:

- helper SHA256:
  `d541397c823b7c6311dbec950dd3a82dc6a5881984b45838c99ffedebc2d3d14`;
- focused test SHA256:
  `314b3efc9fec555b31bf6b926bcdbe4b34ebe75ad17bf1172d0e3027e52bf145`;
- v3 connected promotion-record SHA256:
  `6b78cfb646432bb2dcb8f65a47a7e547d4b8a3862c72cb0ada2cc6237f2c4084`;
- named v3 connected result SHA256:
  `5e54811e8e3363fa372ca65e2938565e7465511b6b0e5bbe0754679ef7a5c5d3`;
- Python bytecode compilation: PASS;
- related R4W1-A tests: `48/48` PASS;
- complete offline gate: `PASS_R4W1A_LIVE_HELPER_OFFLINE_CHECK`;
- policy state: `oracle_policy_active=true`,
  `candidate_policy_active=false`;
- offline side effects: `device_contact=false`, `device_write=false`,
  `flash=false`;
- oracle consumed/PASS and candidate consumed records: absent.

The reviewed zero-flash oracle is therefore source- and policy-ready for one
fresh-ack attended invocation after this binding change is committed. This
verification did not contact the device and did not consume the one-shot
exception.
