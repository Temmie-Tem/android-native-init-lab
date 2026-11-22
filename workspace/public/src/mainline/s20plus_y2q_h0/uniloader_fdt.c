/* SPDX-License-Identifier: GPL-2.0-only */
#include <lib/libfdt/libfdt.h>
#include "uniloader_layout.h"
#include "uniloader_marker.h"

void *y2q_mark_fdt(const void *original, void *scratch)
{
    if (fdt_open_into(original, scratch, Y2Q_FDT_CAPACITY))
        return NULL;
    int chosen = fdt_path_offset(scratch, "/chosen");
    if (chosen < 0 || fdt_setprop_string(scratch, chosen, Y2Q_MARKER_PROPERTY, Y2Q_MARKER))
        return NULL;
    if (fdt_pack(scratch))
        return NULL;
    return scratch;
}
