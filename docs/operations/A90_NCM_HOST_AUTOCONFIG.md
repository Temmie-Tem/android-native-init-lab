# A90 NCM Host Autoconfig

Date: `2026-05-21`

이 문서는 native-init Wi-Fi 작업 중 큰 helper/증거 파일을 serial appendfile 대신 NCM 위 TCP 전송으로 처리하기 위한 host 설정 절차다.

## 기본 전제

- device NCM IP: `192.168.7.2`
- host NCM IP: `192.168.7.1/24`
- repo deploy 기본값: `workspace/public/archive/scripts/revalidation/wifi_execns_helper_v12_deploy_preflight.py`는 `--transfer-method ncm`이 기본이다.
- 전송 원리: HTTP가 아니라 device `toybox netcat` listener와 host TCP socket send를 이용한 NCM bulk transfer다.
- 안전 범위: host IP 자동 설정만 다루며, Wi-Fi scan/connect/link-up/external ping과 무관하다.
- `v725-fasttransport` 이후 계열은 IPv4 고정 주소 대신 USB NCM IPv6 link-local
  (`fe80::...%ncm0`)도 사용한다. 현재 transport selector는 Samsung
  `idVendor=04e8` + `driver=cdc_ncm`만 자동 후보로 인정하고, ASIX 등
  generic `cdc_ncm` USB NIC는 배제한다.

## 현재 상태 확인

```bash
python3 workspace/public/src/scripts/revalidation/a90_ncm_host_preflight.py run
```

판정 기준:

- `a90-ncm-host-ready`: NCM candidate에 `192.168.7.1/24`가 있고 `192.168.7.2` ping이 통과했다.
- `a90-ncm-host-needs-address`: NCM candidate는 있지만 host IP가 없다. 아래 영구 설정을 적용한다.
- `a90-ncm-host-no-interface`: device NCM이 내려갔거나 USB 재열거가 안 됐다.
- `a90-ncm-host-address-present-ping-failed`: host IP는 있으나 device NCM state/cable/주소를 다시 확인한다.
- IPv6 link-local 전송 runner에서는 `a90-ncm-host-needs-address`가 곧바로
  실패를 의미하지 않을 수 있다. 현재 selector는 별도로 host `fe80::`, device
  `ncm0` reachability, device-to-host TCP probe를 확인한다.

검증기는 `/etc`를 수정하지 않는다. copyable template은 `tmp/host/a90-ncm-host-preflight/templates/` 아래에 만든다.

## 추천: udev + systemd-run

Kubuntu host는 보통 `NetworkManager`가 active이고 `systemd-networkd`가 inactive다. 이 경우 `systemd-networkd`를 새로 켜기보다 udev가 작은 root-owned helper를 호출하게 하는 방식이 충돌이 적다.

```bash
python3 workspace/public/src/scripts/revalidation/a90_ncm_host_preflight.py run

sudo install -m 0755 \
  tmp/host/a90-ncm-host-preflight/templates/a90-ncm-up.sh \
  /usr/local/sbin/a90-ncm-up

sudo install -m 0644 \
  tmp/host/a90-ncm-host-preflight/templates/90-a90-ncm.rules \
  /etc/udev/rules.d/90-a90-ncm.rules

sudo udevadm control --reload-rules
```

적용 후에는 A90 USB를 재연결하거나 NCM을 재시작한다. 즉시 적용이 필요하면 현재 interface명을 확인한 뒤 한 번만 실행한다.

```bash
ip -br link
sudo /usr/local/sbin/a90-ncm-up enx...
ping -c 3 -W 2 192.168.7.2
```

## v725 권장: NetworkManager link-local profile

재플래시/재부팅 뒤 host ifname은 `enx...` 형태로 바뀔 수 있다. ifname을
고정값으로 보지 말고, `udevadm`/sysfs에서 Samsung `04e8:6861` 및
`cdc_ncm` driver로 현재 interface를 찾는다.

