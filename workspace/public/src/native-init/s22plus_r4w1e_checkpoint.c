#include "s22plus_r4w1e_checkpoint.h"

#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "R4W1-E checkpoint ABI requires little-endian byte order"
#endif

#define AT_FDCWD (-100)
#define O_WRONLY 00000001
#define O_CLOEXEC 02000000

#define EIO 5
#define EINVAL 22
#define EALREADY 114
#define EKEYREJECTED 129

#define NR_OPENAT 56
#define NR_CLOSE 57
#define NR_WRITE 64

#define S22_R4W1E_PROFILE_E1 1U
#define S22_R4W1E_OUTCOME_PROGRESS 0U
#define S22_R4W1E_OUTCOME_SUCCESS 1U
#define S22_R4W1E_OUTCOME_FAILURE 2U

struct s22_r4w1e_checkpoint_request {
    uint8_t magic[4];
    uint8_t version;
    uint8_t profile;
    uint8_t stage;
    uint8_t outcome;
    uint16_t detail;
    uint8_t item_index;
    uint8_t reserved;
    uint8_t run_id[16];
    uint32_t crc32;
} __attribute__((packed));

_Static_assert(sizeof(struct s22_r4w1e_checkpoint_request) == 32U, "request size");
_Static_assert(
    offsetof(struct s22_r4w1e_checkpoint_request, detail) == 8U,
    "detail offset");
_Static_assert(
    offsetof(struct s22_r4w1e_checkpoint_request, run_id) == 12U,
    "run ID offset");
_Static_assert(
    offsetof(struct s22_r4w1e_checkpoint_request, crc32) == 28U,
    "CRC offset");

static inline long syscall6(
    long nr,
    long a0,
    long a1,
    long a2,
    long a3,
    long a4,
    long a5) {
    register long x0 asm("x0") = a0;
    register long x1 asm("x1") = a1;
    register long x2 asm("x2") = a2;
    register long x3 asm("x3") = a3;
    register long x4 asm("x4") = a4;
    register long x5 asm("x5") = a5;
    register long x8 asm("x8") = nr;
    asm volatile(
        "svc #0"
        : "+r"(x0)
        : "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x5), "r"(x8)
        : "memory");
    return x0;
}

static long sys_openat(const char *path, int flags) {
    return syscall6(
        NR_OPENAT, AT_FDCWD, (long)(uintptr_t)path, flags, 0, 0, 0);
}

static long sys_write(int fd, const void *buffer, size_t count) {
    return syscall6(
        NR_WRITE, fd, (long)(uintptr_t)buffer, (long)count, 0, 0, 0);
}

static long sys_close(int fd) {
    return syscall6(NR_CLOSE, fd, 0, 0, 0, 0, 0);
}

static void copy_bytes(uint8_t *destination, const uint8_t *source, size_t count) {
    for (size_t index = 0; index < count; ++index) {
        destination[index] = source[index];
    }
}

static int all_zero(const uint8_t *value, size_t count) {
    uint8_t combined = 0;
    for (size_t index = 0; index < count; ++index) {
        combined |= value[index];
    }
    return combined == 0;
}

static uint32_t checkpoint_crc32(const void *data, size_t count) {
    const uint8_t *bytes = (const uint8_t *)data;
    uint32_t crc = ~0U;
    for (size_t index = 0; index < count; ++index) {
        crc ^= bytes[index];
        for (unsigned int bit = 0; bit < 8U; ++bit) {
            uint32_t mask = 0U - (crc & 1U);
            crc = (crc >> 1U) ^ (0xedb88320U & mask);
        }
    }
    return crc ^ ~0U;
}

static uint8_t e1_next_stage(uint8_t stage) {
    switch (stage) {
    case 0x00: return S22_R4W1E_STAGE_PROC_MOUNTED;
    case S22_R4W1E_STAGE_PROC_MOUNTED: return S22_R4W1E_STAGE_SYS_MOUNTED;
    case S22_R4W1E_STAGE_SYS_MOUNTED: return S22_R4W1E_STAGE_DEV_TMPFS_MOUNTED;
    case S22_R4W1E_STAGE_DEV_TMPFS_MOUNTED: return S22_R4W1E_STAGE_RUN_TMPFS_MOUNTED;
    case S22_R4W1E_STAGE_RUN_TMPFS_MOUNTED: return S22_R4W1E_STAGE_DEV_NODES_VERIFIED;
    case S22_R4W1E_STAGE_DEV_NODES_VERIFIED: return S22_R4W1E_STAGE_CHILD_EXEC_STARTED;
    case S22_R4W1E_STAGE_CHILD_EXEC_STARTED: return S22_R4W1E_STAGE_CHILD_TOKEN_VERIFIED;
    case S22_R4W1E_STAGE_CHILD_TOKEN_VERIFIED: return S22_R4W1E_STAGE_CHILD_REAPED;
    case S22_R4W1E_STAGE_CHILD_REAPED: return S22_R4W1E_STAGE_WDT_MODULE_0;
    case S22_R4W1E_STAGE_WDT_MODULE_0: return S22_R4W1E_STAGE_WDT_MODULE_1;
    case S22_R4W1E_STAGE_WDT_MODULE_1: return S22_R4W1E_STAGE_WDT_MODULE_2;
    case S22_R4W1E_STAGE_WDT_MODULE_2: return S22_R4W1E_STAGE_WDT_MODULE_3;
    case S22_R4W1E_STAGE_WDT_MODULE_3: return S22_R4W1E_STAGE_WDT_MODULE_4;
    case S22_R4W1E_STAGE_WDT_MODULE_4: return S22_R4W1E_STAGE_WDT_MODULES_VERIFIED;
    case S22_R4W1E_STAGE_WDT_MODULES_VERIFIED: return S22_R4W1E_STAGE_E1_SUCCESS;
    default: return 0;
    }
}

