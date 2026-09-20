/* H0 virt-board substitute ONLY for UFS/sysfs discovery and module insertion.
 * Real ARM64 block ioctls, sealed GPT reads and every installer/handoff syscall
 * remain unchanged. A production build never defines S22_DEBIAN_VIRT_TEST. */
static int fs1_resolve(struct fs1_endpoint *e) {
    uint64_t value;
    if (!realpath("/sys/class/block/vda", e->parent) ||
        !realpath("/sys/class/block/vda41", e->sys_partition)) return ENODEV;
    if (strncmp(e->parent, "/sys/devices/platform/", 22) ||
        !strstr(e->parent, "/virtio")) return EPROTO;
    if (fs1_number(e->parent, "size", &value) || value != FS1_GPT_BLOCKS * 8U ||
        fs1_number(e->parent, "queue/logical_block_size", &value) || value != FS1_BLOCK ||
        fs1_number(e->sys_partition, "partition", &value) || value != 41U ||
        fs1_number(e->sys_partition, "start", &value) || value != FS1_FIRST_LBA * 8U ||
        fs1_number(e->sys_partition, "size", &value) || value != FS1_BLOCKS * 8U ||
        fs1_number(e->sys_partition, "ro", &value) || value != 0) return EPROTO;
    char user[PATH_MAX];
    if (!realpath("/sys/class/block/vda40", user)) return ENODEV;
    if (fs1_number(user, "start", &value) || value != 3726848ULL * 8U ||
        fs1_number(user, "size", &value) || value != 67108864ULL ||
        fs1_device_number(e->parent, &e->disk) ||
        fs1_device_number(e->sys_partition, &e->partition)) return EPROTO;
    dev_t userdata;
    if (fs1_device_number(user, &userdata) || fs1_not_mounted(userdata) ||
        fs1_not_mounted(e->partition)) return EBUSY;
    return 0;
}
