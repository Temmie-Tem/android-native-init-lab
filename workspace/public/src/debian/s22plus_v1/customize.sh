#!/bin/sh
# mmdebstrap customize hook. Host build only, inside its isolated namespace.
set -eu
root=$1
test -n "$LAB_SOURCE" && test -n "$LAB_OUTPUT" && test -n "$LAB_AUTH_KEY"
mkdir -p "$root/usr/local/lib" "$root/etc/ssh/sshd_config.d" "$root/run"
for service in mdev lab-log lab-network lab-firstboot; do
 install -m 0755 "$LAB_SOURCE/$service" "$root/etc/init.d/$service"
 chroot "$root" update-rc.d "$service" defaults
done
install -m 0755 "$LAB_SOURCE/lab-udhcpc" "$root/usr/local/lib/lab-udhcpc"
cat > "$root/etc/mdev.conf" <<'EOF'
null|zero|full|random|urandom 0:0 0666
tty 0:5 0666
ptmx 0:5 0666
.* 0:0 0600
EOF
printf 's22-debian\n' > "$root/etc/hostname"
getent ahostsv4 localhost | awk 'NR == 1 {print $1 " localhost"}' > "$root/etc/hosts"
: > "$root/etc/resolv.conf"
: > "$root/etc/fstab"
printf 'LANG=C.UTF-8\n' > "$root/etc/default/locale"
# This image has no virtual terminal or interactive root login.
sed -i '/^[1-6]:/d' "$root/etc/inittab"
chroot "$root" useradd -m -s /bin/bash lab
# A locked password hash permits public-key PAM sessions; passwords stay disabled.
chroot "$root" passwd -l root
install -d -m 0700 "$root/home/lab/.ssh"
install -m 0600 "$LAB_AUTH_KEY" "$root/home/lab/.ssh/authorized_keys"
chroot "$root" chown -R lab:lab /home/lab
cat > "$root/etc/ssh/sshd_config.d/10-lab.conf" <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
AuthenticationMethods publickey
AllowUsers lab
EOF
rm -f "$root"/etc/ssh/ssh_host_* "$root/etc/machine-id"
printf 'S22PLUS_DEBIAN_V1\n' > "$root/etc/lab-rootfs-id"
chroot "$root" dpkg-query -W '-f=${Package}\t${Version}\t${Architecture}\n' > "$LAB_OUTPUT/packages.tsv"
"$LAB_SOURCE/retain-packages.sh" "$root"
# No host identity, build host resolver, host keys or QEMU interpreter in product.
find "$root/var/log" -type f -exec truncate -s 0 '{}' +
rm -f "$root/var/lib/systemd/random-seed" "$root/var/lib/urandom/random-seed"
