# A90 H17 tcpctl normal-idle-exit health observer incident

Date: 2026-08-11
Target: operator-owned Samsung Galaxy A90 5G only
Incident: `H17_TCPCTL_NORMAL_IDLE_EXIT_HEALTH_OBSERVER`

## Result

The first approved H17 native-fallback finalizer attempt sent only bounded
read-only resident commands and stopped before either terminal host record.
Exact H17 identity, self-test `11/1/0`, PID 1 guard `12/0/0`, native HUD,
serial control, USB NCM, and the consumed `binding=1 enable=1 latch=1` state
remained present. The only rejected marker was
`transport.tcpctl=starting` instead of `transport.tcpctl=ready`.

The same current H17 boot log proves one tcpctl child was spawned and reached
its authenticated listener, then much later the same child was reaped with
`status=0x0` and `netservice: tcpctl exited`. No later tcpctl start exists
in that boot segment. The compiled configuration gives tcpctl a 3600-second
idle limit and unlimited client count. Source inspection confirms that the
status path reaps a finished child but does not restart it; with netservice
still enabled it therefore reports `starting` indefinitely.

## Safety disposition

This is an observer-predicate incident, not a handoff, UFS, resident, or
device-control failure. The serial bridge and USB NCM control path remain
ready, self-test and PID 1 guard remain exact, and the tcpctl child exited
normally after exceeding its configured idle interval. The failed finalizer
attempt wrote no journal record and sent no arm, reboot, handoff, mount,
service-control, payload, flash, state-clear, or userdata-write command.

The old finalizer qualification is retired because it assumed tcpctl must
remain running indefinitely. It may be replaced only by a fresh independently
reviewed closure that distinguishes these two exact native-health cases:

- tcpctl is currently ready; or
- serial and NCM are ready while the same latest H17 boot proves one
  same-child tcpctl start followed by a zero-status reap and exit after at
  least the configured idle interval, with no later start.

The second case must explicitly report tcpctl as not running. It establishes
native resident safety and available serial/NCM recovery control only; it does
not prove persistent TCP control, Debian, SSH, server readiness, display,
Wi-Fi, or a successful `switch_root`.

## Successor boundary

No live service restart is authorized by this incident. A later boot candidate
may add a bounded tcpctl supervisor or change the idle policy, but that is a
separate capability and cannot be smuggled into the read-only H17 close.
S22+ evidence, commands, approvals, artifacts, and recovery remain outside
scope and untouched.
