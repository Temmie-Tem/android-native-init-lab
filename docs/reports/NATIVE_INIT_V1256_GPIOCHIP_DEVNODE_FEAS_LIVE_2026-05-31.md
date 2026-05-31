# V1256 GPIOChip Devnode Feasibility Live

- report: `docs/reports/NATIVE_INIT_V1256_GPIOCHIP_DEVNODE_FEAS_LIVE_2026-05-31.md`
- runner: `scripts/revalidation/native_wifi_gpiochip_devnode_feas_live_v1256.py`
- evidence: `tmp/wifi/v1256-gpiochip-devnode-feas-live/manifest.json`
- result: `v1256-gpiochip-temporary-devnode-feasible`
- pass: `true`

## Scope

V1256 is read-only. It temporarily mounted debugfs, inspected `/dev`,
`/sys/class/gpio`, `/sys/bus/gpio/devices`, `/proc/devices`, and
`/sys/kernel/debug/gpio`, then unmounted debugfs and verified postflight
selftest. It did not create a device node, request a GPIO line, write
PMIC/GPIO/debugfs or regulator state, open `/dev/subsys_esoc0`, start PM/CNSS/HAL
actors, scan/connect, use credentials, DHCP/routes, external ping, reboot,
flash, boot image write, or partition write.

## Findings

| Field | Value |
| --- | --- |
| `/dev/gpiochip*` | absent |
| `/proc/devices` | `254 gpiochip` |
| PM8150L class chip | `/sys/class/gpio/gpiochip1263` |
| PM8150L class base | `1263` |
| PM8150L class label | `c440000.qcom,spmi:qcom,pm8150l@4:pinctrl@c000` |
| PM8150L class ngpio | `11` |
| PM8150L bus chip | `/sys/bus/gpio/devices/gpiochip2` |
| PM8150L bus dev | `254:2` |
| PM8150L bus uevent | `MAJOR=254`, `DEVNAME=gpiochip2` |
| debugfs gpio range | `gpiochip2: GPIOs 1263-1273, parent: platform/c440000.qcom,spmi:qcom,pm8150l@4:pinctrl@c000, c440000.qcom,spmi:qcom,pm8150l@4:pinctrl@c000:` |
| PMIC GPIO9 debug line | `gpio9 : out normal vin-1 pull-down 10uA push-pull high low atest-1 dtest-0` |
| feasibility candidate | `true` |
| cleanup | debugfs unmounted; selftest `fail=0` |

## Interpretation

V1256 closes the V1255 blocker. The kernel exposes gpiochip cdev metadata in
sysfs, but native `/dev` does not contain the corresponding nodes. For the
PM8150L chip, the safe candidate is a temporary `/dev/gpiochip2` node with
major/minor `254:2`, paired with the already proven debugfs range `1263-1273`
and PMIC GPIO9 offset `7`.

The next step is still not a GPIO line request. V1257 should be source/build-only:
extend helper support to materialize a private temporary `/dev/gpiochip2` node
from sysfs-provided `254:2`, open it read-only, run `GPIO_GET_CHIPINFO_IOCTL`,
print chip name/label/line count, and clean up. The helper must still print
`gpio_line_request_executed=0` and must not hold PMIC GPIO9.

## Safety

- read-only live classifier; temporary debugfs mount was cleaned up
- no `mknod`, GPIO line request, PMIC/GPIO/debugfs/regulator write, eSoC ioctl,
  PM actor, CNSS actor, Wi-Fi HAL, scan/connect, credentials, DHCP/routes,
  external ping, reboot, flash, boot image write, or partition write

## Next

V1257 should be helper v262 source/build-only for temporary gpiochip devnode
preflight support. V1258 can deploy it, and V1259 can run a bounded live
devnode-open proof without requesting a GPIO line.
