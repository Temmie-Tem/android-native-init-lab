/*
 * V2674 lower hidden-node ACDB SET capture preload.
 *
 * V2673 proved the old post-init helper path can SIGSEGV after the common
 * hook returns but before the helper can arm capture and call the lower runner.
 * This preload therefore keeps the V2608 safety policy (skip the real public
 * common path and patch the initialized flag), then arms capture and executes
 * the lower hidden-node sequence inside the common-topology hook itself. After
 * artifacts are written it exits the process to avoid the unstable init tail.
 *
 * The lower sequence still uses libacdbloader internal offsets:
 * create_cal_node(base+0xfd45), allocate_cal_block(base+0xfbbd), the pinned
 * acdb_ioctl GET command, and a fake AUDIO_SET_CALIBRATION ioctl. The V2630
 * ioctl shim linked into the same shared object always fake-successes SET and
 * dumps the SET argument/dma-buf before returning.
 */

typedef signed int int32_t;
typedef unsigned int uint32_t;
typedef unsigned char uint8_t;
typedef unsigned long uintptr_t;
typedef unsigned long size_t;

extern void *dlsym(void *handle, const char *symbol);
extern int32_t acdb_ioctl(uint32_t cmd, const uint8_t *in, uint32_t in_len,
                          uint8_t *out_buf, uint32_t out_len);
extern int ioctl(int fd, unsigned long request, ...);
extern void a90_arm_capture(void) __attribute__((weak, visibility("default")));

#define A90_RTLD_NEXT ((void *)-1L)
#define A90_RTLD_DEFAULT ((void *)0)

#define A90_EVENTS_PATH "/data/local/tmp/a90-acdb-ownget/acdb-v2674-lower-hidden-inhook-events.jsonl"
#define A90_LOADER_IS_INITIALIZED_OFF 0x00008034UL
#define A90_LOADER_INIT_FLAG_OFF 0x00018a9cUL
#define A90_CREATE_CAL_NODE_OFF 0x0000fd44UL
#define A90_ALLOCATE_CAL_BLOCK_OFF 0x0000fbbcUL
#define A90_AUDIO_SET_CALIBRATION 0xc00461cbUL

#define A90_AT_FDCWD (-100)
#define A90_O_WRONLY 00000001
#define A90_O_CREAT 00000100
#define A90_O_APPEND 00002000
#define A90_MODE_0600 0600

#define A90_NR_WRITE 4
#define A90_NR_CLOSE 6
#define A90_NR_GETPID 20
#define A90_NR_GETTID 224
#define A90_NR_EXIT_GROUP 248
#define A90_NR_EXIT 1
#define A90_NR_OPENAT 322

struct a90_cal_node {
    uint32_t word0;
    uint32_t word4;
    void *block;
};

struct a90_cal_block {
    uint32_t get_arg0;
    uint32_t word4;
    uint32_t get_arg1;
    int32_t mem_handle;
    uint32_t word16;
    uint32_t word20;
};

struct a90_target_cal {
    uint32_t cal_type;
    uint32_t get_cmd;
    const char *label;
};

typedef struct a90_cal_node *(*a90_create_cal_node_fn)(uint32_t cal_type);
typedef int32_t (*a90_allocate_cal_block_fn)(uint32_t cal_type, uint32_t node_word0,
                                             uint32_t *set_arg, void *block);

typedef int32_t (*a90_common_topology_fn)(void);

static volatile int a90_in_hook;
static uintptr_t a90_loader_base;
static a90_common_topology_fn a90_real_common_topology;
static a90_create_cal_node_fn a90_create_cal_node;
static a90_allocate_cal_block_fn a90_allocate_cal_block;

static const struct a90_target_cal a90_targets[] = {
    {24U, 0x000130daU, "afe-custom-topology"},
    {10U, 0x00011394U, "adm-custom-topology"},
    {14U, 0x00012e01U, "asm-custom-topology"},
};

static long a90_syscall0(long n)
{
    register long r7 __asm__("r7") = n;
    register long r0 __asm__("r0");
    __asm__ volatile("svc #0" : "=r"(r0) : "r"(r7) : "memory");
    return r0;
}

static long a90_syscall1(long n, long a0)
{
    register long r7 __asm__("r7") = n;
    register long r0 __asm__("r0") = a0;
    __asm__ volatile("svc #0" : "+r"(r0) : "r"(r7) : "memory");
    return r0;
}

static long a90_syscall3(long n, long a0, long a1, long a2)
{
    register long r7 __asm__("r7") = n;
    register long r0 __asm__("r0") = a0;
    register long r1 __asm__("r1") = a1;
    register long r2 __asm__("r2") = a2;
    __asm__ volatile("svc #0" : "+r"(r0) : "r"(r1), "r"(r2), "r"(r7) : "memory");
    return r0;
}

