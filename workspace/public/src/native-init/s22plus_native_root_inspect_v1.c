/* Fixed native_data inspection. No payload execution, filesystem repair,
 * extraction, writable mount or block-data write exists in this program.
 * BLKROSET protects only the sealed partition until the next kernel boot.
 */
#define FS1_READONLY_BINDING_ONLY
#ifdef S22_ROOT_INSPECT_VIRT_TEST
#define fs1_resolve fs1_unused_physical_resolve
#endif
#include "s22plus_native_ext4_v1.c"
#ifdef S22_ROOT_INSPECT_VIRT_TEST
#undef fs1_resolve
#include "../debian/s22plus_v1/device/virt-binding.inc.c"
#endif
#include "s22plus_native_root_inspect_seal_v1.h"
#include <stdarg.h>

_Static_assert(BLKROSET == 0x125d && BLKROGET == 0x125e, "target ARM64 block RO ioctls");

#define RI_MAX_ENTRIES 20000U
#define RI_MAX_DEPTH 32U
#define RI_MAX_BYTES (512ULL * 1024U * 1024U)
#define RI_MAX_TABLE (2U * 1024U * 1024U)
#define RI_FINDINGS 32U

static const char ri_work[] = "/s22-root-work/root-inspect-v1";
static const char ri_root[] = "/s22-root-work/root-inspect-v1/root";
static unsigned ri_stage, ri_reported;
static uint64_t ri_hashed_bytes;

/* Optional fixed-stage instrumentation for separately compiled diagnostics.
 * The ordinary inspector/probe retain their original paths and output. */
#ifndef RI_PROGRESS_BEGIN
#define RI_PROGRESS_BEGIN(name) ((void)0)
#define RI_PROGRESS_END(name) ((void)0)
#define RI_PROGRESS_ERROR(error) ((void)0)
#define RI_PROGRESS_CLEANUP(error) ((void)0)
#endif
#ifndef RI_PRE_MOUNT
#define RI_PRE_MOUNT(endpoint) 0
#endif

struct ri_counts { unsigned entries, files, directories, links, other; uint64_t bytes; };
struct ri_compare { unsigned expected, matched, missing, metadata, content;
                    unsigned boot_expected, boot_missing, boot_metadata, boot_content; };

static void ri_print(const char *format, ...) {
    va_list args; va_start(args, format);
    int rc = vprintf(format, args); va_end(args);
    if (rc < 0 || fflush(stdout)) _exit(120);
}

static void ri_digest(const uint8_t bytes[32], char out[65]) {
    static const char hex[] = "0123456789abcdef";
    for (unsigned i = 0; i < 32; ++i) { out[i*2] = hex[bytes[i] >> 4]; out[i*2+1] = hex[bytes[i] & 15]; }
    out[64] = 0;
}

static int ri_read(int fd, void *buffer, size_t length) {
    uint8_t *p = buffer;
    while (length) {
        ssize_t n = read(fd, p, length);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return n ? fs1_error() : EIO;
        p += n; length -= (size_t)n;
    }
    return 0;
}

static int ri_fd_identity(int fd, dev_t device, bool directory) {
    struct stat st;
    if (fstat(fd, &st)) return fs1_error();
    return st.st_dev == device && (directory ? S_ISDIR(st.st_mode) : S_ISREG(st.st_mode)) ? 0 : EPROTO;
}

/* Every parent is opened without following symlinks, including on 5.10 kernels
 * without usable openat2. A changed ancestor is observed, never traversed.
 */
