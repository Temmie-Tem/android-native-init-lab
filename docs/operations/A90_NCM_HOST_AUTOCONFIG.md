# A90 NCM Host Autoconfig

Date: `2026-05-21`

이 문서는 native-init Wi-Fi 작업 중 큰 helper/증거 파일을 serial appendfile 대신 NCM 위 TCP 전송으로 처리하기 위한 host 설정 절차다.

## 기본 전제

- device NCM IP: `192.168.7.2`
- host NCM IP: `192.168.7.1/24`
- repo deploy 기본값: `scripts/revalidation/wifi_execns_helper_v12_deploy_preflight.py`는 `--transfer-method ncm`이 기본이다.
- 전송 원리: HTTP가 아니라 device `toybox netcat` listener와 host TCP socket send를 이용한 NCM bulk transfer다.
- 안전 범위: host IP 자동 설정만 다루며, Wi-Fi scan/connect/link-up/external ping과 무관하다.

## 현재 상태 확인

```bash
python3 scripts/revalidation/a90_ncm_host_preflight.py run
```

판정 기준:

- `a90-ncm-host-ready`: NCM candidate에 `192.168.7.1/24`가 있고 `192.168.7.2` ping이 통과했다.
- `a90-ncm-host-needs-address`: NCM candidate는 있지만 host IP가 없다. 아래 영구 설정을 적용한다.
- `a90-ncm-host-no-interface`: device NCM이 내려갔거나 USB 재열거가 안 됐다.
- `a90-ncm-host-address-present-ping-failed`: host IP는 있으나 device NCM state/cable/주소를 다시 확인한다.

검증기는 `/etc`를 수정하지 않는다. copyable template은 `tmp/host/a90-ncm-host-preflight/templates/` 아래에 만든다.

## 추천: udev + systemd-run

Kubuntu host는 보통 `NetworkManager`가 active이고 `systemd-networkd`가 inactive다. 이 경우 `systemd-networkd`를 새로 켜기보다 udev가 작은 root-owned helper를 호출하게 하는 방식이 충돌이 적다.

```bash
python3 scripts/revalidation/a90_ncm_host_preflight.py run

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
python3 scripts/revalidation/wifi_execns_helper_v66_deploy_preflight.py \
  --transfer-method ncm \
  preflight
```

NCM이 ready가 아니면 preflight evidence에 `a90_ncm_host_preflight.py` 판정이 같이 남는다. 느린 serial fallback은 의도적으로 필요할 때만 쓴다.

```bash
python3 scripts/revalidation/wifi_execns_helper_v66_deploy_preflight.py \
  --transfer-method serial \
  preflight
```

## 주의

- `192.168.100.1/24` 같은 다른 대역을 쓰려면 device IP도 같이 바꿔야 한다. 현재 repo 기본은 `192.168.7.1/24`와 `192.168.7.2`다.
- udev rule은 host IP만 설정한다. device NCM enable은 여전히 native command 또는 `ncm_host_setup.py setup` 흐름에서 처리한다.
- 이 설정은 Android Wi-Fi bring-up을 수행하지 않는다. 단지 host와 native init 사이 파일 전송 시간을 줄인다.
