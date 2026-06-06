# Revalidation Scripts

이 디렉토리는 legacy/historical revalidation tree입니다. 현재 baseline에서
승격된 entrypoint는 `workspace/public/src/scripts/revalidation/` 아래에 두고,
여기에는 기존 명령 호환 wrapper와 아직 마이그레이션하지 않은 의존 모듈을 남깁니다.

현재 디렉토리는 rooted baseline과
`native Linux rechallenge` 전단계인 부트체인 재검증에 직접 필요한 스크립트만 두는 자리입니다.

현재 포함 범위:

- `verify_device_state.sh`
  - `adb devices`
  - `sys.boot_completed`
  - `su -c id`
  - 기본 verified boot 관련 prop
  - 필요 시 Wi-Fi 상태
- `capture_baseline.sh`
  - 현재 `boot`, `recovery`, `vbmeta` 백업
  - `getprop`, root 상태, Wi-Fi 상태 저장
  - 다운로드 모드 수동 기록용 노트 템플릿 생성
- `serial_tcp_bridge.py`
  - host의 `/dev/ttyACM0` 또는 `/dev/serial/by-id/...`를
    `127.0.0.1:<port>`로 노출하는 최소 브릿지
  - USB ACM shell을 TCP 클라이언트 한 개로 전달
  - serial 재연결 시 자동 재오픈
  - v48 이후 USB 재열거로 device node identity가 바뀌면 stale fd를 닫고 재연결
  - Batch 3 이후 첫 연결 realpath를 pinning하고, `--expect-realpath`로 특정 serial node를 고정 가능
  - `--device=auto`에서 여러 Samsung ACM 후보가 보이면 기본적으로 거부
  - 빠른 개발용 게이트 용도
- `serial_console.py`
  - 위 브릿지에 붙는 interactive console client
  - raw shell 출력은 그대로 보여주되, `waitkey`/`blindmenu`/`key ...` 같은
    라인을 `[watch]` 메모로 한 번 더 띄워서 버튼 입력을 더 눈에 띄게 보여줌
  - `Ctrl-]` 로 로컬 콘솔만 종료 가능
- `a90ctl.py`
  - v73 `cmdv1`/`A90P1` framed shell protocol을 쓰는 one-shot host wrapper
  - bridge 출력에서 END marker를 파싱해 `rc`/`status`를 판정
  - `--json`, `--allow-error`, `--hide-on-busy`를 지원
  - bridge가 먼저 열리고 ACM serial이 늦게 붙는 재부팅 구간은 timeout 안에서 재시도
  - v74부터 whitespace/empty/`#` 시작 인자는 `cmdv1x <len:hex-utf8-arg>...`로 자동 인코딩
  - 단순 whitespace-free 인자는 기존 `cmdv1 <command> [args...]` wire format 유지
  - Batch 3 이후 자동 재시도는 관찰 명령 allowlist에만 적용하고, 그 외 명령은 `--retry-unsafe`가 필요
  - Batch 3 이후 child output의 가짜 `A90P1 END`는 real trailer/prompt와 sequence matching으로 걸러냄
- `a90_broker.py`
  - v186 `A90B1` host-local broker skeleton
  - private Unix socket endpoint를 만들고 여러 host client request를 single worker queue로 직렬화
  - backend `acm-cmdv1`는 기존 `a90ctl.run_cmdv1_command()`를 사용해 USB ACM bridge에 명령을 전달
  - backend `ncm-tcpctl`는 `run /absolute/path ...` 요청을 NCM `a90_tcpctl`로 보내고, native shell built-in은 ACM fallback으로 처리
  - v193부터 `ncm-tcpctl --no-auth`는 `--allow-no-auth`가 같이 있어야만 허용되며, broker metadata/audit/error는 token 값을 redaction한다
  - backend `fake`와 `selftest`로 request id, observe command, rebind/destructive block 동작을 로컬 검증
  - `reboot`/`recovery`/`poweroff` 같은 rebind/destructive command는 broker multiplex 대상이 아니며 foreground raw-control 경로를 유지
  - audit JSONL은 private/no-follow helper를 통해 owner-only 파일로 남기고, v188 `report`로 integrity/summary/redacted records를 생성