```bash
IFACE="$(
  for devpath in /sys/class/net/*; do
    dev=${devpath##*/}
    driver=$(basename "$(readlink -f "$devpath/device/driver" 2>/dev/null)" 2>/dev/null)
    [ "$driver" = "cdc_ncm" ] || continue

    props=$(udevadm info -q property -p "$devpath" 2>/dev/null)
    echo "$props" | grep -qx 'ID_USB_VENDOR_ID=04e8' || continue
    echo "$props" | grep -qx 'ID_USB_MODEL_ID=6861' || continue
    echo "$dev"
    break
  done
)"

if [ -z "$IFACE" ]; then
  echo "ERROR: A90 NCM interface not found"
  exit 1
fi

old_conn="$(nmcli -g GENERAL.CONNECTION device show "$IFACE" 2>/dev/null | head -n1)"
if [ -n "$old_conn" ] && [ "$old_conn" != "--" ] && [ "$old_conn" != "a90-v725-ncm-bench" ]; then
  sudo nmcli connection modify "$old_conn" connection.autoconnect no || true
  sudo nmcli connection down "$old_conn" || true
fi

sudo nmcli connection delete a90-v725-ncm-bench 2>/dev/null || true
sudo nmcli connection add type ethernet con-name a90-v725-ncm-bench ifname "$IFACE" \
  ipv4.method disabled \
  ipv6.method link-local \
  ipv6.addr-gen-mode stable-privacy \
  connection.autoconnect yes
sudo nmcli connection up a90-v725-ncm-bench
```

확인:

```bash
nmcli -f GENERAL.STATE,GENERAL.CONNECTION,IP6.ADDRESS device show "$IFACE"
ip -6 addr show dev "$IFACE" | grep 'fe80::'
```

현재 `a90_transport.select_transport()`는 위 동작을 one-shot repair로
내장한다. 조건은 A90 NCM interface가 존재하지만 host `fe80::`가 없는
경우다. 자동 복구를 끄고 host 상태를 그대로 관찰하려면:

```bash
A90_TRANSPORT_AUTO_REPAIR_NCM=0 python3 ...
```

`FastTransferSession`도 동일한 NetworkManager repair helper를 사용한다.

## 대안: systemd-networkd

host가 이미 `systemd-networkd`로 USB NIC를 관리하는 구성일 때만 사용한다. `NetworkManager`가 active인 Kubuntu에서 무리하게 enable하지 않는다.

```bash
sudo install -m 0644 \
  tmp/host/a90-ncm-host-preflight/templates/90-a90-ncm.network \
  /etc/systemd/network/90-a90-ncm.network

sudo systemctl enable --now systemd-networkd
```

## 대안: sudoers NOPASSWD

자동 네트워크 관리 대신 수동 one-shot을 빠르게 만들 때만 사용한다. wildcard로 `/usr/sbin/ip`를 직접 허용하지 말고, 검증된 wrapper 하나만 허용한다.

```bash
sudo install -m 0755 \
  tmp/host/a90-ncm-host-preflight/templates/a90-ncm-up.sh \
  /usr/local/sbin/a90-ncm-up

sudo install -m 0440 \
  tmp/host/a90-ncm-host-preflight/templates/a90-ncm-sudoers \
  /etc/sudoers.d/a90-ncm

sudo visudo -cf /etc/sudoers.d/a90-ncm
```

## Deploy 사용 방식

NCM이 ready면 helper deploy는 명시적으로 NCM을 사용한다.

```bash
python3 workspace/public/archive/scripts/revalidation/wifi_execns_helper_v66_deploy_preflight.py \
  --transfer-method ncm \
  preflight
```

NCM이 ready가 아니면 preflight evidence에 `a90_ncm_host_preflight.py` 판정이 같이 남는다. 느린 serial fallback은 의도적으로 필요할 때만 쓴다.

```bash
python3 workspace/public/archive/scripts/revalidation/wifi_execns_helper_v66_deploy_preflight.py \
  --transfer-method serial \
  preflight
```

## 주의

- `192.168.100.1/24` 같은 다른 대역을 쓰려면 device IP도 같이 바꿔야 한다. 현재 repo 기본은 `192.168.7.1/24`와 `192.168.7.2`다.
- udev rule은 host IP만 설정한다. device NCM enable은 여전히 native command 또는 `ncm_host_setup.py setup` 흐름에서 처리한다.
- 이 설정은 Android Wi-Fi bring-up을 수행하지 않는다. 단지 host와 native init 사이 파일 전송 시간을 줄인다.
- udev rule은 `DRIVERS=="cdc_ncm"`, `ATTRS{idVendor}=="04e8"`,
  `ATTRS{idProduct}=="6861"`처럼 A90 쪽으로 좁힌다. `driver=cdc_ncm`
  단독 매칭은 다른 USB NIC까지 잡을 수 있다.
