// SPDX-License-Identifier: MIT
/*
 * Generic-arm64 H0 control for the platform driver_override match fence.
 *
 * This is not an S22+ hardware emulator.  QEMU provides three active
 * virtio-mmio platform devices.  The guest discovers them with the real
 * virtio_mmio driver, unloads that driver, writes a blocking override to two
 * devices, and reloads the driver.  Only the unblocked target may bind.  It
 * then clears both overrides and reprobes them as a positive control.
 */

#define _GNU_SOURCE

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

#define CONTROL_MODULE "virtio_mmio"
#define CONTROL_DRIVER "virtio-mmio"
#define CONTROL_DEVICE_SUFFIX ".virtio_mmio"
#define CONTROL_OVERRIDE "s22plus-max77705-block"
#define CONTROL_ACTIVE_COUNT 3U
#define CONTROL_PATH_CAPACITY 512U
#define CONTROL_READ_CAPACITY 256U

struct control_devices {
	char names[CONTROL_ACTIVE_COUNT][128];
	size_t count;
};

static __attribute__((noreturn)) void control_park(void)
{
	for (;;)
		pause();
}

static __attribute__((noreturn)) void control_fail(
	const char *stage, int detail)
{
	dprintf(
		STDOUT_FILENO,
		"MAX77705_DRIVER_OVERRIDE_QEMU result=FAIL stage=%s detail=%d\n",
		stage,
		detail);
	sync();
	control_park();
}

static void control_mkdir(const char *path)
{
	if (mkdir(path, 0700) != 0 && errno != EEXIST)
		control_fail(path, errno);
}

static void control_mount_filesystems(void)
{
	control_mkdir("/proc");
	control_mkdir("/sys");
	if (mount("proc", "/proc", "proc", 0, NULL) != 0 && errno != EBUSY)
		control_fail("mount-proc", errno);
	if (mount("sysfs", "/sys", "sysfs", 0, NULL) != 0 && errno != EBUSY)
		control_fail("mount-sysfs", errno);
}

static void control_path(
	char *buffer, size_t capacity, const char *format, const char *name)
{
	int length = snprintf(buffer, capacity, format, name);
	if (length < 0 || (size_t)length >= capacity)
		control_fail("path-overflow", EOVERFLOW);
}

static void control_write_exact(const char *path, const char *value)
{
	int fd = open(path, O_WRONLY | O_CLOEXEC);
	if (fd < 0)
		control_fail(path, errno);
	size_t length = strlen(value);
	ssize_t amount = write(fd, value, length);
	int saved_errno = errno;
	close(fd);
	if (amount != (ssize_t)length)
		control_fail(path, amount < 0 ? saved_errno : EIO);
}

static void control_read_exact(const char *path, const char *expected)
{
	char value[CONTROL_READ_CAPACITY];
	int fd = open(path, O_RDONLY | O_CLOEXEC);
	if (fd < 0)
		control_fail(path, errno);
	ssize_t amount = read(fd, value, sizeof(value) - 1U);
	int saved_errno = errno;
	close(fd);
	if (amount < 0)
		control_fail(path, saved_errno);
	value[amount] = '\0';
	if (strcmp(value, expected) != 0)
		control_fail(path, EPROTO);
}

static bool control_exists(const char *path)
{
	struct stat value;
	if (lstat(path, &value) == 0)
		return true;
	if (errno == ENOENT)
		return false;
	control_fail(path, errno);
}

static bool control_module_loaded(void)
{
	FILE *stream = fopen("/proc/modules", "re");
	if (stream == NULL)
		control_fail("open-proc-modules", errno);
	char line[512];
	bool found = false;
	while (fgets(line, sizeof(line), stream) != NULL) {
		char name[256] = {0};
		if (sscanf(line, "%255s", name) == 1
		    && strcmp(name, CONTROL_MODULE) == 0) {
			found = true;
			break;
		}
	}
	if (ferror(stream)) {
		int saved_errno = errno;
		fclose(stream);
		control_fail("read-proc-modules", saved_errno);
	}
	fclose(stream);
	return found;
}

static void control_load_module(void)
{
	int fd = open("/modules/virtio_mmio.ko", O_RDONLY | O_CLOEXEC);
	if (fd < 0)
		control_fail("open-virtio-mmio", errno);
	errno = 0;
	long rc = syscall(SYS_finit_module, fd, "", 0);
	int saved_errno = errno;
	close(fd);
	if (rc != 0)
		control_fail("load-virtio-mmio", saved_errno);
	if (!control_module_loaded())
		control_fail("module-load-readback", EPROTO);
}