static long a90_syscall4(long n, long a0, long a1, long a2, long a3)
{
    register long r7 __asm__("r7") = n;
    register long r0 __asm__("r0") = a0;
    register long r1 __asm__("r1") = a1;
    register long r2 __asm__("r2") = a2;
    register long r3 __asm__("r3") = a3;
    __asm__ volatile("svc #0" : "+r"(r0) : "r"(r1), "r"(r2), "r"(r3), "r"(r7) : "memory");
    return r0;
}

static int a90_open_append(const char *path)
{
    return (int)a90_syscall4(A90_NR_OPENAT, A90_AT_FDCWD, (long)path,
                             A90_O_WRONLY | A90_O_CREAT | A90_O_APPEND,
                             A90_MODE_0600);
}

static void a90_close(int fd)
{
    if (fd >= 0)
        (void)a90_syscall1(A90_NR_CLOSE, fd);
}

static void a90_exit(int code)
{
    (void)a90_syscall1(A90_NR_EXIT_GROUP, code);
    (void)a90_syscall1(A90_NR_EXIT, code);
    for (;;) {
    }
}

static uint32_t a90_getpid(void)
{
    return (uint32_t)a90_syscall0(A90_NR_GETPID);
}

static uint32_t a90_gettid(void)
{
    return (uint32_t)a90_syscall0(A90_NR_GETTID);
}

static size_t a90_strlen(const char *s)
{
    size_t n = 0;
    while (s && s[n])
        n++;
    return n;
}

static void a90_write_all(int fd, const char *p, size_t len)
{
    while (len) {
        long rc = a90_syscall3(A90_NR_WRITE, fd, (long)p, (long)len);
        if (rc <= 0)
            return;
        p += (size_t)rc;
        len -= (size_t)rc;
    }
}

static void a90_write_str(int fd, const char *s)
{
    a90_write_all(fd, s, a90_strlen(s));
}

static void a90_write_dec(int fd, unsigned int v)
{
    char buf[16];
    char rev[16];
    int n = 0;
    int i;

    if (v == 0) {
        a90_write_str(fd, "0");
        return;
    }
    while (v && n < (int)sizeof(rev)) {
        rev[n++] = (char)('0' + (v % 10));
        v /= 10;
    }
    for (i = 0; i < n; i++)
        buf[i] = rev[n - i - 1];
    a90_write_all(fd, buf, (size_t)n);
}

static void a90_write_sdec(int fd, int code)
{
    if (code < 0) {
        a90_write_str(fd, "-");
        a90_write_dec(fd, (unsigned int)(0U - (unsigned int)code));
    } else {
        a90_write_dec(fd, (unsigned int)code);
    }
}

static void a90_write_hex32(int fd, uint32_t v)
{
    static const char hex[] = "0123456789abcdef";
    char buf[10];
    int i;

    buf[0] = '0';
    buf[1] = 'x';
    for (i = 0; i < 8; i++)
        buf[2 + i] = hex[(v >> ((7 - i) * 4)) & 0xf];
    a90_write_all(fd, buf, sizeof(buf));
}

static void a90_write_event(const char *stage, int code, uint32_t cal_type, uint32_t value)
{
    int fd = a90_open_append(A90_EVENTS_PATH);
    if (fd < 0)
        return;

    a90_write_str(fd, "{\"event\":\"v2672_lower_hidden\",\"stage\":\"");
    a90_write_str(fd, stage);
    a90_write_str(fd, "\",\"code\":");
    a90_write_sdec(fd, code);
    a90_write_str(fd, ",\"cal_type\":");
    a90_write_dec(fd, cal_type);
    a90_write_str(fd, ",\"value\":");
    a90_write_hex32(fd, value);
    a90_write_str(fd, ",\"pid\":");
    a90_write_dec(fd, a90_getpid());
    a90_write_str(fd, ",\"tid\":");
    a90_write_dec(fd, a90_gettid());
    a90_write_str(fd, "}\n");
    a90_close(fd);
}

static uintptr_t a90_resolve_loader_base(void)
{
    uintptr_t is_initialized;

    if (a90_loader_base)
        return a90_loader_base;

    is_initialized = (uintptr_t)dlsym(A90_RTLD_DEFAULT, "acdb_loader_is_initialized");
    if (!is_initialized)
        is_initialized = (uintptr_t)dlsym(A90_RTLD_NEXT, "acdb_loader_is_initialized");
    if (!is_initialized)
        return 0;

    is_initialized &= ~(uintptr_t)1U;
    a90_loader_base = is_initialized - A90_LOADER_IS_INITIALIZED_OFF;
    a90_create_cal_node = (a90_create_cal_node_fn)((a90_loader_base + A90_CREATE_CAL_NODE_OFF) | 1U);
    a90_allocate_cal_block = (a90_allocate_cal_block_fn)((a90_loader_base + A90_ALLOCATE_CAL_BLOCK_OFF) | 1U);
    a90_write_event("loader_base_resolved", 0, 0, (uint32_t)a90_loader_base);
    return a90_loader_base;
}

