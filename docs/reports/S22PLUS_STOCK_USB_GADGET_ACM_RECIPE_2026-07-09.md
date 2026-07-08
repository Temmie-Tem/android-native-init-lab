# S22+ Stock USB Gadget ACM Recipe (live read-only extract, 2026-07-09)

Operator (Claude) read-only pull from the live rooted device (Android baseline,
Magisk root) of the stock USB gadget configuration — the runtime "execution
recipe" analog to `modules.dep`. No writes, no flash. Serials shown as
placeholders; raw dumps stay uncommitted in scratchpad.

## The stock gadget is exactly what we need — `ss_acm` is a first-class function

`/config/usb_gadget/g1` (the live, bound gadget):

```text
UDC        = a600000.dwc3          # == ro.boot.usbcontroller == /sys/class/udc
max_speed  = super-speed-plus      # gadget-level speed (see divergence below)
idVendor   = 0x04E8   idProduct = 0x6860   bcdUSB = 0x0320  bcdDevice = 0x0504
```

`/sys/class/udc/` = `a600000.dwc3` and `dummy_udc.0` (bind the real one, never the
dummy). The stock function pool includes **`ss_acm.0`** (the `usb_f_ss_acm`
function) with attribute `port_num`, and the **active config `b.1` links it as
`f2`**:

```text
configs/b.1/f1 -> functions/ffs.mtp
configs/b.1/f2 -> functions/ss_acm.0     ← ACM serial, live in the stock composition
configs/b.1/f3 -> functions/conn_gadget.0
configs/b.1/f4 -> functions/ffs.adb
configs/b.1/f5 -> functions/ss_mon.mtp
```

So Samsung's own stock USB stack runs `ss_acm` alongside mtp/adb — **the ACM
function binds and enumerates fine on this exact controller**, which means our
approach (expose `ss_acm` → `/dev/ttyGS0`) is on-recipe, not exotic.

## The exact stock create/bind order (`/vendor/etc/init/hw/init.qcom.usb.rc`)

Gadget bring-up sequence (composition change is unbind → relink → rebind):

```text
mount configfs none /config
mkdir /config/usb_gadget/g1  (+ strings/0x409)
write  g1/bcdUSB 0x0200                     # created as USB 2.0
write  g1/os_desc/use 1
write  g1/strings/0x409/{serialnumber,manufacturer,product}
mkdir  g1/functions/ss_acm.0                # the ACM function
mkdir  g1/configs/b.1  (+ strings/0x409)
write  g1/configs/b.1/MaxPower 900
# --- composition select (per sys.usb.config) ---
write  g1/UDC "none"                        # UNBIND first
write  g1/idVendor  0x04E8
write  g1/idProduct 0x6860
symlink g1/functions/ss_acm.0  g1/configs/b.1/f2   # LINK function into config
write  g1/UDC ${sys.usb.controller}         # BIND = pullup  (== a600000.dwc3)
```

Key invariants:
- **UDC name = `a600000.dwc3`** (from `sys.usb.controller` / `ro.boot.usbcontroller`).
- **Order: unbind (`UDC none`) → set IDs → symlink function(s) → write UDC (bind).**
  The UDC write is always LAST and is the pullup.
- **Stock does NOT set `dr_mode`/`usb_role`/mode in the rc.** `dwc3 dr_mode=otg`
  is resolved by the **TypeC/PD hardware negotiation** (the `usb_typec_manager`/
  `pdic`/MUIC stack + a real cable), which decides peripheral vs host.

## Minimal stock-aligned ACM recipe for native init (M34)

```text
mount -t configfs none /config
mkdir /config/usb_gadget/g1 ; mkdir g1/strings/0x409
write g1/bcdUSB 0x0200
write g1/idVendor 0x04E8 ; write g1/idProduct <pick>
write g1/strings/0x409/{serialnumber,manufacturer,product}
mkdir g1/functions/ss_acm.0
mkdir g1/configs/b.1 ; mkdir g1/configs/b.1/strings/0x409
write g1/configs/b.1/MaxPower 900
write g1/UDC "none"
symlink g1/functions/ss_acm.0 g1/configs/b.1/f1
write g1/UDC a600000.dwc3        # pullup -> expect /dev/ttyGS0
```

## Two off-stock divergences — and they are exactly the M34 suspects at pullup

Everything above is on-stock. Our HS-only, PD-less native init diverges in
precisely the two places the ~35 s M32 hang most likely lives — both at **UDC
pullup**:

1. **`max_speed`.** Stock leaves `g1/max_speed = super-speed-plus` because it has
   the QMP SS phy powered. We run **HS-only (no QMP)**. Writing UDC at
   super-speed-plus with no SS phy may drive dwc3 into an SS connect/PHY sequence
   that hangs. **Fix to try first (pure configfs, no DT): `write g1/max_speed
   high-speed` before the UDC write.** This is the cheap HS-only lever the live
   read revealed — separate from the DT `maximum-speed` and from any DTBO surgery.
2. **Role / `dr_mode=otg`.** Stock relies on **PD/TypeC hardware negotiation** to
   put dwc3 in peripheral mode; the `write UDC` then completes as a device. Our
   native init has the TypeC/PD *modules* loaded (P28 proved they park fine) but
   **no live PD negotiation**. At UDC pullup, dwc3 in `otg` may sit waiting for a
   role or mis-drive the OTG state machine → hang. **Levers to try:** force
   peripheral via `usb_role` sysfs (`/sys/class/usb_role/*/role = device`) or the
   dwc3 `mode` sysfs, before/around the UDC write; if that is insufficient,
   `dr_mode = peripheral` in the DTBO.

## Recommended M34 sequencing (isolates which divergence bites)

From the proven 44-module park floor, do the configfs recipe with a dwell/marker
between the two divergence knobs:
1. Build the gadget + link `ss_acm` (no UDC), park — expect survive.
2. `write g1/max_speed high-speed`, `usb_role=device`, park — expect survive.
3. `write UDC a600000.dwc3` (pullup), park + host-scan for `/dev/ttyGS0`.
   - Enumerates ⇒ done (ACM up, HS-only, no DT surgery).
   - Hangs ⇒ the pullup is the wall; bisect max_speed vs role by toggling one at a
     time; only then consider `dr_mode=peripheral` DTBO (needs a real FDT tool,
     per the DTBO-mechanics finding).

The live read confirms the recipe is stock-faithful except for these two
HS-only/PD-less knobs, so M34 should encode the stock order verbatim and treat
`max_speed=high-speed` + `usb_role=device` as the two variables under test.

## Discipline

Read-only device pull (getprop / cat configfs / cat rc); no writes, no flash.
Raw dumps (which contain the real serial) remain uncommitted in scratchpad; this
report uses placeholders. Any native-init candidate + live test needs the usual
fresh SHA-pinned boot(+DTBO) exception. Device left untouched on the clean Magisk
baseline.