static void control_unload_module(void)
{
	errno = 0;
	long rc = syscall(SYS_delete_module, CONTROL_MODULE, O_NONBLOCK);
	int saved_errno = errno;
	if (rc != 0)
		control_fail("unload-virtio-mmio", saved_errno);
	if (control_module_loaded())
		control_fail("module-unload-readback", EPROTO);
}

static bool control_has_suffix(const char *value, const char *suffix)
{
	size_t value_length = strlen(value);
	size_t suffix_length = strlen(suffix);
	return value_length >= suffix_length
		&& strcmp(value + value_length - suffix_length, suffix) == 0;
}

static int control_name_compare(const void *left, const void *right)
{
	return strcmp(left, right);
}

static bool control_device_bound(const char *name)
{
	char path[CONTROL_PATH_CAPACITY];
	char target[CONTROL_PATH_CAPACITY];
	control_path(
		path,
		sizeof(path),
		"/sys/bus/platform/devices/%s/driver",
		name);
	if (!control_exists(path))
		return false;
	ssize_t amount = readlink(path, target, sizeof(target) - 1U);
	if (amount < 0)
		control_fail(path, errno);
	target[amount] = '\0';
	if (!control_has_suffix(target, "/" CONTROL_DRIVER))
		control_fail("unexpected-platform-driver", EPROTO);
	return true;
}

static void control_discover_active(struct control_devices *result)
{
	DIR *directory = opendir("/sys/bus/platform/devices");
	if (directory == NULL)
		control_fail("open-platform-devices", errno);
	int readdir_errno = 0;
	for (;;) {
		errno = 0;
		struct dirent *entry = readdir(directory);
		if (entry == NULL) {
			readdir_errno = errno;
			break;
		}
		if (!control_has_suffix(entry->d_name, CONTROL_DEVICE_SUFFIX)
		    || !control_device_bound(entry->d_name))
			continue;
		if (result->count >= CONTROL_ACTIVE_COUNT) {
			closedir(directory);
			control_fail("active-device-overflow", EOVERFLOW);
		}
		size_t length = strlen(entry->d_name);
		if (length >= sizeof(result->names[0])) {
			closedir(directory);
			control_fail("active-device-name", EOVERFLOW);
		}
		memcpy(result->names[result->count], entry->d_name, length + 1U);
		++result->count;
	}
	closedir(directory);
	if (readdir_errno != 0)
		control_fail("read-platform-devices", readdir_errno);
	if (result->count != CONTROL_ACTIVE_COUNT)
		control_fail("active-device-count", EPROTO);
	qsort(
		result->names,
		result->count,
		sizeof(result->names[0]),
		control_name_compare);
}

static void control_require_binding(const char *name, bool expected)
{
	if (control_device_bound(name) != expected)
		control_fail(name, EPROTO);
}

static void control_set_override(const char *name, const char *value)
{
	char path[CONTROL_PATH_CAPACITY];
	control_path(
		path,
		sizeof(path),
		"/sys/bus/platform/devices/%s/driver_override",
		name);
	control_write_exact(path, value);
	control_read_exact(
		path,
		value[0] == '\n' && value[1] == '\0'
			? "(null)\n"
			: CONTROL_OVERRIDE "\n");
}

static void control_reprobe(const char *name)
{
	control_write_exact("/sys/bus/platform/drivers_probe", name);
}

int main(void)
{
	struct control_devices active = {0};

	control_mount_filesystems();
	if (control_module_loaded())
		control_fail("module-preloaded", EBUSY);

	/* Discovery prelude: identify exactly three backed QEMU transports. */
	control_load_module();
	control_discover_active(&active);
	control_unload_module();
	for (size_t index = 0; index < active.count; ++index)
		control_require_binding(active.names[index], false);

	/* Proof phase: block two valid devices before driver registration. */
	control_set_override(active.names[1], CONTROL_OVERRIDE "\n");
	control_set_override(active.names[2], CONTROL_OVERRIDE "\n");
	control_load_module();
	control_require_binding(active.names[0], true);
	control_require_binding(active.names[1], false);
	control_require_binding(active.names[2], false);

	/* Positive control: clearing each override makes reprobe bind it. */
	control_set_override(active.names[1], "\n");
	control_set_override(active.names[2], "\n");
	control_reprobe(active.names[1]);
	control_reprobe(active.names[2]);
	for (size_t index = 0; index < active.count; ++index)
		control_require_binding(active.names[index], true);

	control_unload_module();
	for (size_t index = 0; index < active.count; ++index)
		control_require_binding(active.names[index], false);

	dprintf(
		STDOUT_FILENO,
		"MAX77705_DRIVER_OVERRIDE_QEMU result=PASS target=%s "
		"blocked=%s,%s active=%zu\n",
		active.names[0],
		active.names[1],
		active.names[2],
		active.count);
	sync();
	control_park();
}
