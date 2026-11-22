/* SPDX-License-Identifier: GPL-2.0-only */
/* Fixed firmware spelling produced by the IYC2 formatter. Other spellings
 * can still boot, with the optional recorder disabled. */
static int y2q_log_argument(const char *text, int length)
{
    static const char expected[] = "sec_log=0x200000@0x9f200000";
    int pos = 0, seen = 0;
    if (!text || length < 1 || length > 8192 || text[length-1] ||
        memchr(text, 0, length-1))
        return 0;
    while (pos < length-1) {
        int start, quoted = 0;
        while (pos < length-1 && (text[pos] == ' ' || text[pos] == '\t'))
            pos++;
        start = pos;
        while (pos < length-1) {
            unsigned char c = text[pos];
            if (c == '"') quoted = !quoted;
            if (!quoted && (c == ' ' || c == '\t')) break;
            if (c < 32 || c > 126) return 0;
            pos++;
        }
        if (quoted) return 0;
        int n = pos-start;
        const char *word = text+start;
        if ((n == 2 && !memcmp(word, "--", 2)) ||
            (n == 4 && !memcmp(word, "\"--\"", 4)))
            break;
        if (n && *word == '"') { word++; n--; }
        if (n < 7 || (memcmp(word,"sec_log",7) && memcmp(word,"sec-log",7)))
            continue;
        if (n > 7 && word[7] != '=' && word[7] != '"') continue;
        if (seen || word != text+start || n != sizeof(expected)-1)
            return 0;
        for (int i=0; i<n; i++) {
            char c = word[i];
            if (i >= 8 && c >= 'A' && c <= 'F') c += 'a'-'A';
            if (c != expected[i]) return 0;
        }
        seen = 1;
    }
    return seen;
}

/* The diagnostic uses one stock argument property and a uniquely described
 * RAM owner. Reject duplicates instead of selecting the first encoding. */
static int y2q_unique_fields(const void *fdt, int node, const char *fields)
{
    int prop;
    unsigned seen = 0;
    fdt_for_each_property_offset(prop, fdt, node) {
        const char *key;
        int length;
        if (!fdt_getprop_by_offset(fdt, prop, &key, &length) || length < 0)
            return 0;
        unsigned bit = 1;
        for (const char *field = fields; *field; field += strlen(field)+1, bit <<= 1) {
            if (strcmp(key, field)) continue;
            if (seen & bit) return 0;
            seen |= bit;
        }
    }
    return prop == -FDT_ERR_NOTFOUND;
}

static int y2q_record_permission(const void *stock, void *out, const struct spans *banks)
{
    int chosen = fdt_path_offset(stock, "/chosen"), len;
    static const char arg_keys[] = "bootargs\0status\0";
    static const char owner_keys[] = "reg\0compatible\0no-map\0status\0";
    if (chosen < 0 || !y2q_unique_fields(stock, chosen, arg_keys)) return 0;
    const char *args = fdt_getprop(stock, chosen, "bootargs", &len);
    if (!y2q_log_argument(args, len)) return 0;
    int node = fdt_path_offset(stock, "/reserved-memory/sec_debug_region@0");
    if (node < 0 || !y2q_unique_fields(stock, node, owner_keys) || !enabled(stock, node) ||
        !named(stock, node, "compatible", "removed-dma-pool") ||
        !fdt_getprop(stock, node, "no-map", &len) || len)
        return 0;
    const fdt32_t *reg = fdt_getprop(stock, node, "reg", &len);
    if (!reg || len != 16 || pair(reg) != 0x9f000000 || pair(reg+2) != 0x800000)
        return 0;
    int in_bank = 0;
    for (unsigned i = 0; i < banks->count; i++)
        if (banks->v[i].a <= 0x9f200000 && 0x9f400000 <= banks->v[i].b)
            in_bank = 1;
    if (!in_bank) return 0;
    chosen = fdt_path_offset(out, "/chosen");
    return fdt_setprop(out, chosen, "linux,y2q-log-geometry-v1", NULL, 0);
}