- `a90_broker_concurrent_smoke.py`
  - v189 broker concurrent smoke validator
  - 여러 host client가 동시에 `A90B1` request를 보내도 broker가 single worker queue로 backend command를 직렬화하는지 검증
  - `fake`와 `acm-cmdv1` backend를 지원하고, 선택적으로 blocked `reboot` request가 `operator-required`로 남는지 확인
  - summary/response/audit evidence는 private/no-follow output helper로 `tmp/a90-v189-*` 아래에 저장
- `a90_broker_mixed_soak_gate.py`
  - v190 broker-backed mixed-soak gate
  - broker subprocess를 실행한 뒤 `native_test_supervisor.py mixed-soak`을 `--device-backend broker`로 구동
  - supervisor manifest와 broker audit integrity/count/status를 함께 판정
  - 기본 workload는 `cpu-memory-profiles`라 observer와 workload command가 모두 broker를 통과
- `a90_broker_recovery_tests.py`
  - v192 broker failure/recovery validator
  - blocked command audit, broker restart stale socket recovery, stale non-socket refusal을 fake backend로 검증
  - `--include-live` 사용 시 NCM listener-down `transport-error`와 `ncm-tcpctl` backend의 ACM fallback도 검증
- `a90_broker_auth_hardening_check.py`
  - v193 broker/auth hardening validator
  - `--no-auth` explicit allow gate, invalid token rejection, selftest, no-auth metadata recording을 host-only로 검증
- `a90_broker_ncm_lifecycle_check.py`
  - v194 NCM/tcpctl broker lifecycle validator
  - authenticated tcpctl listener start → NCM broker smoke → tcpctl stop을 하나의 private evidence bundle로 검증
  - `--dry-run`으로 device state 변경 없이 command plan을 검증
- `a90_broker_soak_suite.py`
  - v195 broker-backed soak suite
  - concurrent smoke, mixed-soak gate, recovery tests를 하나의 private bundle로 묶음
  - `--dry-run`은 device-safe wiring 검증, live mode는 장시간 broker soak에 사용
- `security_scan_followup.py`
  - v196 fresh security scan follow-up helper
  - Codex Cloud CSV export가 local finding index에 반영됐는지 확인하고 private summary/report를 생성
- `native_init_flash.py`
  - TWRP recovery ADB에서 native init boot image를 boot 파티션에 기록
  - `adb devices` 출력을 whitespace split으로 파싱해 `recovery` 상태를 안정적으로 감지
  - local image marker 확인, push 후 SHA256 확인, boot partition prefix readback 확인
  - TWRP에서 system으로 돌아갈 때 `adb shell 'twrp reboot'` 무인자 사용
  - 부팅 후 기본 `--verify-protocol auto`로 v73 `cmdv1 version/status`를 확인
  - pre-v73 image는 `A90P1 END`가 없을 때 raw `version` 검증으로 fallback
  - Batch 3 이후 `--remote-image`/`--boot-block`은 절대 경로만 허용하고 remote shell에서 안전하게 quote
- `build_static_toybox.sh`
  - 공식 `toybox-0.8.13` tarball을 해시 검증 후 다운로드
  - `aarch64-linux-gnu-gcc`로 static ARM64 toybox를 빌드
  - 산출물은 gitignore된 `workspace/private/inputs/external_tools/userland/bin/toybox-aarch64-static-0.8.13`
  - native init 실기 검증 시 `/cache/bin/toybox`로 올려 `run /cache/bin/toybox ...` 형태로 사용
- `build_static_busybox.sh`
  - `busybox-1.36.1` tarball을 해시 검증 후 다운로드
  - `aarch64-linux-gnu-gcc`로 static ARM64 BusyBox를 빌드
  - 산출물은 gitignore된 `workspace/private/inputs/external_tools/userland/bin/busybox-aarch64-static-1.36.1`
  - v99 검증 시 SD runtime root의 `/mnt/sdext/a90/bin/busybox` 후보로 사용
  - Batch 3 이후 dynamic-section 검사 임시 파일은 `mktemp`로 생성하고 종료 시 삭제
- `busybox_userland.py`
  - v99 BusyBox/toybox 후보의 local-info, manifest, device status, smoke 비교를 수행
- `kernel_inventory_collect.py`
  - v154 kernel capability inventory host collector
  - captures `kernelinv` summary/full/paths with private 0700/0600 output
- `kernel_diag_bundle.py`
  - v155 kernel diagnostics evidence bundle
  - captures `kernelinv`, `diag`, `longsoak`, `exposure`, `wifiinv`, and `wififeas` read-only outputs
