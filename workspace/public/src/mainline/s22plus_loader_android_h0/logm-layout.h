/* SPDX-License-Identifier: GPL-2.0-only */
/* Exact shared live-FDT eligibility, unchanged from LA002. */
#ifndef S22_LOGM_LAYOUT_H
#define S22_LOGM_LAYOUT_H
static int equal_bytes(const void *a, const void *b, unsigned n)
{
    const unsigned char *x = a, *y = b;
    for (unsigned i = 0; i < n; ++i) if (x[i] != y[i]) return 0;
    return 1;
}

static int property(const void *fdt, int node, const char *name,
                    const void *expected, unsigned size)
{
    int length;
    const void *p = fdt_getprop(fdt, node, name, &length);
    if (!p || length != (int)size || !equal_bytes(p, expected, size)) return 0;
    unsigned count = 0;
    int offset;
    fdt_for_each_property_offset(offset, fdt, node) {
        const char *key;
        if (!fdt_getprop_by_offset(fdt, offset, &key, &length)) return 0;
        unsigned i = 0;
        while (key[i] && name[i] && key[i] == name[i]) ++i;
        if (!key[i] && !name[i]) ++count;
    }
    return offset == -FDT_ERR_NOTFOUND && count == 1;
}

static int absent(const void *fdt, int node, const char *name)
{
    int length;
    return !fdt_getprop(fdt, node, name, &length) && length == -FDT_ERR_NOTFOUND;
}

static int active(const void *fdt, int node)
{
    return node >= 0 && (absent(fdt, node, "status") ||
        property(fdt, node, "status", "okay", 5) || property(fdt, node, "status", "ok", 3));
}

static int named(const void *fdt, int node, const char *name, unsigned size)
{
    int length;
    const char *p = fdt_get_name(fdt, node, &length);
    return p && length == (int)size && equal_bytes(p, name, size);
}

static int log_layout(const void *fdt)
{
    static const unsigned char log_reg[16] = {0,0,0,8,0,0x20,0,0,0,0,0,0,0,0x20,0,0};
    static const unsigned char reserved_reg[16] = {0,0,0,8,0,0x1f,0xf0,0,0,0,0,0,0,0x90,0x10,0};
    static const unsigned char two[4] = {0,0,0,2}, three[4] = {0,0,0,3};
    const char *log_name = "samsung,kernel_log_buf", *reserved_name = "sec_debug_region_log@8001FF000";
    int log = fdt_path_offset(fdt, "/soc/samsung,kernel_log_buf");
    int reserved = fdt_path_offset(fdt, "/reserved-memory/sec_debug_region_log@8001FF000");
    if (!active(fdt, log) || !active(fdt, reserved) ||
        !active(fdt, fdt_path_offset(fdt, "/soc")) ||
        !active(fdt, fdt_path_offset(fdt, "/reserved-memory")) ||
        !named(fdt, log, log_name, 22) || !named(fdt, reserved, reserved_name, 30) ||
        !property(fdt, log, "compatible", "samsung,kernel_log_buf", 23) ||
        !property(fdt, reserved, "compatible", "samsung,carve-out", 18) ||
        !property(fdt, log, "reg", log_reg, 16) ||
        !property(fdt, reserved, "reg", reserved_reg, 16) ||
        !property(fdt, log, "#address-cells", two, 4) ||
        !property(fdt, log, "#size-cells", two, 4) ||
        !property(fdt, log, "sec,strategy", three, 4) ||
        !property(fdt, log, "sec,use-partial_reserved_mem", "", 0) ||
        !property(fdt, log, "sec,use-last_kmsg_compression", "", 0) ||
        !property(fdt, log, "sec,last_kmsg_compressor", "zstd", 5) ||
        !absent(fdt, reserved, "no-map") || !absent(fdt, reserved, "reusable")) return 0;
    int length;
    const fdt32_t *ref = fdt_getprop(fdt, log, "memory-region", &length);
    if (!ref || length != 4 || !property(fdt, log, "memory-region", ref, 4)) return 0;
    uint32_t phandle = fdt32_to_cpu(*ref);
    if (!phandle || phandle == 0xffffffffU || fdt_get_phandle(fdt, reserved) != phandle) return 0;
    unsigned log_count = 0, name_count = 0, reserved_count = 0, refs = 0;
    int depth = 0, node = -1;
    while ((node = fdt_next_node(fdt, node, &depth)) >= 0) {
        if (!absent(fdt, node, "linux,phandle") || !absent(fdt, node, "ibm,phandle")) return 0;
        int phandle_size;
        const void *handle = fdt_getprop(fdt, node, "phandle", &phandle_size);
        if (handle && !property(fdt, node, "phandle", handle, 4)) return 0;
        if (fdt_node_check_compatible(fdt, node, log_name) == 0) ++log_count;
        if (named(fdt, node, log_name, 22)) ++name_count;
        if (named(fdt, node, reserved_name, 30)) ++reserved_count;
        if (fdt_get_phandle(fdt, node) == phandle) ++refs;
    }
    return node == -FDT_ERR_NOTFOUND && log_count == 1 && name_count == 1 &&
        reserved_count == 1 && refs == 1;
}

#endif
