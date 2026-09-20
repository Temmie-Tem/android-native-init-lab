#!/usr/bin/env python3
"""Integration checks against a private ARM64 virt image; never a device runner."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import uuid


class VM:
    def __init__(self, folder, kernel, qemu_root, key):
        self.folder, self.kernel, self.qemu_root, self.key = folder, kernel, qemu_root, key
        with socket.socket() as sock:
            sock.bind(('localhost', 0))
            self.port = sock.getsockname()[1]
        self.process = None

    def start(self, label, disk=None, initrd=None):
        disk = disk or self.folder / 'root.ext4'
        initrd = initrd or self.folder / 'initramfs.cpio.gz'
        command = [self.qemu_root / 'usr/bin/qemu-system-aarch64', '-machine', 'virt',
            '-cpu', 'cortex-a76', '-smp', '2', '-m', '1024', '-nographic',
            '-monitor', 'none', '-no-reboot', '-kernel', self.kernel,
            '-initrd', initrd, '-append', 'console=ttyAMA0 rdinit=/init panic=-1',
            '-drive', f'if=none,id=root,file={disk},format=raw',
            '-device', 'virtio-blk-device,drive=root', '-netdev',
            f'user,id=net0,hostfwd=tcp:{socket.gethostbyname("localhost")}:{self.port}-:22',
            '-device', 'virtio-net-device,netdev=net0', '-device', 'virtio-rng-device']
        self.log = self.folder / (label + '.serial.log')
        (self.folder / (label + '.command.json')).write_text(json.dumps([str(x) for x in command]) + '\n')
        with self.log.open('wb') as log:
            self.process = subprocess.Popen([str(x) for x in command], stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, env=dict(os.environ,
                LD_LIBRARY_PATH=str(self.qemu_root / 'usr/lib/x86_64-linux-gnu')))

    def ssh(self, script, label, *, user='root', pty=False, check=True, timeout=30):
        command = ['ssh', '-i', self.key, '-p', str(self.port), '-o', 'BatchMode=yes',
            '-o', 'ConnectTimeout=3', '-o', 'StrictHostKeyChecking=accept-new',
            '-o', 'UserKnownHostsFile=' + str(self.folder / 'known_hosts'),
            *(['-tt'] if pty else []), user + '@localhost', script]
        result = subprocess.run([str(x) for x in command], capture_output=True, timeout=timeout)
        (self.folder / (label + '.ssh.log')).write_bytes(result.stdout + result.stderr)
        if check and result.returncode:
            raise RuntimeError(f'{label}: SSH status {result.returncode}')
        return result

    def ready(self, label):
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError('VM exited before SSH')
            if b'BOOTSTRAP_STOP' in self.log.read_bytes():
                raise RuntimeError('bootstrap stopped; see serial log')
            result = self.ssh('test -s /run/lab/boot-receipt', label, check=False, timeout=6)
            if result.returncode == 0:
                return
            time.sleep(1)
        raise RuntimeError('SSH readiness deadline')

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=10)


def qualify(vm):
    results = dict(scope='H0 ARM64 virt only', device_actions=0)
    token = uuid.uuid4().hex
    vm.start('boot-1')
    vm.ready('ready-1')
    output = vm.ssh("""set -eu
test "$(readlink /proc/1/exe)" = /usr/sbin/init
test "$(readlink /proc/1/root)" = /
test "$(stat -c %d /)" = "$(stat -Lc %d /proc/1/root)"
test "$(cat /var/lib/lab/boot-count)" = 1
test -c /dev/null && test -c /dev/pts/ptmx
test "$(findmnt -n -o FSTYPE /dev)" = tmpfs
test "$(findmnt -n -o FSTYPE /)" = ext4
test "$(findmnt -n -o FSTYPE /dev/pts)" = devpts
test "$(pgrep -fc '^/bin/busybox mdev -df$')" = 1
test "$(pgrep -fc '^/bin/busybox udhcpc ' )" = 1
test "$(cat /sys/fs/selinux/enforce)" = 0
cat /proc/sys/kernel/random/boot_id
sha256sum /etc/ssh/ssh_host_ed25519_key.pub
cat /run/lab/boot-receipt
""", 'identity-1').stdout.decode()
    results['first_boot_id'] = output.splitlines()[0]
    results['ssh_host_key'] = output.splitlines()[1]
    vm.ssh('test -t 0 && test -t 1 && id && echo PTY_PASS', 'pty', user='lab', pty=True)
    vm.ssh("""set -eu