- `sensor_map_collect.py`
  - v156 thermal/power sensor map host collector
  - captures `sensormap` summary/thermal/power/paths with private 0700/0600 output
- `pstore_feas_collect.py`
  - v157 pstore/ramoops feasibility host collector
  - captures `pstore` summary/full/paths with private 0700/0600 output
- `watchdog_feas_collect.py`
  - v158 watchdog feasibility host collector
  - captures `watchdoginv` summary/full/paths with private 0700/0600 output
- `tracefs_feas_collect.py`
  - v159 tracefs/ftrace feasibility host collector
  - captures `tracefs` summary/full/paths with private 0700/0600 output
- `diag_collect.py`
  - v102 diagnostics/log bundle host collector
  - v116 기준 기본 실행 시 `status`, `bootstatus`, `selftest verbose`, `runtime`, `helpers verbose`, `helpers verify`, `service list`, `netservice status`, `rshell audit`, `diag paths` device evidence를 함께 수집
  - `--device-bundle`로 device-side `/mnt/sdext/a90/logs/a90-diag-*.txt` bundle 생성을 확인
  - `--rshell-harden`으로 v115+ remote shell token rejection/smoke를 선택 검증
  - v125부터 host 출력 directory는 `0700`, report file은 `0600`으로 생성하고 default diagnostic log-tail은 redacted 상태로 수집
- `rshell_host.py`
  - v100 custom remote shell helper의 start/status/stop/token/exec/smoke 검증 wrapper
  - v115 기준 `invalid-token`과 `harden`으로 token 거부, smoke 실행, stop/rollback까지 한 번에 확인
  - serial bridge로 `rshell` lifecycle을 제어하고, 명령 실행은 USB NCM `192.168.7.2:2326`의 `A90RSH1` protocol로 확인
  - `start`/`stop`처럼 NCM 재열거로 framed END가 끊길 수 있는 동작은 raw-control-like로 처리한 뒤 status를 재확인
- `build_usbnet_helper.sh`
  - `stage3/linux_init/a90_usbnet.c`를 static ARM64 helper로 빌드
  - 산출물은 gitignore된 `workspace/private/inputs/external_tools/userland/bin/a90_usbnet-aarch64-static`
  - TWRP ADB로 `/cache/bin/a90_usbnet`에 배치해 USB ACM/NCM/RNDIS probe에 사용
- `ncm_host_setup.py`
  - native init bridge를 통해 `/cache/bin/a90_usbnet ncm`을 실행하고 device `ncm0` IP를 설정
  - 기본 `--device-protocol auto`로 짧은 device command는 `cmdv1` rc/status를 우선 사용
  - `off`처럼 USB 재열거로 끊길 수 있는 명령은 raw bridge 경로 유지
  - v60 boot netservice처럼 NCM이 이미 켜져 있으면 재실행하지 않고 기존 `ncm0`/host MAC을 사용
  - Batch 3 이후 host sudo NIC 설정은 기본적으로 `--interface <ifname>`가 필요
  - trusted single-device lab에서만 `--allow-auto-interface`로 `ncm.host_addr` 기반 자동 탐지를 opt-in
  - host `192.168.7.1/24`, device `192.168.7.2/24` ping 검증과 `off` rollback 제공
- `build_nettest_helper.sh`
  - `stage3/linux_init/a90_nettest.c`를 static ARM64 TCP 검증 helper로 빌드
  - 산출물은 gitignore된 `workspace/private/inputs/external_tools/userland/bin/a90_nettest-aarch64-static`
  - `/cache/bin/a90_nettest listen|send`로 USB NCM 양방향 TCP payload를 검증
- `build_tcpctl_helper.sh`
  - `stage3/linux_init/a90_tcpctl.c`를 static ARM64 TCP command helper로 빌드
  - 산출물은 gitignore된 `workspace/private/inputs/external_tools/userland/bin/a90_tcpctl-aarch64-static`
  - v123 이후 ramdisk `/bin/a90_tcpctl listen <bind_addr> <port> <idle_timeout_sec> [max_clients] [token_path]`로 NCM 위의 작은 명령/응답 채널을 검증
