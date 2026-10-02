/* Included only in the separately built, pinned e2fsprogs journal.c.
 * GPL-2.0-or-later, matching the upstream replay implementation.
 * No ordinary e2fsck entry, options, configuration, repair or mount path.
 */
#include <fcntl.h>
#include <stdint.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include "s22plus_journal_replay_seal_v1.h"
#include "s22plus_native_ext4_core_v1.h"

static int jr_fd = -1, jr_phase;
static unsigned long long jr_writes, jr_bytes;
static struct struct_io_manager jr_manager;
static blk64_t *jr_journal_blocks;
static unsigned jr_journal_count;
static uint64_t jr_journal_offset;

static errcode_t jr_fail(errcode_t error)
{
    if (!jr_io_error) jr_io_error = error ? error : EIO;
    return jr_io_error;
}

static errcode_t jr_range(uint64_t offset, uint64_t length)
{
    if (!length || offset > JR_BYTES || length > JR_BYTES - offset)
        return jr_fail(EOVERFLOW);
    return 0;
}

static errcode_t jr_read_bytes(uint64_t offset, size_t size, void *buffer)
{
    ssize_t got;
    if (jr_io_error || jr_range(offset, size)) return jr_io_error;
    got = pread(jr_fd, buffer, size, (off_t)offset);
    if (got != (ssize_t)size) return jr_fail(got < 0 ? errno : EIO);
    return 0;
}

static int jr_compare_blocks(const void *a, const void *b)
{
    blk64_t x = *(const blk64_t *)a, y = *(const blk64_t *)b;
    return x < y ? -1 : x > y;
}

static errcode_t jr_write_bytes(uint64_t offset, size_t size, const void *buffer)
{
    ssize_t put;
    blk64_t block = offset / FS1_BLOCK;
    if (jr_io_error || jr_range(offset, size)) return jr_io_error;
    if (jr_phase == 1) {
        if (size != FS1_BLOCK || offset % FS1_BLOCK ||
            bsearch(&block, jr_journal_blocks, jr_journal_count,
                    sizeof(block), jr_compare_blocks)) return jr_fail(EPERM);
    } else if (jr_phase == 2) {
        if (size != FS1_BLOCK || offset != jr_journal_offset) return jr_fail(EPERM);
    } else if (jr_phase == 3) {
        if (offset != 1024 || size != 1024) return jr_fail(EPERM);
    } else return jr_fail(EPERM);
    ++jr_writes; /* An attempted short/failed write is still consumed. */
    put = pwrite(jr_fd, buffer, size, (off_t)offset);
    if (put != (ssize_t)size) return jr_fail(put < 0 ? errno : EIO);
    jr_bytes += size;
    return 0;
}

static errcode_t jr_open(const char *name, int flags, io_channel *out)
{
    struct stat st;
    uint64_t size = 0;
    io_channel c;
    if (jr_fd != -1 || strcmp(name, JR_DEVICE) || !(flags & IO_FLAG_RW)) return EINVAL;
    jr_fd = open(name, O_RDWR | O_EXCL | O_NOFOLLOW | O_CLOEXEC);
    if (jr_fd < 0) return errno;
    if (fstat(jr_fd, &st)) goto reject;
#if JR_FIXTURE_REGULAR
    if (!S_ISREG(st.st_mode) || st.st_nlink != 1) goto reject;
    size = st.st_size;
#else
    if (!S_ISBLK(st.st_mode) || ioctl(jr_fd, 0x80081272UL, &size)) goto reject;
#endif
    if (size != JR_BYTES) goto reject;
    c = calloc(1, sizeof(*c));
    if (!c) goto reject;
    c->magic = EXT2_ET_MAGIC_IO_CHANNEL;
    c->manager = &jr_manager; c->name = strdup(name);
    if (!c->name) { free(c); goto reject; }
    c->block_size = 1024; c->refcount = 1;
    c->flags = CHANNEL_FLAGS_WRITETHROUGH | CHANNEL_FLAGS_NODISCARD | CHANNEL_FLAGS_NOZEROOUT;
    *out = c;
    return 0;
reject:
    close(jr_fd); jr_fd = -1;
    return EINVAL;
}