static int ri_parent(int root, dev_t device, const char *path, char leaf[NAME_MAX+1]) {
    size_t length = strlen(path);
    if (!length || length >= PATH_MAX || path[0] == '/') { errno = EINVAL; return -1; }
    char copy[PATH_MAX]; memcpy(copy, path, length + 1);
    int fd = fcntl(root, F_DUPFD_CLOEXEC, 3);
    if (fd < 0) return -1;
    char *part = copy;
    for (unsigned depth = 0; depth < RI_MAX_DEPTH; ++depth) {
        char *slash = strchr(part, '/'); if (slash) *slash = 0;
        if (!*part || strlen(part) > NAME_MAX || !strcmp(part, ".") || !strcmp(part, "..")) {
            (void)close(fd); errno = EINVAL; return -1;
        }
        if (!slash) { memcpy(leaf, part, strlen(part) + 1); return fd; }
        int next = openat(fd, part, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
        int error = next < 0 ? fs1_error() : ri_fd_identity(next, device, true);
        if (close(fd) && !error) error = fs1_error();
        if (error) { if (next >= 0) (void)close(next); errno = error; return -1; }
        fd = next; part = slash + 1;
    }
    (void)close(fd); errno = EOVERFLOW; return -1;
}

static int ri_hash_file(int parent, const char *name, dev_t device, uint64_t size, uint8_t hash[32]) {
    if (size > RI_MAX_BYTES || ri_hashed_bytes > RI_MAX_BYTES - size) return EFBIG;
    int fd = openat(parent, name, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0) return fs1_error();
    int error = ri_fd_identity(fd, device, false);
    struct stat before, after;
    if (!error && (fstat(fd, &before) || before.st_size < 0 || (uint64_t)before.st_size != size)) error = EPROTO;
    struct s22plus_max77705_runtime_sha256 h; s22plus_max77705_runtime_sha256_init(&h);
    uint8_t buffer[65536]; uint64_t used = 0;
    while (!error && used < size) {
        size_t amount = size - used < sizeof(buffer) ? (size_t)(size - used) : sizeof(buffer);
        error = ri_read(fd, buffer, amount);
        if (!error) { s22plus_max77705_runtime_sha256_update(&h, buffer, amount); used += amount; }
    }
    uint8_t extra;
    if (!error && read(fd, &extra, 1) != 0) error = EIO;
    if (!error && (fstat(fd, &after) || before.st_dev != after.st_dev || before.st_ino != after.st_ino ||
        before.st_mode != after.st_mode || before.st_size != after.st_size ||
        before.st_mtim.tv_sec != after.st_mtim.tv_sec || before.st_mtim.tv_nsec != after.st_mtim.tv_nsec ||
        before.st_ctim.tv_sec != after.st_ctim.tv_sec || before.st_ctim.tv_nsec != after.st_ctim.tv_nsec)) error = EPROTO;
    if (close(fd) && !error) error = fs1_error();
    if (!error) { s22plus_max77705_runtime_sha256_final(&h, hash); ri_hashed_bytes += size; }
    return error;
}

/* A small, bounded sample identifies mismatches by expected path. Unknown
 * filenames and all file contents remain digest-only, including credentials.
 */
static void ri_finding(const char *path, const char *kind) {
    if (ri_reported >= RI_FINDINGS) return;
    uint8_t digest[32]; char hex[65];
    struct s22plus_max77705_runtime_sha256 h; s22plus_max77705_runtime_sha256_init(&h);
    s22plus_max77705_runtime_sha256_update(&h, (const uint8_t *)path, strlen(path));
    s22plus_max77705_runtime_sha256_final(&h, digest); ri_digest(digest, hex);
    ri_print("RI1_FINDING path_sha256=%s kind=%s\n", hex, kind); ++ri_reported;
}

static int ri_compare_tree(int root, dev_t device, struct ri_compare *c) {
    if (ri_table_size < 12 || ri_table_size > RI_MAX_TABLE) return EINVAL;
    int fd = fs1_pin_file("/s22-root-inspect.table", ri_table_size, ri_table_sha256, false);
    if (fd < 0) return fs1_error();
    uint8_t *table = malloc(ri_table_size);
    int error = table ? ri_read(fd, table, ri_table_size) : ENOMEM;
    if (close(fd) && !error) error = fs1_error();
    if (error) { free(table); return error; }
    if (memcmp(table, "S22RI01\0", 8) || fs1_u32(table + 8) != ri_table_count ||
        !ri_table_count || ri_table_count > RI_MAX_ENTRIES) { free(table); return EPROTO; }
    size_t offset = 12;
    char previous[PATH_MAX] = {0};
    for (unsigned i = 0; i < ri_table_count && !error; ++i) {
        if (offset > ri_table_size || ri_table_size - offset < 57) { error = EPROTO; break; }
        const uint8_t *record = table + offset; offset += 57;
        unsigned mode = fs1_u32(record), uid = fs1_u32(record+4), gid = fs1_u32(record+8);
        uint64_t size = fs1_u64(record+12);
        unsigned plen = fs1_u16(record+20), llen = fs1_u16(record+22), critical = record[56];
        if (!plen || plen >= PATH_MAX || llen >= PATH_MAX || critical > 1 ||
            (size_t)plen + llen > ri_table_size - offset) { error = EPROTO; break; }
        char path[PATH_MAX], link[PATH_MAX], leaf[NAME_MAX+1];
        memcpy(path, table + offset, plen); path[plen] = 0; offset += plen;
        memcpy(link, table + offset, llen); link[llen] = 0; offset += llen;
        if (strlen(path) != plen || strlen(link) != llen || strcmp(previous, path) >= 0 ||
            !(S_ISDIR(mode) || S_ISREG(mode) || S_ISLNK(mode)) ||
            (!S_ISLNK(mode) && llen)) { error = EPROTO; break; }
        memcpy(previous, path, plen+1); ++c->expected; c->boot_expected += critical;
        int parent = ri_parent(root, device, path, leaf);
        if (parent < 0) {
            if (errno == ENOENT) { ++c->missing; c->boot_missing += critical; ri_finding(path,"missing"); }
            else if (errno == ELOOP || errno == ENOTDIR) { ++c->metadata; c->boot_metadata += critical; ri_finding(path,"ancestor"); }
            else error = fs1_error();
            continue;
        }
        struct stat st;
        if (fstatat(parent, leaf, &st, AT_SYMLINK_NOFOLLOW)) {
            if (errno == ENOENT) { ++c->missing; c->boot_missing += critical; ri_finding(path,"missing"); }
            else error = fs1_error();
        } else {
            bool meta = st.st_dev == device && st.st_mode == mode && st.st_uid == uid && st.st_gid == gid;
            if (S_ISREG(mode)) meta = meta && st.st_size >= 0 && (uint64_t)st.st_size == size;
            if (S_ISLNK(mode) && meta) {
                char actual[PATH_MAX]; ssize_t n = readlinkat(parent, leaf, actual, sizeof(actual));
                if (n < 0) error = fs1_error();
                else meta = n == llen && !memcmp(actual, link, llen);
            }
            if (!error && !meta) { ++c->metadata; c->boot_metadata += critical; ri_finding(path,"metadata"); }
            else if (!error && S_ISREG(mode)) {
                uint8_t digest[32]; error = ri_hash_file(parent, leaf, device, size, digest);
                if (!error && memcmp(digest, record+24, 32)) {
                    ++c->content; c->boot_content += critical; ri_finding(path,"content");
                } else if (!error) ++c->matched;
            } else if (!error) ++c->matched;
        }
        if (close(parent) && !error) error = fs1_error();
    }
    if (!error && offset != ri_table_size) error = EPROTO;
    free(table); return error;
}

static int ri_name_order(const void *a, const void *b) { return strcmp(*(char *const *)a, *(char *const *)b); }

static int ri_inventory(int fd, dev_t device, const char *prefix, unsigned depth,
                        struct ri_counts *c, struct s22plus_max77705_runtime_sha256 *hash) {
    if (depth >= RI_MAX_DEPTH) return EOVERFLOW;
    int copy = fcntl(fd, F_DUPFD_CLOEXEC, 3);
    if (copy < 0) return fs1_error();
    DIR *directory = fdopendir(copy);
    if (!directory) { int error = fs1_error(); (void)close(copy); return error; }
    char **names = calloc(RI_MAX_ENTRIES, sizeof(*names)); unsigned count = 0; int error = names ? 0 : ENOMEM;
    while (!error) {
        errno = 0; struct dirent *entry = readdir(directory);
        if (!entry) { if (errno) error = errno; break; }
        if (!strcmp(entry->d_name,".") || !strcmp(entry->d_name,"..")) continue;
        if (count >= RI_MAX_ENTRIES || c->entries + count >= RI_MAX_ENTRIES) { error = EOVERFLOW; break; }
        names[count] = strdup(entry->d_name);
        if (!names[count]) { error = ENOMEM; break; } ++count;
    }
    if (closedir(directory) && !error) error = fs1_error();
    if (!error) qsort(names,count,sizeof(*names),ri_name_order);
    for (unsigned i = 0; i < count && !error; ++i) {
        struct stat st; char path[PATH_MAX], metadata[192];
        int length = snprintf(path,sizeof(path),"%s%s%s",prefix,*prefix?"/":"",names[i]);
        if (length < 1 || length >= PATH_MAX || ++c->entries > RI_MAX_ENTRIES) { error = EOVERFLOW; break; }
        if (fstatat(fd,names[i],&st,AT_SYMLINK_NOFOLLOW)) { error = fs1_error(); break; }
        if (st.st_dev != device || st.st_size < 0) { error = EPROTO; break; }
        length = snprintf(metadata,sizeof(metadata),"%zu:%s%u:%u:%u:%llu:",strlen(path),"",
                          st.st_mode,st.st_uid,st.st_gid,(unsigned long long)st.st_size);
        if (length < 1 || (size_t)length >= sizeof(metadata)) { error = EOVERFLOW; break; }
        s22plus_max77705_runtime_sha256_update(hash,(uint8_t *)metadata,(size_t)length);
        s22plus_max77705_runtime_sha256_update(hash,(uint8_t *)path,strlen(path));
        if (S_ISREG(st.st_mode)) { ++c->files; c->bytes += (uint64_t)st.st_size; }
        else if (S_ISLNK(st.st_mode)) {
            ++c->links; char link[PATH_MAX]; ssize_t n = readlinkat(fd,names[i],link,sizeof(link));
            if (n < 0 || n == PATH_MAX) { error = n < 0 ? fs1_error() : EOVERFLOW; break; }
            s22plus_max77705_runtime_sha256_update(hash,(uint8_t *)link,(size_t)n);
        } else if (S_ISDIR(st.st_mode)) {
            ++c->directories;
            int child = openat(fd,names[i],O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
            if (child < 0) { error = fs1_error(); break; }
            error = ri_fd_identity(child,device,true);
            if (!error) error = ri_inventory(child,device,path,depth+1,c,hash);
            if (close(child) && !error) error = fs1_error();
        } else ++c->other;
    }
    for (unsigned i = 0; i < count; ++i) free(names[i]);
    free(names); return error;
}

/* Missing/changed records are an observed state, never permission to create or
 * repair them. Only I/O failure makes the observation itself incomplete.
 */
static int ri_marker(int root, dev_t device, const char *name, const char *expected, int *state) {
    *state = 0; struct stat st;
    if (fstatat(root,name,&st,AT_SYMLINK_NOFOLLOW)) return errno == ENOENT ? 0 : fs1_error();
    *state = 2;
    if (!S_ISREG(st.st_mode) || st.st_dev != device || st.st_uid || st.st_gid ||
        st.st_nlink != 1 || (st.st_mode & 07777) != 0400 || st.st_size != (off_t)strlen(expected)) return 0;
    int fd = openat(root,name,O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);
    if (fd < 0) return fs1_error();
    char value[256]; int error = strlen(expected) >= sizeof(value) ? EOVERFLOW : ri_read(fd,value,strlen(expected));
    if (!error && !memcmp(value,expected,strlen(expected))) *state = 1;
    if (close(fd) && !error) error = fs1_error();
    return error;
}

static int ri_witness(int root, dev_t device, int *state) {
    struct stat st; *state = 0;
    if (fstatat(root,FS1_WITNESS_NAME,&st,AT_SYMLINK_NOFOLLOW)) return errno == ENOENT ? 0 : fs1_error();
    *state = 2;
    if (!S_ISREG(st.st_mode) || st.st_dev != device || st.st_uid || st.st_gid ||
        st.st_nlink != 1 || (st.st_mode & 07777) != 0400 || st.st_size != FS1_BLOCK) return 0;
    int fd = openat(root,FS1_WITNESS_NAME,O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);
    if (fd < 0) return fs1_error();
    uint8_t actual[FS1_BLOCK], expected[FS1_BLOCK]; fs1_witness(expected);
    int error = ri_read(fd,actual,sizeof(actual));
    if (!error && !memcmp(actual,expected,sizeof(actual))) *state = 1;
    if (close(fd) && !error) error = fs1_error();
    return error;
}

/* Retain the exact existing identity/features checks. Recognize only state,
 * RECOVER and orphan-head variations for reporting; they NEVER admit a mount.
 */
static int ri_super_identity(const uint8_t raw[1024]) {
    uint8_t clean[1024]; memcpy(clean,raw,sizeof(clean));
    if (fs1_u32(raw+0x3fc) != fs1_crc32c(raw,0x3fc)) return EPROTO;
    clean[0x3a] = 1; clean[0x3b] = 0; clean[0x60] &= ~4U;
    memset(clean+0xe8,0,4);
    uint32_t crc = fs1_crc32c(clean,0x3fc);
    for (unsigned i=0;i<4;++i) clean[0x3fc+i]=(uint8_t)(crc>>(i*8));
    return fs1_superblock(clean,sizeof(clean),fs1_uuid,FS1_BLOCKS) ? 0 : EPROTO;
}

static int ri_ro(struct fs1_endpoint *e, bool set) {
    int fd = fs1_open_block(fs1_node,e->partition,FS1_BYTES);
    if (fd < 0) return fs1_error();
    int value = 1, actual = -1, error = 0;
    if (set && ioctl(fd,BLKROSET,&value)) error = fs1_error();
    if (!error && (ioctl(fd,BLKROGET,&actual) || actual != 1)) error = EPROTO;
    uint64_t ro = 0;
    if (!error && (fs1_number(e->sys_partition,"ro",&ro) || ro != 1)) error = EPROTO;
    if (close(fd) && !error) error = fs1_error();
    return error;
}

/* A separately compiled probe may add a fixed post-comparison observation.
 * The standalone inspector never supplies that callback or permits execution.
 */
typedef int (*ri_observer)(int, struct fs1_endpoint *, const struct ri_counts *,
                           const struct ri_compare *, int, int, int);

static int ri_run(int argc, char **argv, const char *mode, ri_observer observe) {
    if (argc != 3 || strcmp(argv[1],mode) || strcmp(argv[2],fs1_run_id) ||
        getuid() || geteuid() || getgid() || getegid()) return 100;
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    char compatible[32];
    if (fs1_read_text("/sys/firmware/devicetree/base/compatible",compatible,sizeof(compatible)) ||
        strcmp(compatible,"linux,dummy-virt")) return 101;
#endif
    umask(077); ri_print("RI1_BEGIN version=1\n");
    int error = 0, cleanup = 0, parent = -1, devices = -1, root = -1;
    bool work_created = false, nodes_created = false, mounted = false, mount_proved = false, unmounted = false, ro = false;
    struct fs1_endpoint e = {.root_fd=-1,.file_fd=-1,.work_fd=-1,.node_fd=-1};
    struct stat st; struct statfs fs;
    uint8_t before[1024] = {0}; struct ri_counts counts = {0}; struct ri_compare comparison = {0};
    int started = 0, complete = 0, witness = 0, clean = 0;
    char inventory[65] = "none";
    ri_stage = 1;
    RI_PROGRESS_BEGIN("setup");
    parent = open("/s22-root-work",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    devices = open("/dev",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if (parent < 0 || devices < 0) { error = fs1_error(); goto done; }
    for (unsigned i=0;i<2;++i) {
        int fd = i ? devices : parent;
        if (fstat(fd,&st) || fstatfs(fd,&fs) || st.st_uid || st.st_gid || !S_ISDIR(st.st_mode) ||
            (st.st_mode&022) || fs.f_type != 0x01021994L || (i && (fs.f_flags&ST_NODEV))) { error=EPROTO; goto done; }
    }
    if (mkdirat(parent,"root-inspect-v1",0700)) { error=fs1_error(); goto done; } work_created=true;
    e.work_fd=openat(parent,"root-inspect-v1",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if (e.work_fd < 0 || mkdirat(e.work_fd,"root",0700)) { error=fs1_error(); goto done; } e.root_created=1;
    if (mkdirat(devices,".s22-ext4-v1",0700)) { error=fs1_error(); goto done; } nodes_created=true;
    e.node_fd=openat(devices,".s22-ext4-v1",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if (e.node_fd < 0 || unshare(CLONE_NEWNS) || mount(NULL,"/",NULL,MS_REC|MS_PRIVATE,NULL)) { error=fs1_error(); goto done; }
    RI_PROGRESS_END("setup");
    ri_stage=2;
    RI_PROGRESS_BEGIN("binding");
    if ((error=fs1_resolve(&e)) || (error=fs1_make_node(&e,"lu0",e.disk,0400)) ||
        (error=fs1_make_node(&e,"native",e.partition,0400)) || (error=fs1_gpt_exact(&e))) goto done;
    ri_print("RI1_BIND exact=1\n");
    RI_PROGRESS_END("binding");
    ri_stage=3;
    RI_PROGRESS_BEGIN("block-ro");
    if ((error=ri_ro(&e,true))) goto done;
    ro=true;
    ri_print("RI1_BLOCK_RO partition=1\n");
    RI_PROGRESS_END("block-ro");
    ri_stage=4;
    RI_PROGRESS_BEGIN("superblock");
    if ((error=fs1_read_super(&e,false)) || (error=ri_super_identity(e.superblock))) goto done;
    memcpy(before,e.superblock,sizeof(before)); clean=fs1_superblock(before,sizeof(before),fs1_uuid,FS1_BLOCKS);
    ri_print("RI1_SUPER clean=%d state=%u recover=%u orphan=%u\n",clean,fs1_u16(before+0x3a),
             !!(fs1_u32(before+0x60)&4U),fs1_u32(before+0xe8));
    RI_PROGRESS_END("superblock");
    if (!clean) goto final;
    /* A negative callback is a settled scientific stop, not an errno. */
    int pre_mount = RI_PRE_MOUNT(&e);
    if (pre_mount > 0) { error=pre_mount; goto done; }
    if (pre_mount < 0) goto final;
    ri_stage=5;
    RI_PROGRESS_BEGIN("mount");
    if (mount(fs1_node,ri_root,"ext4",MS_RDONLY|MS_NOSUID|MS_NODEV|MS_NOEXEC,"noload,nodiscard")) { error=fs1_error(); goto done; }
    mounted=true;
    root=open(ri_root,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if (root < 0 || fstat(root,&st) || fstatfs(root,&fs) || st.st_dev != e.partition ||
        fs.f_type != 0xef53 || fs.f_bsize != FS1_BLOCK ||
        (fs.f_flags&(ST_RDONLY|ST_NOSUID|ST_NODEV|ST_NOEXEC)) != (ST_RDONLY|ST_NOSUID|ST_NODEV|ST_NOEXEC) ||
        (error=ri_ro(&e,false))) { if (!error) error=EPROTO; goto done; }
    mount_proved=true; ri_print("RI1_MOUNT readonly=1 noload=1 nodev=1 noexec=1 nosuid=1\n");
    RI_PROGRESS_END("mount");
    ri_stage=6;
    RI_PROGRESS_BEGIN("markers");
    if ((error=ri_marker(root,e.partition,".s22-debian-start-v1",ri_install_identity,&started)) ||
        (error=ri_marker(root,e.partition,".s22-debian-complete-v1",ri_install_identity,&complete)) ||
        (error=ri_witness(root,e.partition,&witness))) goto done;
    ri_print("RI1_MARKERS start=%d complete=%d witness=%d\n",started,complete,witness);
    RI_PROGRESS_END("markers");
    ri_stage=7;
    RI_PROGRESS_BEGIN("inventory");
    struct s22plus_max77705_runtime_sha256 tree_hash; uint8_t tree_digest[32];
    s22plus_max77705_runtime_sha256_init(&tree_hash);
    if ((error=ri_inventory(root,e.partition,"",0,&counts,&tree_hash))) goto done;
    s22plus_max77705_runtime_sha256_final(&tree_hash,tree_digest); ri_digest(tree_digest,inventory);
    ri_print("RI1_TREE entries=%u files=%u dirs=%u links=%u other=%u bytes=%" PRIu64 " sha256=%s\n",
             counts.entries,counts.files,counts.directories,counts.links,counts.other,counts.bytes,inventory);
    RI_PROGRESS_END("inventory");
    ri_stage=8;
    RI_PROGRESS_BEGIN("comparison");
    if ((error=ri_compare_tree(root,e.partition,&comparison))) goto done;
    ri_print("RI1_COMPARE expected=%u matched=%u missing=%u metadata=%u content=%u boot_expected=%u boot_missing=%u boot_metadata=%u boot_content=%u hashed_bytes=%" PRIu64 " findings=%u\n",
             comparison.expected,comparison.matched,comparison.missing,comparison.metadata,comparison.content,
             comparison.boot_expected,comparison.boot_missing,comparison.boot_metadata,comparison.boot_content,ri_hashed_bytes,ri_reported);
    RI_PROGRESS_END("comparison");
    if (observe && (error=observe(root,&e,&counts,&comparison,started,complete,witness))) goto done;
    ri_stage=9;
    RI_PROGRESS_BEGIN("unmount");
    if (close(root)) { root=-1; error=fs1_error(); goto done; } root=-1;
    if (umount2(ri_root,0)) { error=fs1_error(); mounted=false; goto done; }
    mounted=false; unmounted=true; ri_print("RI1_UNMOUNT complete=1\n");
    RI_PROGRESS_END("unmount");
final:
    ri_stage=10;
    RI_PROGRESS_BEGIN("final-binding");
    if ((error=ri_ro(&e,false)) || (error=fs1_not_mounted(e.partition)) ||
        (error=fs1_read_super(&e,false)) || memcmp(before,e.superblock,sizeof(before)) ||
        (error=fs1_gpt_exact(&e))) { if (!error) error=EPROTO; goto done; }
    ri_print("RI1_FINAL super_unchanged=1 gpt_unchanged=1 partition_ro=1\n");
    RI_PROGRESS_END("final-binding");
done:
    RI_PROGRESS_ERROR(error);
    RI_PROGRESS_BEGIN("cleanup");
    if (root >= 0 && close(root)) cleanup=fs1_error();
    /* One cleanup unmount is allowed only for a known owned mount. A failed
     * normal unmount is never tried again. No RO-clear ioctl exists. */
    if (mounted) {
        if (umount2(ri_root,0)) cleanup=fs1_error();
        else { unmounted=true; mounted=false; }
    }
    if (e.node_fd >= 0) {
        if (e.node_created && unlinkat(e.node_fd,"native",0) && !cleanup) cleanup=fs1_error();
        if (e.disk_created && unlinkat(e.node_fd,"lu0",0) && !cleanup) cleanup=fs1_error();
        if (close(e.node_fd) && !cleanup) cleanup=fs1_error();
    }
    if (nodes_created && unlinkat(devices,".s22-ext4-v1",AT_REMOVEDIR) && !cleanup) cleanup=fs1_error();
    if (e.work_fd >= 0) {
        if (e.root_created && unlinkat(e.work_fd,"root",AT_REMOVEDIR) && !cleanup) cleanup=fs1_error();
        if (close(e.work_fd) && !cleanup) cleanup=fs1_error();
    }
    if (work_created && unlinkat(parent,"root-inspect-v1",AT_REMOVEDIR) && !cleanup) cleanup=fs1_error();
    if (devices >= 0 && close(devices) && !cleanup) cleanup=fs1_error();
    if (parent >= 0 && close(parent) && !cleanup) cleanup=fs1_error();
    RI_PROGRESS_CLEANUP(cleanup);
    ri_print("RI1_RESULT complete=%u stage=%u errno=%d cleanup_errno=%d partition_ro=%u clean=%d mounted=%u unmounted=%u\n",
             !error&&!cleanup,ri_stage,error,cleanup,ro,clean,mount_proved,unmounted);
    return error || cleanup ? 1 : 0;
}

#ifndef S22_ROOT_INSPECT_LIBRARY
int main(int argc, char **argv) { return ri_run(argc,argv,"inspect",NULL); }
#endif