- `tcpctl_host.py`
  - host에서 `/bin/a90_tcpctl`을 start/call/run/stop/smoke/soak 형태로 다루는 wrapper
  - serial bridge는 launch/rescue 채널로 유지하고, 명령은 NCM `192.168.7.2:2325`로 전달
  - 기본값은 `netservice token show`로 tcpctl token을 읽어 `run`/`shutdown` 전에 `auth <token>`을 보낸다
  - legacy pre-v123 checks only: `--no-auth`
  - v124부터 `install`은 runtime/cache helper root만 허용하고 임시 파일 업로드, SHA256 검증, `mv -f` 교체, 실패 시 임시 파일 삭제 순서로 동작
  - Wi-Fi execns helper deploy는 NCM `tcpctl install`을 기본 경로로 쓰며, serial `appendfile + uudecode`는 NCM이 불가능한 rescue fallback으로만 사용
  - serial fallback은 `cmdv1x` hex 인코딩 때문에 4096-byte line/buffer 한계가 병목이며, 현재 기본 chunk는 안전 검증된 `1900` bytes
  - install 후 chmod/sha256, smoke/soak의 bridge version 확인은 `cmdv1` rc/status 우선
  - tcpctl listener처럼 long-running serial command는 raw bridge streaming 유지
  - `smoke`는 start → ping/version/status/run/shutdown → serial/NCM 상태 확인을 한 번에 수행
  - `soak`은 기본 300초 동안 TCP ping/status/run과 host NCM ping을 반복해 안정성을 확인
- `netservice_reconnect_soak.py`
  - v60 `netservice stop/start`로 USB UDC 재열거 뒤 ACM/NCM/tcpctl 복구를 검증
  - bridge version/netservice status/usbnet status/ifconfig 같은 짧은 확인은 `cmdv1` rc/status 우선
  - `netservice start|stop`처럼 USB 재열거로 끊길 수 있는 명령은 raw bridge 유지
  - Batch 3 이후 host sudo NIC 설정은 기본적으로 `--interface <ifname>`가 필요하고 MAC 자동 선택은 `--allow-auto-interface` opt-in
- `physical_usb_reconnect_check.py`
  - 실제 USB 케이블 unplug/replug 이후 ACM bridge, NCM ping, tcpctl 응답 복구를 한 번에 확인
  - 필요하면 netservice를 먼저 시작하고, sudo가 막히면 `--manual-host-config`로 host IP 수동 설정을 기다림
  - NCM host 설정은 `netservice_reconnect_soak.py`의 `--interface`/`--allow-auto-interface` 정책을 따름
  - `--manual-host-config`는 sudo가 불가능한 환경에서 현재 `sudo ip ... dev <enx...>` 명령을 출력하고 사용자의 수동 설정을 기다림

권장 순서:

```bash
./scripts/revalidation/verify_device_state.sh
./scripts/revalidation/capture_baseline.sh --label baseline_a
```

브릿지 실행 예:

```bash
sudo python3 ./scripts/revalidation/serial_tcp_bridge.py --port 54321
```

접속 예:

```bash
nc 127.0.0.1 54321
```

권장 콘솔 예:

```bash
python3 ./scripts/revalidation/serial_console.py --port 54321
```

관찰 전용 예:

```bash
python3 ./scripts/revalidation/serial_console.py --port 54321 --watch-only
```

framed one-shot command 예:

```bash
python3 ./scripts/revalidation/a90ctl.py status
python3 ./scripts/revalidation/a90ctl.py --json --allow-error nope
python3 ./scripts/revalidation/a90ctl.py --hide-on-busy status
```

A90B1 broker smoke 예:

```bash
python3 ./scripts/revalidation/a90_broker.py selftest
python3 ./scripts/revalidation/a90_broker.py serve --backend fake --runtime-dir tmp/a90-broker
python3 ./scripts/revalidation/a90_broker.py call --runtime-dir tmp/a90-broker --json status
```

v201 이후 broker 기본 정책은 observe-only입니다. `run`, `cpustress`,
`mountsd`, `menu` 같은 operator/exclusive 명령은 명시적으로 허용한 broker
인스턴스에서만 실행합니다.

```bash
python3 ./scripts/revalidation/a90_broker.py serve \
  --backend fake \
  --runtime-dir tmp/a90-broker-exclusive \
  --allow-exclusive

python3 ./scripts/revalidation/a90_broker.py call \
  --runtime-dir tmp/a90-broker-exclusive \
  --json \
  run id
```

A90B1 broker concurrent smoke 예:

```bash
python3 ./scripts/revalidation/a90_broker_concurrent_smoke.py \
  --backend fake \
  --clients 4 \
  --rounds 3 \
  --include-blocked

python3 ./scripts/revalidation/a90_broker_concurrent_smoke.py \
  --backend acm-cmdv1 \
  --clients 4 \
  --rounds 2 \
  --include-blocked \
  --expect-version "A90 Linux init 0.9.59 (v159)"
```

A90B1 broker mixed-soak gate 예:

```bash
python3 ./scripts/revalidation/a90_broker_mixed_soak_gate.py \
  --duration-sec 45 \
  --observer-interval 10 \
  --workload-profile smoke \
  --seed 190
```

A90B1 broker recovery tests 예:

```bash
python3 ./scripts/revalidation/a90_broker_recovery_tests.py
python3 ./scripts/revalidation/a90_broker_recovery_tests.py --include-live
```

A90B1 broker auth hardening 예:

```bash
python3 ./scripts/revalidation/a90_broker_auth_hardening_check.py
```

A90B1 broker NCM/tcpctl lifecycle 예:

```bash
python3 ./scripts/revalidation/a90_broker_ncm_lifecycle_check.py --dry-run
# NCM host IP와 bridge가 준비된 상태에서는 --dry-run 없이 실행
python3 ./scripts/revalidation/a90_broker_ncm_lifecycle_check.py
```

A90B1 broker soak suite 예:

```bash
python3 ./scripts/revalidation/a90_broker_soak_suite.py \
  --dry-run \
  --duration-sec 30

python3 ./scripts/revalidation/a90_broker_soak_suite.py \
  --duration-sec 3600 \
  --include-live-recovery
```

Security scan follow-up 예:

```bash
python3 ./scripts/revalidation/security_scan_followup.py \
  --require-indexed \
  --run-dir tmp/a90-v196-security-followup
```

A90B1 broker로 실제 ACM bridge를 감싸는 예:

```bash
python3 ./scripts/revalidation/a90_broker.py serve \
  --backend acm-cmdv1 \
  --runtime-dir tmp/a90-broker \
  --bridge-host 127.0.0.1 \
  --bridge-port 54321

python3 ./scripts/revalidation/a90_broker.py call \
  --runtime-dir tmp/a90-broker \
  --json version

python3 ./scripts/revalidation/a90_broker.py report \
  --runtime-dir tmp/a90-broker
```

A90B1 broker의 NCM/tcpctl backend 예:

```bash
# 전제: host 192.168.7.1/24, device 192.168.7.2, a90_tcpctl listener running
python3 ./scripts/revalidation/a90_broker.py serve \
  --backend ncm-tcpctl \
  --runtime-dir tmp/a90-broker-ncm \
  --token "$A90_TCPCTL_TOKEN" \
  --allow-exclusive

python3 ./scripts/revalidation/a90_broker.py call \
  --runtime-dir tmp/a90-broker-ncm \
  --json \
  run /cache/bin/toybox uptime
```

하네스가 broker를 통하게 하는 예:

```bash
python3 ./scripts/revalidation/native_test_supervisor.py \
  --device-backend broker \
  --broker-runtime-dir tmp/a90-broker \
  smoke
```

native init 이미지 플래시/검증 예:

```bash
python3 ./scripts/revalidation/native_init_flash.py \
  stage3/boot_linux_v73.img \
  --expect-version "A90 Linux init 0.8.4 (v73)"
```

현재 native init에서 recovery로 전환한 뒤 플래시까지 이어가는 예:

```bash
python3 ./scripts/revalidation/native_init_flash.py \
  stage3/boot_linux_v73.img \
  --expect-version "A90 Linux init 0.8.4 (v73)" \
  --from-native
```

이미 부팅된 native init 버전만 확인하는 예:

```bash
python3 ./scripts/revalidation/native_init_flash.py \
  --verify-only \
  --expect-version "A90 Linux init 0.8.4 (v73)" \
  --verify-protocol auto
```

static toybox 빌드 예:

```bash
./scripts/revalidation/build_static_toybox.sh
```

USB net helper 빌드 예:

```bash
./scripts/revalidation/build_usbnet_helper.sh
```

NCM host 설정 예:

```bash
python3 ./scripts/revalidation/ncm_host_setup.py setup
python3 ./scripts/revalidation/ncm_host_setup.py status
python3 ./scripts/revalidation/ncm_host_setup.py off
```

Host에 A90 NCM 자동 설정이 설치된 경우에는 A90 NCM 인터페이스가 생길 때
host IP가 자동으로 설정된다. 이 경우 매번 수동
`sudo ip addr replace 192.168.7.1/24 dev <ifname>`가 필요하지 않다.

