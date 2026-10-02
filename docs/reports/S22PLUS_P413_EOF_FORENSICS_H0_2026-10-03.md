# S22+ P413 rcS observation cutoff: retained-evidence H0 assessment

Date: 2026-10-03 KST. Target: `SM-S906N/g0q/S906NKSS7FYG8` only.

The retained evidence does **not establish the cause of P413's EOF**. It
establishes an observation cutoff after the authenticated rcS-entry record,
with host tty hangup symptoms. No production fix or new candidate is justified
as an EOF remedy from these inputs. This H0 unit sent zero device commands,
opened zero grants and built zero candidates. P413 remains consumed and closed
`ANDROID_CLOSED_HEALTHY`; A90 and S20+ were untouched.

## Inputs and last proved boundary

The [P413 physical-run report](S22PLUS_DEBIAN_HANDOFF_P413_FIRST_RUN_2026-10-03.md)
retains the installed-PID1 proof, original-A recovery and terminal health.
The frozen P413 source, authenticated prefix, capture, task, grant, closure
audit and terminal were read without changing their bytes. The private H0
evidence directory is
`workspace/private/outputs/s22plus-p413-eof-forensics-h0-20261003-1/`.

The actual source order after START is: rcS hook opens ACM, verifies installed
PID1, emits stage 1, closes fd 3, forks/executes rcS, waits, reopens ACM, then
emits stage 2. Stage 1 precedes both the close and the fork. Therefore it proves
neither completion of `close(3)` nor execution or completion of the rcS child.
There is no later authenticated STOP errno, runtime sample or boot identity.

The failed capture lasted 26,873 ms, with producer error `EOFError`, no returned
exit status, no timeout and no overflow. That capture duration includes the
preceding compound preparation; it is **not** an rcS duration or a measured
delay from stage 1 to EOF. P413 sent no release, NCM/SSH request or shutdown.

## Tests of the initial explanations

| Explanation | Retained or host-only evidence | Conclusion |
| --- | --- | --- |
| Missing host `CLOCAL` | P413 acquisition records `local_carrier=true`; the frozen opener sets and reads it back before handoff. | Not supported. |
| Last ACM close directly drops the entire USB gadget | The Samsung source and actual P413 Image show `gs_close` calling the gadget callback, which clears DSR/DCD and sends serial-state notification. That callback does not unbind the UDC. | A carrier change is possible; it is not proof of USB disconnection. |
| DCD falling necessarily hangs up this host tty | The installed module for host kernel `7.0.0-34-generic` copies CLOCAL into its ACM state and skips the DCD-triggered hangup when set. | Simple close-to-DCD-to-hangup is not an established cause. The loaded module's bytes and termios at the exact EOF instant were not captured. |
| An idle read is being mistaken for EOF | The frozen reader waits with `select`, retries `EAGAIN`/`EINTR` and treats an actual zero-byte read as EOF. A local raw nonblocking PTY with CLOCAL produced no readiness/EAGAIN while idle; peer hangup produced read-zero and `TIOCNXCL` EIO. P413 also recorded EIO when releasing exclusivity after EOF. | Consistent with tty hangup, not ordinary idle. PTY evidence does not reproduce USB hardware or identify the cause. |
| rcS explicitly reconfigures USB or reboots | Independent inspection of the exact installed scripts and RAM overlays found no selected direct UDC/gadget/reboot path. | No script correction is supported by this inspection. |
| Operator manipulation caused the initial cutoff | The operator reported no button or cable actions before the Download-recovery request. | The reported actions occurred afterward; this is operator evidence, not a kernel reset trace. |

The [upstream CDC ACM source](https://github.com/torvalds/linux/blob/master/drivers/usb/class/cdc-acm.c)
provides context for the CLOCAL guard. The conclusion above additionally uses
the matching installed host module's disassembly and the retained acquisition,
not an assumption that upstream source exactly identifies the running module.

The target Image contains both host and gadget ACM implementations. Its
unsuffixed `acm_disconnect` is the host driver; the relevant gadget callback is
`acm_disconnect.51494`. The verification script checks the actual allocation
callback assignment, `gs_close` call site, bit clearing and notification branch.
The correct gadget callback slice has SHA-256
`dd4952cf82b5c862e17fba5eeffc6daf1ebd2ddf496f512b405d22c6a450b998`.

## Exact startup-script assessment

The retained `.legacy-bootordering` selects sequential rcS execution. The
selected path includes mount setup, mdev, module/configuration scripts,
brightness, procps, urandom, networking and cleanup. The udev script exits
because its daemon is absent. Fstab, module lists and network-interface
fragments contain no selected mounts, modules or interfaces. Mdev rules have
no command hooks. These are source facts, not proof that those scripts ran on
P413 or that their kernel interactions cannot fail.

`mount-configfs` may add `/sys/kernel/config`; it performs no UDC or gadget
attribute write. The later rc2 `lab-usb` entry is overlaid by the fixed inert
deferred script. Existing `/run` is retained, and the prepared `.tmpfs` marker
makes bootclean skip `/run` until bootmisc removes the marker afterward. No
selected path was found that deletes the observer state directory.

The observer does have an unobserved interval while the script runs with ACM
closed. A script failure in that interval also lacks the open diagnostic fd
needed for useful STOP delivery. Keeping the parent descriptor open could be
considered for a **separately reviewed diagnostic change**, with child/service
descriptor isolation verified. It is not a demonstrated fix for P413's cutoff.

## Disposition and verification

The cause remains unresolved among a USB/session interruption, kernel/device
failure or another unrecorded tty transition. No later authenticated boot ID
distinguishes same-boot gadget loss from a reboot. Recovery USB receipts were
collected after the cutoff and the physical-recovery request; they cannot
retroactively identify its cause. No watchdog, panic or rcS-failure diagnosis
is asserted from timing or EOF alone.

H0 verification passed retained-input hashes, the actual Image symbol table
and gadget callback chain, the installed host module's CLOCAL guard, and the
local PTY behavior. The private verifier passed `py_compile` and execution.
An independent read-only assessment agreed with the no-fix conclusion. No
execution source, policy, approval, historical review, image, journal or
consumer acceptance rule changed; no build or device test was needed.

The next useful bounded development unit is an H0 design and qualification of
observations across the rcS close/fork/exec/wait boundary while preserving
service fd isolation, the original deadline and one-shot execution. Such a
candidate would improve diagnosis rather than claim the current cause solved.
EOF remains a stop; reconnecting or accepting it as progress is not justified.
Any later physical run needs its own current admission and authority. In
particular, native_data cleanliness remains **unproved after P413's writable
lifetime**; Android health does not renew P412's clean-root proof.
