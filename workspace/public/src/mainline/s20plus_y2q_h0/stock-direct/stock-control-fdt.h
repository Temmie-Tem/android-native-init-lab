/* SPDX-License-Identifier: GPL-2.0-only */
/* Only the private copy is changed. The incoming firmware tree is read-only. */
#include "y2q-pair-data.h"
char *y2q_stock_handoff_fdt(const void *stock, void *out)
{
    static const char property[] = "codex,y2q-stock-direct-v1";
    static const char initial[] = STOCK_CONTROL_NONCE ":U";
    char *value;
    int node, len;

    if (fdt_open_into(stock, out, 0x200000))
        return NULL;
    node = fdt_path_offset(out, "/chosen");
    if (node < 0 || fdt_getprop(out, node, property, &len) || len != -FDT_ERR_NOTFOUND)
        return NULL;
    if (fdt_setprop(out, node, property, initial, sizeof(initial)) || fdt_pack(out))
        return NULL;
    node = fdt_path_offset(out, "/chosen");
    value = (char *)fdt_getprop(out, node, property, &len);
    if (!value || len != sizeof(initial) || memcmp(value, initial, sizeof(initial)))
        return NULL;
    return value + sizeof(initial) - 2;
}