/* No hidden write, flush, retry or repair during resource destruction. */
static errcode_t jr_close(io_channel c)
{
    int rc;
    if (--c->refcount) return 0;
    rc = close(jr_fd); jr_fd = -1;
    free(c->name); free(c);
    return rc ? jr_fail(errno) : jr_io_error;
}

static errcode_t jr_set_block(io_channel c, int size)
{
    if (size != 1024 && size != FS1_BLOCK) return jr_fail(EINVAL);
    c->block_size = size;
    return 0;
}

static errcode_t jr_transfer(io_channel c, unsigned long long block, int count,
                             void *data, int writing)
{
    uint64_t size = count < 0 ? -(int64_t)count : (uint64_t)count * c->block_size;
    if (block > JR_BYTES / c->block_size || size > 1024 * 1024)
        return jr_fail(EOVERFLOW);
    return writing ? jr_write_bytes(block * c->block_size, size, data) :
                     jr_read_bytes(block * c->block_size, size, data);
}

static errcode_t jr_read64(io_channel c, unsigned long long b, int n, void *d)
{ return jr_transfer(c, b, n, d, 0); }
static errcode_t jr_write64(io_channel c, unsigned long long b, int n, const void *d)
{ return jr_transfer(c, b, n, (void *)d, 1); }
static errcode_t jr_read(io_channel c, unsigned long b, int n, void *d)
{ return jr_read64(c, b, n, d); }
static errcode_t jr_write(io_channel c, unsigned long b, int n, const void *d)
{ return jr_write64(c, b, n, d); }
static errcode_t jr_flush(io_channel c EXT2FS_ATTR((unused)))
{
    if (jr_io_error) return jr_io_error;
    return fsync(jr_fd) ? jr_fail(errno) : 0;
}
static struct struct_io_manager jr_manager = {
    .magic = EXT2_ET_MAGIC_IO_MANAGER, .name = "s22-strict-uncached",
    .open = jr_open, .close = jr_close, .set_blksize = jr_set_block,
    .read_blk = jr_read, .write_blk = jr_write, .flush = jr_flush,
    .read_blk64 = jr_read64, .write_blk64 = jr_write64
};

static void jr_set32(uint8_t *p, uint32_t v)
{ for (unsigned n = 0; n != 4; ++n) p[n] = (uint8_t)(v >> (8 * n)); }

static int jr_super_ok(const uint8_t raw[1024], int recover)
{
    uint8_t normalized[1024];
    if (fs1_u32(raw + 0x3fc) != fs1_crc32c(raw, 0x3fc) ||
        fs1_u32(raw + 0x60) != (FS1_INCOMPAT | (recover ? 4U : 0U))) return 0;
    memcpy(normalized, raw, sizeof(normalized));
    jr_set32(normalized + 0x60, FS1_INCOMPAT);
    jr_set32(normalized + 0x3fc, fs1_crc32c(normalized, 0x3fc));
    return fs1_superblock(normalized, sizeof(normalized), jr_uuid, JR_BLOCKS);
}

