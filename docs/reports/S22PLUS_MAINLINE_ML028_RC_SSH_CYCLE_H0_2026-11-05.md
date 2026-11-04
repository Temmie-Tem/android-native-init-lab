# ML028: Debian rc-managed SSH service cycle in RAM (H0)

ML027 physically established normal Download and original Android return.
ML028 asks whether Debian's packaged rc scripts can start SSH, serve one
unprivileged request, and stop that same service before normal Download.
This report covers host qualification; it does not record an ML028 S22+ boot.

Claude and Argon each critiqued and challenged the next unit. Both selected
the rc-managed RAM service over enabling a watchdog or starting UFS work.
The current Gunyah watchdog driver stops the watchdog at probe and registers
a restart path; enabling it is not a read-only query. The board UFS reset,
pin controller, supplies and PHY are a separate integration task. Neither
is required to answer the selected service question. The ML027 property-read
failure remains undiagnosed; no generic scope expansion follows from it.

## What counts as a service cycle

The candidate uses the same kernel configuration, DTB and PHY change as
ML027, with a freshly built kernel bound to this candidate. It uses 28
signed Debian packages and 34 selected package members. Packaged SysVinit
is initial PID 1; packaged rc2 dispatches the start script, with the master
identified by executable, PID and start ticks. After any issued replug cue
is resolved, one host-key-pinned SSH session runs a fixed command as
UID/GID 1000 with no effective capabilities. One authenticated request on
the still-open base socket asks PID 1 to enter runlevel 6. Packaged rc6
dispatches the stop script against the original master.

A successful shell exit does not establish service shutdown. The observer
also requires both same-boot stage records, disappearance of the original
master and pidfile, and no process with one of the three packaged SSH
executables at the final check. Its 168-byte ACK precedes the peer-EOF
and final clock/driver checks for normal Download. Only actual Download
arrival, original A and complete Android health can finish the physical
experiment. Every uncertain send remains consumed.

## Evidence and limits

- The exact new kernel and VM archive ran the entire packaged cycle. The
  authenticated stop and rc6 completion were recorded at 3.048 and 3.061
  seconds of guest uptime, followed by one guest reset in QMP. The model has
  no Samsung PMIC; it cannot prove Download arrival on the phone.
- The wrong initial request key, six control/EOF cases and six SSH
  restriction cases behaved as expected. After a valid stop, extra bytes
  or a missing final EOF can leave SSH stopped but cannot authorize reset.
- Seven separate fault archives exercised masked start/stop success, a stale
  pidfile, an invalid start record, duplicate stop intent, missing stop record
  and a telinit that exits zero without a transition. None obtained a stop ACK
  or guest reset. The production validator rejected each archive. An earlier
  altered-inittab fixture failed the genuine base identity check; its raw
  evidence was preserved separately and was not counted as a transition test.
- Independent interim review identified a Python type alias in the effect
  declaration and incomplete VM producer/command joins. The fixed checks
  reject boolean/float substitutions and ten rebound capture mutations,
  including missing producer sources and a changed QEMU kernel or initramfs.
  All thirteen complete control/SSH captures were rederived. Raw producer
  provenance remains the original snapshot; the current checker did not
  recreate those captures.
- 178 focused mainline tests and 21 Session tests passed, including loopback
  tests of the physical host path. An SSH failure sent zero controls; an ACK
  for a different master preserved independently proved SSH and could not
  produce service success. The physical readiness/deadline/returning-syscall
  fixtures and loader, entry, marker and boot-package checks also passed.

This bounds one service, its observed process state and one normal return.
It does not establish full system shutdown, signal causality, automatic
recovery after failure, persistent Debian, Linux storage or general remote
access. A90 and S20+ are outside this work. ML027 and all prior operations
remain consumed. Fresh finite attended approval and usable physical Download
recovery are still required by the [mainline policy](../operations/S22PLUS_MAINLINE_RAM_V1.md).

## Prepared state

The independent review returned `PASS_GO` with no findings for this exact
candidate, reachable capability and V33 backend. Both complete recorded-key
producer reproductions matched the original seals, package locks, observer
ELFs and CPIOs. The stable worker did not change. The real image and task
passed preparation with acquisition blocked; twelve changed admission inputs
were rejected. The named preapproval D0 then verified seven successful raw
Android health captures for the bound target and original A. There was no
unresolved F1 owner, operator approval, grant, transfer or experimental
control. This is a qualified proposal, not execution authority.
