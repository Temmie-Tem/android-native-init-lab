# S22+ mainline USB switch observation and Android return

The 2026-11-25 attended MAX77705 run on SM-S906N / g0q / FYG8 closed
`OBSERVED_MAX77705_USB_SWITCH` / `ANDROID_CLOSED_HEALTHY`. The retained
decoder and the final owner both returned `OPEN_THEN_OTHER_AFTER_ATTACH`.
The owner authenticated the mainline USB response and rederived the
observation at closure.

| Observer time from first observation sequence | CONTROL1 | Event |
| ---: | ---: | --- |
| 0.011 s | 0x3f | First read, switch open |
| 10.020 s | 0x3f | Periodic read |
| 14.504 s | 0x00 | VBUS and charger change flags |
| 17.564 s | 0x00 | Voltage ADC change flag |

The record contains seven events and four successful CONTROL1 samples.
It also reports three I/O errors. Later VBUS and charger change events
at 17.768 s and 17.971 s have no CONTROL1 sample. The change flags alone
do not identify which physical edge they represent. No read returned
`COM_USB` (`0x09`), and the switch state at enumeration is unknown.

The host issued the cue 22.21 s into the evidence window and recorded the
operator's completed replug at 32.45 s. In its own time base, the host port
monitor first saw the USB2 port powered at 29.29 s, then default at 29.49 s
and configured at 29.59 s. The SuperSpeed port stayed unattached throughout
the 200 s capture. The capture lists the cable type as unknown.

### Which side of the replug did the switch samples cover?

The [FYG8 field definitions](../../workspace/public/src/scripts/revalidation/s22plus_fyg8_p319_max77705_reg_stage_b_d0.py)
give a direction to the change flags. At 0.011 and 10.020 s the IC reported
VBUS present and CC sink (`BC_STATUS=0x82`, `CC_STATUS0=0xa1`). Both
registers read zero at 14.504 and 17.564 s, the two samples with
`CONTROL1=0x00`. The first sample showing VBUS present and CC sink again
was at 17.768 s. The two low samples were 3.060 s apart.
Both zero switch samples belong to the disconnected status, and there is
no successful switch sample after the return to sink. The decoder labels
the first VBUS or charger *change flag* an attach for its verdict; in this
trace that first flag accompanies the drop.

The 17.768 s and 17.971 s events fell 204 and 407 ms after the last switch
command sample, within the observer's one-second event-command spacing.
Both record `skipped`. Its idle-period read runs every ten seconds, and the
signed record was filled at 19.964 s. The FSA4480 failure mask was 0xff,
so its three reported bytes do not establish the companion switch state.

The host opened the authenticated request attempt at W+32.606 s and had
closed the exchange by W+32.769 s. The responder fills the signed record
between receiving that request and sending the response. Subtracting the
phone-side interval from 17.768 to 19.964 s places the first observed return
to sink at approximately W+30.41–30.57 s, without assigning an exact time
to insertion. The host kernel logged a new high-speed device at about
W+31.30 s. The host capture has no earlier enumeration error on this port.

The next read-only discriminator is a deferred CONTROL1 sample after the
observed VBUS-low to VBUS-high / CC-sink transition, respecting the existing
command spacing, and a switch sample at the authenticated request while USB
is known to work. A coincident gadget-controller state would help distinguish
switch routing from controller startup. Neither a register transition nor
a working USB exchange by itself proves that changing the switch is sufficient
for a cable-untouched boot.

### Return to Android

After the operator confirmed physical Download, the same owner restored
original Android once. The first final health check lost the ADB target.
A health-only continuation verified rooted Android, the original device and
USB topology, a changed boot ID and matching boot, dtbo, recovery and
vendor_boot digests. Candidate and original Android each transferred once.
The candidate and grant are consumed.

The private run directory is
`workspace/private/outputs/s22plus-max77705-usb-h0-20261125-1/`.
`task-1/closed.json` binds the terminal result, source snapshot, canonical
timeline and raw index. The host port samples and transition summary are in
`cue-dialog/host-port-watch/`.