static errcode_t jr_load(journal_t *j)
{
    journal_superblock_t *s;
    errcode_t rc;
    unsigned long long physical;
    ll_rw_block(REQ_OP_READ, 0, 1, &j->j_sb_buffer);
    if (jr_io_error || j->j_sb_buffer->b_err) return EIO;
    s = j->j_superblock;
    /* Reject every input that upstream journal_load could normalize/repair. */
    if (s->s_header.h_magic != htonl(JBD2_MAGIC_NUMBER) ||
        s->s_header.h_blocktype != htonl(JBD2_SUPERBLOCK_V2) ||
        ntohl(s->s_nr_users) != 1 || memcmp(s->s_uuid, jr_uuid, 16) ||
        s->s_errno || s->s_feature_compat || s->s_feature_ro_compat ||
        (ntohl(s->s_feature_incompat) & ~(JBD2_FEATURE_INCOMPAT_REVOKE |
          JBD2_FEATURE_INCOMPAT_64BIT | JBD2_FEATURE_INCOMPAT_CSUM_V2 |
          JBD2_FEATURE_INCOMPAT_CSUM_V3)) ||
        !(ntohl(s->s_feature_incompat) & (JBD2_FEATURE_INCOMPAT_CSUM_V2 |
                                         JBD2_FEATURE_INCOMPAT_CSUM_V3)) ||
        ntohl(s->s_first) != 1 || ntohl(s->s_maxlen) != j->j_total_len ||
        j->j_total_len != (unsigned)ext2fs_default_journal_size(JR_BLOCKS) ||
        j->j_total_len > 262144 ||
        !j->j_inode || EXT2_I_SIZE(&j->j_inode->i_ext2) != j->j_total_len * (uint64_t)FS1_BLOCK ||
        ntohl(s->s_start) >= j->j_total_len) return EINVAL;
    rc = e2fsck_journal_load(j);
    if (rc || jr_io_error) return rc ? rc : jr_io_error;
    jr_journal_count = j->j_total_len;
    jr_journal_blocks = calloc(jr_journal_count, sizeof(*jr_journal_blocks));
    if (!jr_journal_blocks) return ENOMEM;
    for (unsigned n = 0; n != jr_journal_count; ++n) {
        if (jbd2_journal_bmap(j, n, &physical) || !physical || physical >= JR_BLOCKS)
            return EINVAL;
        jr_journal_blocks[n] = physical;
    }
    qsort(jr_journal_blocks, jr_journal_count, sizeof(*jr_journal_blocks), jr_compare_blocks);
    for (unsigned n = 1; n != jr_journal_count; ++n)
        if (jr_journal_blocks[n] == jr_journal_blocks[n-1]) return EINVAL;
    jr_journal_offset = j->j_sb_buffer->b_blocknr * (uint64_t)FS1_BLOCK;
    return 0;
}

