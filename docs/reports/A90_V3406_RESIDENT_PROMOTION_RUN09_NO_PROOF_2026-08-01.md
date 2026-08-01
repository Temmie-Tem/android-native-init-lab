# A90 V3406 resident promotion run 09 no-proof report

Run `a90-v3406-debian-display-f1-20260801-09` is closed
`NO_PROOF_A90_F1_RP_CANDIDATE_ROLLED_BACK`.

## Result

- The exact approval was consumed once.
- Rootfs staging and candidate preflight passed.
- One boot-only candidate transfer completed with no replay.
- The first candidate version, selftest, and promotion health checks passed.
- The resident reboot command was accepted and a new exact A90 USB serial
  epoch appeared.
- The first safe `version` probe on that returned epoch received only its
  command echo and `a90:/#` prompt. No A90P1 frame was accepted.
- One exact V2321 rollback transfer completed from the durable journal.
- Final V2321 version/build, selftest `fail=0`, and pstore health passed.
- Debian PID 1 and display acquisition were not proved. S22+ was untouched.

The private result SHA256 is
`d2530ef3e187823249f7803a9e3d6851bcd398a2b8504e79c078a12a8aa81ecb`;
the private timeline SHA256 is
`4b8f79f6640b649a26891eb6608f02a011e759fc05acb2a689bc7165090b5839`.

## Host observer finding

USB connectivity was present. The host confirmed the new exact A90 epoch and
received serial bytes, but `should_retry_cmdv1_exchange()` did not classify an
exact prompt/echo-only response as retryable. `version` was already in the
safe observation allowlist, yet the first not-ready response became a terminal
framing error before the channel-settle sequence could run.

The bounded H0 repair recognizes only prompt/echo-only transcripts as a retry
signal for safe commands in `slow` or `double` mode. It does not accept them as
proof. Arbitrary partial output and unsafe commands retain the old stop
behavior. Independent review returned GO.

The long-running serial bridge captured this run into an older private capture
path. That did not cause the failure, but the capture must be rebound to the
next run before another live attempt so evidence does not cross run names.