static int valid_item_index(uint8_t stage, uint8_t item_index) {
    if (stage >= S22_R4W1E_STAGE_WDT_MODULE_0 &&
        stage <= S22_R4W1E_STAGE_WDT_MODULE_4) {
        return item_index == stage - S22_R4W1E_STAGE_WDT_MODULE_0;
    }
    return item_index == 0U;
}

static long publish(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t stage,
    uint8_t outcome,
    uint8_t item_index,
    uint16_t detail) {
    struct s22_r4w1e_checkpoint_request request = {0};
    if (client == NULL || !client->initialized || client->terminal) {
        return -EALREADY;
    }
    if (e1_next_stage(client->stage) != stage || !valid_item_index(stage, item_index)) {
        return -EINVAL;
    }
    if ((outcome == S22_R4W1E_OUTCOME_PROGRESS &&
         (stage == S22_R4W1E_STAGE_E1_SUCCESS || detail != 0U)) ||
        (outcome == S22_R4W1E_OUTCOME_SUCCESS &&
         (stage != S22_R4W1E_STAGE_E1_SUCCESS || detail != 0U)) ||
        (outcome == S22_R4W1E_OUTCOME_FAILURE && detail == 0U) ||
        outcome > S22_R4W1E_OUTCOME_FAILURE) {
        return -EINVAL;
    }

    request.magic[0] = 'S';
    request.magic[1] = '2';
    request.magic[2] = '2';
    request.magic[3] = 'Q';
    request.version = 1U;
    request.profile = S22_R4W1E_PROFILE_E1;
    request.stage = stage;
    request.outcome = outcome;
    request.detail = detail;
    request.item_index = item_index;
    copy_bytes(request.run_id, client->run_id, sizeof(request.run_id));
    request.crc32 = checkpoint_crc32(&request, offsetof(
        struct s22_r4w1e_checkpoint_request, crc32));

    long fd = sys_openat("/proc/s22_checkpoint", O_WRONLY | O_CLOEXEC);
    if (fd < 0) {
        return fd;
    }
    long written = sys_write((int)fd, &request, sizeof(request));
    long closed = sys_close((int)fd);
    if (written != (long)sizeof(request)) {
        return written < 0 ? written : -EIO;
    }
    if (closed != 0) {
        return closed;
    }
    client->stage = stage;
    client->terminal = outcome != S22_R4W1E_OUTCOME_PROGRESS;
    return 0;
}

int s22_r4w1e_checkpoint_client_init(
    struct s22_r4w1e_checkpoint_client *client,
    const uint8_t run_id[16]) {
    if (client == NULL || run_id == NULL || all_zero(run_id, 16U)) {
        return -EKEYREJECTED;
    }
    copy_bytes(client->run_id, run_id, sizeof(client->run_id));
    client->stage = 0;
    client->initialized = 1U;
    client->terminal = 0U;
    return 0;
}

long s22_r4w1e_checkpoint_progress(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t stage,
    uint8_t item_index) {
    return publish(
        client, stage, S22_R4W1E_OUTCOME_PROGRESS, item_index, 0U);
}

long s22_r4w1e_checkpoint_failure(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t stage,
    uint8_t item_index,
    long operation_error) {
    unsigned long detail = operation_error < 0
        ? (unsigned long)(-operation_error)
        : (unsigned long)operation_error;
    if (detail == 0U) {
        detail = EIO;
    }
    if (detail > 4095U) {
        detail = 4095U;
    }
    return publish(
        client,
        stage,
        S22_R4W1E_OUTCOME_FAILURE,
        item_index,
        (uint16_t)detail);
}

long s22_r4w1e_checkpoint_success(
    struct s22_r4w1e_checkpoint_client *client) {
    return publish(
        client,
        S22_R4W1E_STAGE_E1_SUCCESS,
        S22_R4W1E_OUTCOME_SUCCESS,
        0U,
        0U);
}