int s22plus_strict_journal_main(int argc, char **argv EXT2FS_ATTR((unused)))
{
    e2fsck_t ctx = NULL;
    journal_t *journal = NULL;
    uint8_t before[1024], after[1024], final[1024], check[FS1_BLOCK], primary[FS1_BLOCK];
    errcode_t rc = EINVAL, close_rc;
    unsigned stage = 0;
    int revoke_ready = 0, record_cache = 0, table_cache = 0;
    setvbuf(stdout, NULL, _IONBF, 0); setvbuf(stderr, NULL, _IONBF, 0);
    if (argc != 1) goto done;
    rc = e2fsck_allocate_context(&ctx);
    if (rc) goto done;
    ctx->program_name = "s22-strict-replay";
    ctx->device_name = strdup(JR_DEVICE); ctx->filesystem_name = strdup(JR_DEVICE);
    if (!ctx->device_name || !ctx->filesystem_name) { rc = ENOMEM; goto done; }
    ctx->options = E2F_OPT_NO; /* Defensive: an unreachable prompt must not repair. */
    rc = ext2fs_open(JR_DEVICE, EXT2_FLAG_RW | EXT2_FLAG_EXCLUSIVE |
            EXT2_FLAG_64BITS | EXT2_FLAG_SKIP_MMP, 0, FS1_BLOCK, &jr_manager, &ctx->fs);
    if (rc) goto done;
    ctx->fs->priv_data = ctx;
    rc = jr_read_bytes(1024, sizeof(before), before);
    if (rc || !jr_super_ok(before, 1)) { if (!rc) rc = EINVAL; goto done; }
    stage = 1;
    rc = e2fsck_get_journal(ctx, &journal);
    if (rc) goto done;
    rc = jr_load(journal);
    if (rc) goto done;
    rc = jbd2_journal_init_revoke_record_cache();
    if (rc) goto done;
    record_cache = 1;
    rc = jbd2_journal_init_revoke_table_cache();
    if (rc) goto done;
    table_cache = 1;
    rc = jbd2_journal_init_revoke(journal, 1024);
    if (rc) goto done;
    revoke_ready = 1; stage = 2; jr_phase = 1;
    rc = -jbd2_journal_recover(journal);
    jr_phase = 0;
    if (rc || jr_io_error || journal->j_failed_commit) { if (!rc) rc = EIO; goto done; }
    rc = jr_flush(ctx->fs->io);
    if (rc) goto done;
    stage = 3;
    rc = jr_read_bytes(0, sizeof(primary), primary);
    memcpy(after, primary + 1024, sizeof(after));
    if (rc || !jr_super_ok(after, 1)) { if (!rc) rc = EINVAL; goto done; }
    /* No orphan cleanup, group-descriptor writes, repair, restart or passes. */
    journal->j_superblock->s_start = 0;
    journal->j_superblock->s_sequence = htonl(journal->j_transaction_sequence);
    e2fsck_journal_sb_csum_set(journal, journal->j_superblock);
    jr_phase = 2;
    rc = jr_write_bytes(journal->j_sb_buffer->b_blocknr * (uint64_t)FS1_BLOCK,
                         FS1_BLOCK, journal->j_sb_buffer->b_data);
    if (!rc) rc = jr_flush(ctx->fs->io);
    jr_phase = 0;
    if (rc) goto done;
    rc = jr_read_bytes(journal->j_sb_buffer->b_blocknr * (uint64_t)FS1_BLOCK,
                        sizeof(check), check);
    if (rc || memcmp(check, journal->j_sb_buffer->b_data, sizeof(check))) {
        if (!rc) rc = jr_fail(EIO); goto done;
    }
    stage = 4;
    memcpy(final, after, sizeof(final));
    jr_set32(final + 0x60, FS1_INCOMPAT);
    jr_set32(final + 0x3fc, fs1_crc32c(final, 0x3fc));
    jr_phase = 3;
    rc = jr_write_bytes(1024, sizeof(final), final);
    if (!rc) rc = jr_flush(ctx->fs->io);
    jr_phase = 0;
    if (rc) goto done;
    memcpy(primary + 1024, final, sizeof(final));
    rc = jr_read_bytes(0, sizeof(check), check);
    if (rc || memcmp(check, primary, sizeof(check)) || !jr_super_ok(check + 1024, 0)) {
        if (!rc) rc = jr_fail(EIO); goto done;
    }
    stage = 5;
done:
    jr_phase = 0;
    if (revoke_ready) jbd2_journal_destroy_revoke(journal);
    if (record_cache) jbd2_journal_destroy_revoke_record_cache();
    if (table_cache) jbd2_journal_destroy_revoke_table_cache();
    if (journal) e2fsck_journal_release(ctx, journal, 0, 1);
    free(jr_journal_blocks);
    if (ctx && ctx->fs) {
        /* free() uses our no-flush close. Never ext2fs_close/flush on error. */
        ext2fs_free(ctx->fs); ctx->fs = NULL;
    }
    if (jr_fd >= 0) {
        close_rc = close(jr_fd); jr_fd = -1;
        if (close_rc) jr_fail(errno);
    }
    if (ctx) e2fsck_free_context(ctx);
    if (jr_io_error && !rc) rc = jr_io_error;
    printf("S22_JOURNAL_REPLAY_V1 stage=%u writes=%llu bytes=%llu error=%ld io_error=%ld complete=%u\n",
           stage, jr_writes, jr_bytes, (long)rc, (long)jr_io_error, !rc && stage == 5);
    return !rc && stage == 5 ? 0 : 8;
}