현재 개발 host 기준 NetworkManager 자동 설정:

- NM profile: `유선 연결 2`
- interface: `enx362362068825`
- MAC: `36:23:62:06:88:25`
- host IP: `192.168.7.1/24`
- device IP: `192.168.7.2`
- autoconnect: on
- prerequisite: native init `netservice`가 활성화되어 NCM interface가 올라와야 함

NetworkManager preflight:

```bash
ip -4 addr show enx362362068825 | grep 192.168.7.1
ip -4 addr show | grep 192.168.7.1
python3 scripts/revalidation/a90ctl.py netservice status
```

주의: `enx0000000005e1`은 USB hub 유선 LAN(`192.168.0.8/24`)이며 A90 NCM이
아니다.

대체 udev 자동 설정:

- udev rule: `/etc/udev/rules.d/90-a90-ncm.rules`
- match: `cdc_ncm` driver + Samsung VID `04e8`
- action: `/usr/local/sbin/a90-ncm-up <ifname>`
- result: `ip link set <ifname> up` + `192.168.7.1/24`

udev 자동 설정 최초 설치 (1회, operator가 직접 실행):

```bash
python3 scripts/revalidation/a90_ncm_host_preflight.py --no-ping run
sudo cp tmp/host/a90-ncm-host-preflight/templates/a90-ncm-up.sh /usr/local/sbin/a90-ncm-up
sudo chmod 755 /usr/local/sbin/a90-ncm-up
sudo cp tmp/host/a90-ncm-host-preflight/templates/90-a90-ncm.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
```

주의: `enx*` 인터페이스가 항상 A90 NCM인 것은 아니다. USB 허브를 통한
유선 LAN 어댑터도 `enx*` 이름을 가질 수 있다. preflight는 인터페이스
이름이 아니라 실제 IP 주소로 확인한다:

```bash
ip -4 addr show | grep 192.168.7.1
```

TCP nettest helper 빌드 예:

```bash
./scripts/revalidation/build_nettest_helper.sh
```

TCP control helper 빌드 예:

```bash
./scripts/revalidation/build_tcpctl_helper.sh
```

TCP control host wrapper 예:

```bash
python3 ./scripts/revalidation/tcpctl_host.py smoke
python3 ./scripts/revalidation/tcpctl_host.py start
python3 ./scripts/revalidation/tcpctl_host.py status
python3 ./scripts/revalidation/tcpctl_host.py run /cache/bin/toybox uname -a
python3 ./scripts/revalidation/tcpctl_host.py stop
python3 ./scripts/revalidation/tcpctl_host.py soak
```

netservice reconnect 검증 예:

```bash
python3 ./scripts/revalidation/netservice_reconnect_soak.py status
python3 ./scripts/revalidation/netservice_reconnect_soak.py once --manual-host-config
python3 ./scripts/revalidation/netservice_reconnect_soak.py soak --cycles 3 --manual-host-config
```

물리 케이블 unplug/replug 검증 예:

```bash
python3 ./scripts/revalidation/physical_usb_reconnect_check.py --manual-host-config
```

`READY`가 보이면 A90 USB 케이블을 뽑았다가 다시 꽂는다. host IP 설정이 필요하면
스크립트가 출력하는 `sudo ip addr replace ...`와 `sudo ip link set ...` 명령을
다른 터미널에서 실행한다.

참고:

- 현재 호스트 계정이 `dialout` 그룹이 아니면 `sudo`로 실행해야 할 수 있습니다.
- 이 브릿지는 빠른 개발용 최소 구현이라 클라이언트 1개만 허용합니다.
- 따라서 `serial_console.py`와 `nc`는 동시에 붙지 않습니다.
- serial device가 없는 상태에서는 기본적으로 TCP client를 거절합니다.
  - 이전처럼 serial 없이도 client를 유지하고 싶으면 `--allow-client-without-serial`을 사용합니다.
- 장기적으로는 `USB networking + SSH` 또는 안정적인 `ADB` 채널이 더 적합합니다.

생성 산출물은 기본적으로 `backups/` 아래에 저장합니다.
`.img`와 백업 디렉토리는 이미 `.gitignore`에 포함되어 있습니다.

과거 AOSP, headless Android, Magisk 모듈, 커널 최적화 스크립트는 `../archive/legacy/`를 참고합니다.
