# Runtime Gate Rules

## Generic Module Gate

A module is usable only after all applicable gates pass in order:

1. `artifact`: exact module SHA256 and target kernel identity match.
2. `metadata`: hard dependencies and soft pre/post ordering are satisfied.
3. `insert`: `finit_module` succeeds, or an already-loaded state is proved.
4. `registration`: `/proc/modules` is read to EOF and contains the runtime name.
5. `match`: the expected DT/platform device exists and matches the driver.
6. `probe`: the driver/device bind symlink exists and probe did not defer/fail.
7. `surface`: the expected `/proc`, `/sys`, `/dev`, class, or protocol surface
   exists and behaves correctly.
8. `function`: a bounded end-to-end operation succeeds.

Failure at one gate stops interpretation at that gate. Source intent cannot be
promoted to runtime proof.

## Retention Gate

`sec_log_buf.ko` requires `registration -> platform bind -> /proc/last_kmsg and
/proc/ap_klog -> emit unique kmsg marker -> next-boot exact marker readback`.
`sec_debug.ko` is a separate optional panic-notifier/upload rung.

## USB Gate

The ordered USB bind gates are maintained in `subsystem-usb.md`. Host
enumeration without a device-reported bind bundle remains ambiguous.