old=$(cat /run/lab-dhcp.pid)
service lab-network start
service lab-network start
test "$(cat /run/lab-dhcp.pid)" = "$old"
test "$(pgrep -fc '^/bin/busybox udhcpc ')" = 1
service mdev stop
rm /dev/full
service mdev start
sleep 1
test -c /dev/full
test "$(pgrep -fc '^/bin/busybox mdev -df$')" = 1
service lab-log restart
logger -t h0-log lifecycle-pass
sleep 1
grep -q lifecycle-pass /var/log/messages
service cron stop
if service cron status; then exit 1; fi
service cron start
service cron status
service ssh restart
printf '* * * * * root echo tick >> /var/lib/lab/cron-proof; logger -t h0-cron tick\n' > /etc/cron.d/h0-proof
chmod 644 /etc/cron.d/h0-proof
""", 'services')
    vm.ssh("""cat > /run/net-cycle.sh <<'EOF'
#!/bin/sh
set -eu
trap 'status=$?; printf "%s\\n" "$status" > /run/net-cycle.status' EXIT
old=$(cat /run/lab-dhcp.pid)
service lab-network stop
if kill -0 "$old" 2>/dev/null; then exit 1; fi
service lab-network start
echo PASS > /run/net-cycle.result
EOF
chmod 700 /run/net-cycle.sh
nohup /bin/sh /run/net-cycle.sh > /run/net-cycle.log 2>&1 < /dev/null &
""", 'network-cycle-launch')
    deadline = time.monotonic() + 35
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        result = vm.ssh("""set -eu
cat /run/net-cycle.log 2>/dev/null || :
test -f /run/net-cycle.status || exit 42
printf 'job_status=%s\n' "$(cat /run/net-cycle.status)"
test "$(cat /run/net-cycle.status)" = 0
test "$(cat /run/net-cycle.result)" = PASS
test "$(pgrep -fc '^/bin/busybox udhcpc ')" = 1
echo NETWORK_CYCLE_PASS
""", f'network-cycle-result-{attempt}', check=False, timeout=6)
        if result.returncode == 0:
            break
        if result.returncode not in (42, 255):
            raise RuntimeError('network cycle job failed; raw job log retained')
        time.sleep(1)
    else:
        raise RuntimeError('network cycle completion deadline')
    vm.ssh('apt-get update && apt-get install -y --no-install-recommends hello && hello',
           'package-install', timeout=90)
    deadline = time.monotonic() + 75
    while time.monotonic() < deadline:
        if vm.ssh('test -s /var/lib/lab/cron-proof && grep -q h0-cron /var/log/messages',
                  'cron-proof', check=False).returncode == 0:
            break
        time.sleep(3)
    else:
        raise RuntimeError('cron did not produce file and logger evidence')
    vm.ssh(f"printf '{token}\\n' > /home/lab/persistence; chown lab:lab /home/lab/persistence; sync; /sbin/shutdown -r now",
           'reboot-request')
    if vm.process.wait(timeout=30) != 0:
        raise RuntimeError('normal reboot failed')
    if b'reboot: Restarting system' not in vm.log.read_bytes():
        raise RuntimeError('normal reboot terminal absent')
    vm.start('boot-2')
    vm.ready('ready-2')
    second = vm.ssh(f"""set -eu
test "$(cat /var/lib/lab/boot-count)" = 2
test "$(cat /home/lab/persistence)" = {token}
service cron status >/dev/null
hello
cat /proc/sys/kernel/random/boot_id
sha256sum /etc/ssh/ssh_host_ed25519_key.pub
""", 'identity-2').stdout.decode().splitlines()
    if second[-2] == results['first_boot_id'] or second[-1] != results['ssh_host_key']:
        raise RuntimeError('fresh-boot or persistent-host-key check failed')
    results['second_boot_id'] = second[-2]
    vm.ssh('/sbin/shutdown -h now', 'shutdown-request')
    if vm.process.wait(timeout=30) != 0 or b'reboot: Power down' not in vm.log.read_bytes():
        raise RuntimeError('normal shutdown failed')
    check = subprocess.run(['e2fsck', '-fn', vm.folder / 'root.ext4'], capture_output=True)
    (vm.folder / 'final-e2fsck.log').write_bytes(check.stdout + check.stderr)
    if check.returncode:
        raise RuntimeError('final filesystem check failed')
    results.update(verdict='PASS_DEBIAN_VIRT_LIFECYCLE_H0',
        proved=['PID1/root handoff', 'device nodes and PTY', 'SSH public key',
                'mdev/syslog/cron/SSH lifecycle', 'DHCP duplicate start and stop',
                'signed apt install', 'cron job and log', 'normal reboot',
                'persistent file/package/host key', 'normal shutdown and clean ext4'])
    (vm.folder / 'result.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('folder', 'kernel', 'qemu-root', 'key'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    vm = VM(args.folder.resolve(), args.kernel.resolve(), args.qemu_root.resolve(), args.key.resolve())
    try:
        qualify(vm)
    finally:
        vm.stop()
