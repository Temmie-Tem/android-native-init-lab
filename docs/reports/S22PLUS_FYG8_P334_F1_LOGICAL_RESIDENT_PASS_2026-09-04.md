# S22+ FYG8 P3.34 authenticated logical-resident F1 PASS

Date: 2026-09-04 KST

Target: `SM-S906N / g0q / S906NKSS7FYG8`

Formal verdict:
`PASS_F1_V2_P334_AUTHENTICATED_LOGICAL_RESIDENT_FIRST_CONSOLE_RETURN_AND_ROLLED_BACK`

Outcome:
`p334_authenticated_logical_resident_first_console_return_rollback_verified`

## Result

P3.34 succeeded on its primary observer. The exact boot-only candidate and
Magisk rollback each transferred once, with no attempt 2. The candidate
observer reopened as `accepted` and proved two complete authenticated logical
sessions on one continuously open tty file descriptor:

- sessions attempted/successful: `2/2`;
- physical reopen/reconnect: `0/0`;
- HMAC authentication: true, with distinct nonce hashes;
- fixed BusyBox commands: `6/6`, three per session, all exit code `0`;
- diagnostics in each session: stage `0`, then `OPEN_PARSED` stage `1`, then
  RNG stage `2`, all code `0`;
- clean framed close: true;
- caller-selected command, interactive PTY, arbitrary file transfer and
  persistent state: false.

The second logical session can start only after the first console call returns
to the outer loop. The primary receipt therefore proves the first console
returned and that the prior P3.32/P3.33 first-session failure did not recur.
It also proves native-PID1 authenticated bidirectional USB and bounded static
BusyBox command execution for two consecutive sessions without reopening the
tty.

## Supplemental return record

The deferred Carrier supplement did not contain P3.34's generation-107,
stage-147 return-detail record. Both stable rollback reads contain one P3.34
record at offset `1,657,037`, ending at generation `106`, stage `146`; the
instrumented numeric return detail was not published before the attended
rollback began. Consequently the exact numeric return value/errno is not
claimed. The final result retains this honestly as
`P334_STOCK_PARSER_EXCEPTION`, `accepted=false`, while the independent primary
session proof remains successful.

The ordinary runner had an intended supplemental-parser fallback, but the
adapter raised `AdapterIdentityError` while that boundary caught only the
wrapped `F1LiveError`. This was a host finalization defect after candidate,
rollback and final-health collection, not a device or transport failure.

## Exact evidence

- run: `p334-ready1-prepared-20260904-1`;
- candidate AP: 28,631,081 bytes, SHA-256
  `d79ecf0721604dc30b32777e6a8bfdda54609198b09e3cf081d62446fcbaf7dc`;
- rollback AP: 23,367,721 bytes, SHA-256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`;
- candidate raw: 1,162 bytes, SHA-256
  `06a1cdcfd547d652bc6cb76745599e61ad280933c82c8ad8f340e4f28eae80a8`;
- candidate receipt: 15,385 bytes, SHA-256
  `811d8c0340b4058c7e5f5ecaa0fb5ef629dd96179c2f12a5bf10a61c5e25d28d`;
- identical rollback reads: 2,097,136 bytes, SHA-256
  `3492285992bacda0d82494093433dcfa42c56142191d97389fdab9dfa0eebc3e`;
- final state: 13,105 bytes, SHA-256
  `ebfc0e3a908ddd8b0966ded809a711d76d37e88bff916e95c348773321250ff5`;
- final result: 15,807 bytes, SHA-256
  `91ba8a7e0642155c0a2bf5a111beff32854fabe673866e434413c486b9bb63ed`;
- CLOSED journal: 19 records, terminal record SHA-256
  `bbb939241a54f9b9c343cf0c4c3c50e89b5fe2bb9a95bc126280752b8d7f04ca`.

Final retained health proves boot completion, stopped boot animation, Magisk
root, exact boot/vendor_boot/dtbo/recovery identities, final target/topology
continuity and absence of Download mode. `recovery_required=false`.

## Host finalization incident

No candidate or rollback was replayed. After the parser exception, an
exact-run host-only finalizer pinned the 1/1 transfer receipts, accepted
candidate proof, final raw health, identical rollback reads and
`ROLLBACK_FLASHED` journal. Independent review returned
`PASS_GO_P334_POSTROLLBACK_FINALIZER_H0`. Its first invocation appended only
the already-supported final-health and closure records; the same exception in
result validation then stopped before result publication. A second exact
CLOSED/result-only review returned
`PASS_GO_P334_CLOSED_RESULT_PUBLISHER_H0`; it published only the missing
canonical result and left state, journal, device and transfers unchanged.

Post-publication focused tests pass 3/3 and audit-only reconstruction returns
`CLOSED`, result present, zero device/ADB/USB/Odin/transfer action.

## Boundary

P3.34 is consumed and never replayable. This PASS proves the bounded two-
session authenticated fixed-command capability described above. It does not
grant an interactive PTY, caller-selected command, general shell, file
transfer, resident installation, persistent service, Max77705 causality or
standing device authority.
