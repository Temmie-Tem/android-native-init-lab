/* Fixed RAM-only handover. No path, command or workload is caller selected. */
#ifndef S22_PREFLIGHT_RECORD_H
#define S22_PREFLIGHT_RECORD_H
#define BP_MAGIC 0x31504642U
#define BP_VERSION 1U
#define BP_FD 198
#define BP_LOG_MAX 65536U
#define BP_MODULE_COUNT 81U
#define BP_EXPECTED_CHILDREN 8U
#define BP_SEALS 15U
#define BP_TIMEOUT_MS 30000U
#define BP_TOTAL_MS 240000U

enum bp_stage {
    BP_ENTER = 1, BP_BASE_MOUNTS = 2, BP_MODULES = 3, BP_ENDPOINT = 4,
    BP_BLOCK_RO = 5, BP_CHECKER = 6, BP_FIRST_ROOT = 7, BP_MDEV = 8,
    BP_SECOND_ROOT = 9, BP_LOADER_VERIFY = 10, BP_LOADER_LIST = 11,
    BP_PREFLIGHT_DONE = 12
};

struct bp_record {
    unsigned magic, version, header_size, log_size;
    unsigned stage, error, cleanup_error, complete;
    unsigned modules_completed, children_started, children_reaped, children_executed;
    unsigned child_status, child_error, timed_out, output_exceeded;
    unsigned partition_ro, super_unchanged, gpt_unchanged, mounts_released;
    unsigned descriptors_closed, children_settled, virtual_board, root_mounts;
    unsigned char run_id[16];
    char boot_id[37];
    char stop_name[63];
};
_Static_assert(sizeof(struct bp_record) == 212, "fixed preflight record layout");

static int bp_valid(const struct bp_record *p, const unsigned char run[16], int virt) {
    if (p->magic != BP_MAGIC || p->version != BP_VERSION || p->header_size != sizeof(*p) ||
        p->log_size > BP_LOG_MAX || p->stage < BP_MODULES || p->stage > BP_PREFLIGHT_DONE ||
        p->complete > 1 || p->error > 4095 || p->cleanup_error || p->timed_out ||
        p->output_exceeded || p->partition_ro > 1 || p->super_unchanged > 1 ||
        p->gpt_unchanged > 1 || p->mounts_released != 1 || p->descriptors_closed != 1 ||
        p->children_settled != 1 || p->virtual_board != (unsigned)virt ||
        p->modules_completed != (virt ? 0U : BP_MODULE_COUNT) ||
        p->children_started > BP_EXPECTED_CHILDREN || p->children_reaped != p->children_started ||
        p->children_executed > p->children_reaped || p->root_mounts > 2 ||
        (p->root_mounts && !p->partition_ro) ||
        p->super_unchanged != p->partition_ro || p->gpt_unchanged != p->partition_ro ||
        p->boot_id[36] != '\n') return 0;
    for (unsigned i = 0; i < 16; ++i) if (p->run_id[i] != run[i]) return 0;
    for (unsigned i = 0; i < 36; ++i) {
        char c = p->boot_id[i];
        int hyphen = i == 8 || i == 13 || i == 18 || i == 23;
        if (hyphen ? c != '-' : !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return 0;
    }
    if (p->stop_name[62]) return 0;
    if (p->complete) return !p->error && !p->child_error && !p->child_status &&
        p->stage == BP_PREFLIGHT_DONE && p->children_started == BP_EXPECTED_CHILDREN &&
        p->children_executed == 6 && p->root_mounts == 2 && p->partition_ro &&
        p->super_unchanged && p->gpt_unchanged && !p->stop_name[0];
    return p->error && p->stop_name[0];
}
#endif
