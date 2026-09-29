/* Shared fixed terminal state. All fields are little endian on target ARM64.
 * fd 3 is the already authenticated ACM descriptor; fd 4 is a sealed memfd.
 * Neither descriptor is an old-root directory or a block-data writer.
 */
#ifndef S22PLUS_SWITCH_ROOT_V1_H
#define S22PLUS_SWITCH_ROOT_V1_H
#define SW_REQUEST 37U
#define SW_ACCEPTED 168U
#define SW_RECORD 169U
#define SW_RETURN 38U
#define SW_RETURN_ACK 170U
#define SW_SEQUENCE 5U
#define SW_RETURN_SEQUENCE 6U
#define SW_MAX_RECORDS 256U
#define SW_STATE_MAGIC 0x31575253U
#define SW_STATE_VERSION 1U
#define SW_TIMEOUT_MS 300000ULL
#define SW_SETTLE_MS 5000ULL
#define SW_MAX_MOUNTS 32U
#define SW_MEMFD_SEALS 15
struct sw_child_state { int32_t pid, reaped, status, unknown; };
struct sw_state {
    uint32_t magic,version,sequence,next_record;
    uint8_t run[16],nonce[32],boot[32];
    uint64_t deadline_ms,root_device,old_device,tty_device;
    struct sw_child_state child[3];
    uint32_t settled,root_admitted,mount_count,reserved;
    uint32_t mount_ids[SW_MAX_MOUNTS];
    uint8_t mount_digest[32];
    uint8_t witness_digest[32];
};
_Static_assert(sizeof(struct sw_state)==384,"shared native/libc ARM64 state ABI");
enum sw_stage {
    SW_ENTER=1, SW_WORKERS=2, SW_ROOT=3, SW_STORAGE=4, SW_MOUNTS=5,
    SW_MOVE=6, SW_EXEC=7, SW_WITNESS=8, SW_DOWNLOAD=9, SW_LOG=10,
    SW_STOP=11
};
#endif
