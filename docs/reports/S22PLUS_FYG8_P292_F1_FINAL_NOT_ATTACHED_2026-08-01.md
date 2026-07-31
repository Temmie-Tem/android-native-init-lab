# S22+ FYG8 P2.92 F1 Final Not-Attached Result

## Result

- Candidate run: `029c8b1739f06242008c0a7657cef9e2`
- Manifest: `s22plus-fyg8-p292-process-v2-ready-1`
- Process-v2 verdict: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`
- Outcome: `candidate_not_proven_rollback_verified`
- Transaction state: `CLOSED`
- Candidate transfers: exactly one
- Rollback transfers: exactly one
- Replay or retransmission: none
- Recovery required: no

The exact Magisk rollback restored Android, the FYG8 kernel, root, boot, and
the three bound supporting-partition identities. Final Android boot and boot
animation health passed and the Download endpoint was absent.

## Durable evidence

The host CDC-ACM observer timed out without accepting an endpoint. The two
rollback reads of `/proc/last_kmsg` are byte-identical and contain one exact,
integrity-clean P2.92 record:

```text
generation 105: stage 0x92, item 0, PROGRESS, detail 0
                final_sampling_started
generation 106: stage 0x92, item 1, FAILURE, detail 0x0d00
                final_result_classified
```

`0x0d00` is the first exact final-tuple value and decodes to:

```text
repair = power-helper-off-on-zero
bind   = direct-run-stop
state  = not attached
speed  = UNKNOWN
```

The result repairs the earlier observation deficit rather than proving E3
success. P2.84 through P2.90 stopped at generation 88 because the inherited
writer could accept but not resume a nonzero-detail progress slot. P2.92
resumed that exact state and advanced through every declared successor up to
the final classifier.

## Proven live prefix

Advancement through generations 89 through 106 proves all of these bounded
coordinates completed in program order:

1. the generation-88 suspended publication returned;
2. suspend returned and restart entered with a valid deadline;
3. the peripheral restart helper dispatched and returned;
4. the child became runtime-active;
5. the parent read back `peripheral`;
6. the exact real UDC membership check passed;
7. restart refresh, trace capture, and classification completed;
8. bind-cycle cleanup and bind-trace setup completed;
9. the configfs UDC write returned;
10. bind trace classification completed; and
11. final state/speed sampling ran to its classified result.

The restart classification is stronger than a zero-return helper alone. Its
authoritative trace requires the outer worker, child resume, FEMTO init, and
FEMTO power-on paths to enter and return zero; it also requires HSPHY
notify-connect, child active, parent peripheral, and exact UDC membership.
The selected repair class additionally requires the earlier power-off and the
later power-on helper to both return zero.

The bind class is also authoritative. Configfs pullup returned zero, the trace
observed direct `run_stop`, and `run_stop` returned zero. Diagnostic-degraded,
missing-run-stop, negative-return, and trace-source contradiction classes were
not selected.

## Failure boundary

After the successful restart and bind prefix, the final sampler waited for a
stable `configured` / `high-speed` pair. It never reached that pair. At the
30-second final deadline, two consecutive samples were stable at
`not attached` / `UNKNOWN`, producing terminal detail `0x0d00`. The independent
host observer endpoint timeout is consistent with that retained result.

This narrows the next question to the interval after successful direct
`run_stop` and before a physical UDC attach. It is no longer valid to attribute
the failure to the old generation-88 publisher, parent-suspend overlap,
restart-helper non-return, child resume, FEMTO init/power-on, notify-connect,
parent mode readback, exact UDC discovery, configfs bind return, or missing
direct run-stop.

## Limits

- Helper return zero proves the driver path result, not physical rail voltage.
- UDC membership proves the controller exists, not host electrical attach.
- Pullup/direct-run-stop return zero proves software completion, not that VBUS,
  cable state, PHY line state, or host enumeration followed.
- The operator's normal-boot/no-bootloop observation is supportive only; the
  formal result is the retained record plus verified rollback health.
- No conclusion is yet justified about the exact cause of `not attached`.

## Next H0 frontier

Analyze the post-bind attach boundary without another live run first. The next
host-only unit should correlate the authoritative bind trace semantics with
the DWC3/HS-PHY path that changes UDC state from `not attached`, and identify
which VBUS, cable, pullup, event-notification, or host-presence predicate can
remain false after direct `run_stop` returns zero. Any successor must preserve
the now-proven generation-88-through-106 prefix and add evidence only inside
that narrowed boundary.
