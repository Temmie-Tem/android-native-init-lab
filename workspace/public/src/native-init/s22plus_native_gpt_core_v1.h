/* H0 prospective fixed FYG8 GPT reservation. No live authority.
 * The caller binds the exact original/proposed private byte arrays, endpoint
 * and one-shot intent. Each write is one call; no failed effect is retried.
 */
#ifndef S22PLUS_NATIVE_GPT_CORE_V1_H
#define S22PLUS_NATIVE_GPT_CORE_V1_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define GPT1_BLOCK 4096U
#define GPT1_PRIMARY (6U * GPT1_BLOCK)
#define GPT1_BACKUP (9U * GPT1_BLOCK)
#define GPT1_BYTES (GPT1_PRIMARY + GPT1_BACKUP)
#define GPT1_TOTAL_LBAS 62305280ULL

enum gpt1_mode { GPT1_OBSERVE = 0, GPT1_APPLY = 1, GPT1_RESTORE = 2 };
enum gpt1_error {
    GPT1_OK = 0, GPT1_BAD_MODE = 1, GPT1_READ = 2, GPT1_OUTSIDE = 3,
    GPT1_NO_COPY = 4, GPT1_NOT_ORIGINAL = 5, GPT1_WRITE = 6,
    GPT1_SYNC = 7, GPT1_READBACK = 8, GPT1_FINAL = 9
};
enum gpt1_event { GPT1_INTENT = 1, GPT1_COMPLETE = 2, GPT1_SKIP = 3 };

struct gpt1_io {
    void *context;
    /* Reads both fixed regions into an aligned GPT1_BYTES buffer. */
    int (*read)(void *, uint8_t *);
    /* Writes exactly one aligned block at the given real LU0 LBA. */
    int (*write)(void *, uint64_t, const uint8_t *);
    int (*sync)(void *);
    void (*event)(void *, unsigned, unsigned, uint64_t);
};

struct gpt1_result {
    unsigned writes_attempted, writes_completed, skipped;
    unsigned primary_kind, backup_kind, final_kind;
};

/* The only mutable blocks: backup table block 2, backup header, primary
 * table block 2, primary header. The original boot-entry block is outside. */
static const unsigned gpt1_offsets[4] = {
    GPT1_PRIMARY + GPT1_BLOCK, GPT1_PRIMARY + 8U * GPT1_BLOCK,
    3U * GPT1_BLOCK, GPT1_BLOCK
};
static const uint64_t gpt1_lbas[4] = {
    GPT1_TOTAL_LBAS - 8U, GPT1_TOTAL_LBAS - 1U, 3U, 1U
};

static unsigned gpt1_kind(const uint8_t *data, const uint8_t *original,
                         const uint8_t *proposed, size_t size) {
    if (!memcmp(data, original, size)) return 1U;
    if (!memcmp(data, proposed, size)) return 2U;
    return 0U;
}

static int gpt1_scope(const uint8_t *data, const uint8_t *original,
                      const uint8_t *proposed) {
    for (unsigned off = 0; off < GPT1_BYTES; off += GPT1_BLOCK) {
        unsigned allowed = 0;
        for (unsigned i = 0; i < 4; i++) allowed |= off == gpt1_offsets[i];
        if (!allowed && memcmp(data + off, original + off, GPT1_BLOCK)) return 0;
    }
    /* Even inside a mutable block, unrelated entry/header/padding bytes must
     * remain original. Partial intended bytes may be repaired; unrelated
     * media corruption is outside this reservation's recovery model. */
    for (unsigned i = 0; i < GPT1_BYTES; i++)
        if (original[i] == proposed[i] && data[i] != original[i]) return 0;
    return 1;
}

static int gpt1_copies(const uint8_t *data, const uint8_t *original,
                       const uint8_t *proposed, struct gpt1_result *r) {
    r->primary_kind = gpt1_kind(data, original, proposed, GPT1_PRIMARY);
    r->backup_kind = gpt1_kind(data + GPT1_PRIMARY, original + GPT1_PRIMARY,
                             proposed + GPT1_PRIMARY, GPT1_BACKUP);
    r->final_kind = gpt1_kind(data, original, proposed, GPT1_BYTES);
    return r->primary_kind || r->backup_kind;
}

/* work and expected are distinct aligned GPT1_BYTES buffers. Unknown changes
 * inside the four mutable blocks are repairable only with one exact surviving
 * original/proposed copy and all other captured bytes unchanged. */
static enum gpt1_error gpt1_execute(enum gpt1_mode mode, const struct gpt1_io *io,
        const uint8_t *original, const uint8_t *proposed, uint8_t *work,
        uint8_t *expected, struct gpt1_result *r) {
    memset(r, 0, sizeof(*r));
    if (mode < GPT1_OBSERVE || mode > GPT1_RESTORE) return GPT1_BAD_MODE;
    if (io->read(io->context, work)) return GPT1_READ;
    if (!gpt1_scope(work, original, proposed)) return GPT1_OUTSIDE;
    if (!gpt1_copies(work, original, proposed, r)) return GPT1_NO_COPY;
    if (mode == GPT1_OBSERVE) return GPT1_OK;
    if (mode == GPT1_APPLY && r->final_kind != 1U) return GPT1_NOT_ORIGINAL;
    const uint8_t *target = mode == GPT1_APPLY ? proposed : original;
    /* Never overwrite the only valid copy first. Repair the other side. */
    unsigned first = r->primary_kind ? 0U : 2U;
    memcpy(expected, work, GPT1_BYTES);
    for (unsigned ordinal = 0; ordinal < 4; ordinal++) {
        unsigned i = (first + ordinal) % 4U, off = gpt1_offsets[i];
        if (!memcmp(expected + off, target + off, GPT1_BLOCK)) {
            r->skipped++;
            io->event(io->context, GPT1_SKIP, ordinal, gpt1_lbas[i]);
            continue;
        }
        io->event(io->context, GPT1_INTENT, ordinal, gpt1_lbas[i]);
        r->writes_attempted++;
        if (io->write(io->context, gpt1_lbas[i], target + off)) return GPT1_WRITE;
        if (io->sync(io->context)) return GPT1_SYNC;
        memcpy(expected + off, target + off, GPT1_BLOCK);
        if (io->read(io->context, work)) return GPT1_READ;
        if (memcmp(work, expected, GPT1_BYTES)) return GPT1_READBACK;
        if (!gpt1_copies(work, original, proposed, r)) return GPT1_NO_COPY;
        r->writes_completed++;
        io->event(io->context, GPT1_COMPLETE, ordinal, gpt1_lbas[i]);
    }
    if (io->read(io->context, work)) return GPT1_READ;
    if (memcmp(work, target, GPT1_BYTES)) return GPT1_FINAL;
    (void)gpt1_copies(work, original, proposed, r);
    return GPT1_OK;
}
#endif