static int a90_patch_initialized_flag(void)
{
    uintptr_t base;
    volatile unsigned char *flag;

    base = a90_resolve_loader_base();
    if (!base)
        return -1;

    flag = (volatile unsigned char *)(base + A90_LOADER_INIT_FLAG_OFF);
    *flag = 1U;
    a90_write_event("patched_initialized_flag", 0, 0, (uint32_t)(uintptr_t)flag);
    return 0;
}

static void a90_zero_words(uint32_t *words, uint32_t count)
{
    uint32_t i;
    for (i = 0; i < count; i++)
        words[i] = 0;
}

static int32_t a90_run_one_lower_target(const struct a90_target_cal *target)
{
    struct a90_cal_node *node;
    struct a90_cal_block *block;
    uint32_t alloc_arg[8];
    uint32_t get_in[2];
    uint32_t get_out = 0;
    uint32_t set_arg[8];
    int32_t alloc_ret;
    int32_t get_ret;
    int set_ret;

    if (!a90_create_cal_node || !a90_allocate_cal_block)
        return -30;

    node = a90_create_cal_node(target->cal_type);
    a90_write_event("create_cal_node_return", node ? 0 : -1, target->cal_type, (uint32_t)(uintptr_t)node);
    if (!node)
        return -31;

    a90_zero_words(alloc_arg, 8U);
    alloc_arg[0] = 32U;
    alloc_arg[3] = 16U;
    alloc_ret = a90_allocate_cal_block(target->cal_type, node->word0, alloc_arg, node->block);
    a90_write_event("allocate_cal_block_return", alloc_ret, target->cal_type, (uint32_t)(uintptr_t)node->block);
    if (alloc_ret <= -1)
        return -32;

    block = (struct a90_cal_block *)node->block;
    if (!block) {
        a90_write_event("allocated_block_missing", -1, target->cal_type, 0);
        return -33;
    }

    get_in[0] = block->get_arg0;
    get_in[1] = block->get_arg1;
    get_ret = acdb_ioctl(target->get_cmd, (const uint8_t *)get_in, 8U, (uint8_t *)&get_out, 4U);
    a90_write_event("acdb_ioctl_get_return", get_ret, target->cal_type, get_out);
    if (get_ret != 0)
        return -34;

    a90_zero_words(set_arg, 8U);
    set_arg[0] = 32U;
    set_arg[2] = target->cal_type;
    set_arg[3] = 16U;
    set_arg[6] = get_out;
    set_arg[7] = (uint32_t)block->mem_handle;
    set_ret = ioctl(-1, A90_AUDIO_SET_CALIBRATION, set_arg);
    a90_write_event("fake_set_ioctl_return", set_ret, target->cal_type, set_arg[7]);
    if (set_ret != 0)
        return -35;

    return 0;
}

__attribute__((visibility("default"))) int32_t a90_run_lower_hidden_nodes(void)
{
    uint32_t i;
    int32_t rc = 0;

    if (!a90_resolve_loader_base()) {
        a90_write_event("loader_base_missing", -1, 0, 0);
        return -10;
    }

    for (i = 0; i < (uint32_t)(sizeof(a90_targets) / sizeof(a90_targets[0])); i++) {
        int32_t one = a90_run_one_lower_target(&a90_targets[i]);
        if (one != 0 && rc == 0)
            rc = one;
    }
    a90_write_event("lower_hidden_sequence_complete", rc, 0, 0);
    return rc;
}

__attribute__((visibility("default"))) int32_t acdb_loader_send_common_custom_topology(void)
{
    int32_t common_ret = 0;
    int patch_ret;
    int32_t lower_ret = -99;

    if (a90_in_hook)
        return -92;
    a90_in_hook = 1;

    a90_write_event("entered_common_topology_hook", 0, 0, 0);
    if (!a90_real_common_topology)
        a90_real_common_topology = (a90_common_topology_fn)dlsym(A90_RTLD_NEXT, "acdb_loader_send_common_custom_topology");
    common_ret = 0;
    a90_write_event("skip_real_common_topology", 0, 0, 0);
    patch_ret = a90_patch_initialized_flag();
    a90_write_event("patch_initialized_flag_return", patch_ret, 0, 0);

    if (a90_arm_capture) {
        a90_arm_capture();
        a90_write_event("armed_inside_common_hook", 0, 0, 0);
    } else {
        a90_write_event("arm_capture_missing_inside_common_hook", -1, 0, 0);
    }

    lower_ret = a90_run_lower_hidden_nodes();
    a90_write_event("lower_hidden_nodes_return_inside_common_hook", lower_ret, 0, 0);
    a90_write_event("exit_after_inhook_lower_hidden_nodes", lower_ret, 0, 0);

    a90_in_hook = 0;
    a90_exit(0);
    return common_ret;
}
