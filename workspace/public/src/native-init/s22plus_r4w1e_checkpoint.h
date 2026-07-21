#ifndef S22PLUS_R4W1E_CHECKPOINT_H
#define S22PLUS_R4W1E_CHECKPOINT_H

#include <stddef.h>
#include <stdint.h>

#define S22_R4W1E_STAGE_PROC_MOUNTED 0x10U
#define S22_R4W1E_STAGE_SYS_MOUNTED 0x11U
#define S22_R4W1E_STAGE_DEV_TMPFS_MOUNTED 0x12U
#define S22_R4W1E_STAGE_RUN_TMPFS_MOUNTED 0x13U
#define S22_R4W1E_STAGE_DEV_NODES_VERIFIED 0x14U
#define S22_R4W1E_STAGE_CHILD_EXEC_STARTED 0x20U
#define S22_R4W1E_STAGE_CHILD_TOKEN_VERIFIED 0x21U
#define S22_R4W1E_STAGE_CHILD_REAPED 0x22U
#define S22_R4W1E_STAGE_WDT_MODULE_0 0x30U
#define S22_R4W1E_STAGE_WDT_MODULE_1 0x31U
#define S22_R4W1E_STAGE_WDT_MODULE_2 0x32U
#define S22_R4W1E_STAGE_WDT_MODULE_3 0x33U
#define S22_R4W1E_STAGE_WDT_MODULE_4 0x34U
#define S22_R4W1E_STAGE_WDT_MODULES_VERIFIED 0x35U
#define S22_R4W1E_STAGE_E1_SUCCESS 0x3fU

struct s22_r4w1e_checkpoint_client {
    uint8_t run_id[16];
    uint8_t stage;
    uint8_t initialized;
    uint8_t terminal;
};

int s22_r4w1e_checkpoint_client_init(
    struct s22_r4w1e_checkpoint_client *client,
    const uint8_t run_id[16]);
long s22_r4w1e_checkpoint_progress(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t stage,
    uint8_t item_index);
long s22_r4w1e_checkpoint_failure(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t stage,
    uint8_t item_index,
    long operation_error);
long s22_r4w1e_checkpoint_success(
    struct s22_r4w1e_checkpoint_client *client);

#endif
