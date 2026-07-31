# A90 resident promotion guard corridor independent review

Independent verdict: GO

Unresolved blocking findings: 0

Device actions: none

## Reviewed snapshot

- orchestrator: `27326f21928776d1da4b38298497148c77a4193df8716824305eae0a6416ee17`
- resident promotion: `0e18d50ee059419b273f7af9d3735e8ac8c5ee49c825973f3c36f1adcc7a13c8`
- CDC ACM guard: `6c8a6d2151928d2e098ca41b3c9dc24cdbbfabe9be10df19969be274744ef9a9`
- Phase 2C contract: `2721a65246d92a52725ea8713444e94f103e824b90fdd94555fd3e945b9a102a`

## Findings closed during review

The review required the recovery path to derive the exact guard identity from
durable evidence rather than a currently present ACM node, moved guard-property
proof ahead of every framed settle or health command, and made guard-arm
evidence journal-bound. It also required bounded recovery leases for arm-only
crashes, exact success and failure release receipts, and rejection of stale or
dangling runtime rules.

Rollback authority was separated from observer cleanup: exact adb-recovery can
still perform the pre-authorized rollback if the guard is unavailable, while
unguarded from-native commands and unguarded final health remain forbidden.
Terminal close now follows successful guard release, and a release failure is
left as bounded recoverable state rather than a false close.

The final lifetime audit counted every remote command, the fixed 30-second
bridge preflight floor, six success-path bridge preflights, two complete
155-second NCM slow-success paths, and rollback-source/final-health work. This
removed defaults that had only hidden smaller-timeout under-budgeting.

## Independent validation

- Independent related regression: `268/268` PASS.
- Phase 2C packet: `6/6` PASS.
- Python compilation: PASS.
- `git diff --check`: PASS.
- All four final SHA256 identities were rechecked after the tests with no
  drift.
- Device contact, transfer, flash, and reboot: none. No other device was
  touched.

The review authorizes host-side closure of this implementation unit only. It
does not grant F1 or other live-device authority.
