# Server-Distro Wi-Fi STA Upstream Rung

- Date: 2026-07-04
- Status: HOST-SIDE DESIGN
- Scope: next hardware rung after the Stage0 server-distro hardware contract.
- Device action in this doc: none.

## 0. Goal

Make the D4/D-public Debian appliance reach upstream internet through the phone radio as a
Wi-Fi station, without depending on the host USB/NCM network for public tunnel traffic.

The target flow is:

```text
native init wakes qcacld enough for wlan0
  -> switch_root to Debian
  -> Debian starts STA supplicant + DHCP from private config
  -> Debian route/tunnel uses wlan0
  -> USB NCM remains the recovery/admin path
```

This is the server-appliance rung. It is not a demo workload and it is not SoftAP
concurrency.

## 1. Ground Truth Already Proven

- V2237 proved the older Wi-Fi lineage can associate, DHCP, and externally ping on both
  bands with private credentials.
- V3342 proved the current post-GPU/server lineage can materialize `wlan0` again by using
  the mounted-vendor QCACLD firmware source route:
  `source_policy=qcacld-fwsource-mounted-vendor-first`, `wlan0_present=1`, and
  `decision=softap-iftype-probe-pass`.
- V3344 proved SoftAP/server mode, but that is a private AP transfer endpoint. It does not
  prove upstream internet for the Debian appliance.
- The Stage0 hardware contract assigns native init only the `wlan0` materialization
  responsibility. Debian owns IP config, route policy, and the public tunnel after
  handoff.

## 2. Ownership Boundary

| Surface | Native init owns | Debian owns |
| --- | --- | --- |
| `wlan0` creation | Yes: qcacld/vendor firmware/service glue. | No. Debian consumes the interface after it exists. |
| STA supplicant | No by default. Native may run bounded tests only. | Yes: long-lived station supplicant after handoff. |
| DHCP / DNS / default route | No by default. Native may run bounded tests only. | Yes: Debian applies upstream route policy. |
| USB NCM | Preserve kernel gadget and local admin route. | May use for admin, must not break recovery. |
| Public tunnel | Never. | `cloudflared` or later tunnel client, outbound-only. |

Native child processes must not silently linger across `switch_root` to own Wi-Fi. If a
temporary native Wi-Fi worker is used for a probe, it must be stopped before handoff.

## 3. Debian Rootfs Requirements

The current server-distro rootfs builder includes `iproute2` and `iputils-ping`, but not a
Debian STA client stack. The STA rung should add, source-side first:

- `wpasupplicant` for the long-lived Debian station process;
- one DHCP client path, preferably `isc-dhcp-client` for a conventional Debian userspace;
- one outbound TCP probe path, currently `netcat-openbsd`, so DHCP/default-route success
  cannot masquerade as real upstream reachability;
- a firstboot opt-in script path under `/etc/a90-dpublic/` that starts STA only when the
  operator has staged private config;
- marker fields in `/run/a90-d3-marker` for route ownership and redacted status.

Credentials must stay in private runtime/config state. Public repo artifacts may record only
booleans, redacted profile labels, return codes, and `secret_values_logged=0`.

## 4. Rung Plan

### WSTA0: design lock

This document. No device action.

### WSTA1: Debian STA client source unit

Add rootfs/client support without starting Wi-Fi by default:

- include `wpasupplicant` and one DHCP client in the rootfs builder;
- add `/usr/local/bin/a90-dpublic-wifi-sta` or an equivalent firstboot helper;
- firstboot runs it only when `/etc/a90-dpublic/wifi-sta-enable` exists and a private
  config file is present;
- output is redacted and marker-only;
- tests prove default D-public boot still does not start STA or cloudflared.

No boot image flash is required for this source unit.

### WSTA2: native materialization live gate

Build/flash the exact current native candidate through `native_init_flash.py` only if a new
boot artifact is needed. Validate below association:

- `server-distro hardware-contract` prints `next.required=wifi-sta-upstream`;
- `wifi status` or a bounded no-start probe reaches `wlan0_present=1`;
- no native STA supplicant, DHCP, ping, AP, NAT, or listener remains running;
- `selftest fail=0`.

If `wlan0` does not appear after the bounded window, stop the rung and do not continue into
Debian STA or public tunnel checks.

### WSTA3: Debian STA association + route live gate

With private operator-provided config staged into the userdata appliance:

- boot into Debian PID1;
- firstboot starts Debian `wpa_supplicant` for `wlan0`;
- DHCP obtains an address and DNS without logging concrete private network identifiers in
  public artifacts;
- default route for outbound internet becomes Wi-Fi while USB NCM remains reachable for
  local admin/recovery;
- marker/status proves `wifi_sta_default_route_iface=wlan0`, `ncm_recovery_preserved=1`,
  gateway ARP resolution, DNS resolution, and outbound TCP/443 reachability.

This gate is blocked, not failed, when credentials are absent.

### WSTA4: D-public over Wi-Fi

Only after WSTA3 passes:

- start the D-public smoke service locally;
- start `cloudflared` only from Debian and only when explicitly enabled;
- confirm the tunnel's outbound route is `wlan0`;
- confirm smoke response through the tunnel;
- cleanup/disable leaves no stale tunnel runtime and no secret/public URL in git.

## 5. Stop Conditions

Stop before mutation or public exposure if any condition appears:

- rollback images or recovery/TWRP preconditions are missing before a flash;
- `wlan0` does not materialize in the bounded native gate;
- Debian STA tooling is missing from the rootfs;
- private credentials are absent for an association gate;
- USB NCM admin/recovery is lost;
- any path requires modem/cellular, PMIC/regulator/GDSC/GPIO/backlight writes, inbound public
  ports, NAT export, or SoftAP+STA concurrency.

## 6. Explicit Non-Goals

- Do not reopen modem/cellular upstream.
- Do not require SoftAP+STA concurrency for the server appliance.
- Do not make Wi-Fi a hard blocker for local USB/NCM recovery or userdata handoff.
- Do not start public exposure from native init.
- Do not commit SSID, PSK, BSSID, MAC, DHCP lease, concrete private IP, or public tunnel URL.

## 7. Next Implementation Unit

Implement WSTA1 as a source-only rootfs/firstboot change:

1. add the Debian STA packages to `build_debian_aarch64_rootfs.py`;
2. add an opt-in D-public STA helper called from firstboot;
3. add a real L3 reachability gate so DHCP/default-route alone cannot return `wifi-sta-pass`;
4. update GOAL/report with no device action.
