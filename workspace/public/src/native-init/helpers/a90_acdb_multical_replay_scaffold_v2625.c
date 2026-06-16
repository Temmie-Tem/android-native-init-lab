/*
 * V2625 scaffold for future native ACDB multi-cal replay.
 *
 * Default builds describe the contract only.  Calibration ioctls are compiled
 * in only with A90_ENABLE_NATIVE_MULTICAL_EXECUTE after the operator accepts
 * the Gate-2 per-device manifest.
 */

#include <errno.h>
#include <fcntl.h>
#include <getopt.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define A90_RUN_ID "V2625"
#define A90_BUILD_TAG "v2625-audio-acdb-multical-replay-scaffold"
#define A90_MSM_AUDIO_CAL_PATH "/dev/msm_audio_cal"
#define A90_ION_PATH "/dev/ion"

#define A90_CAL_IOCTL_MAGIC 'a'
#define A90_AUDIO_ALLOCATE_CALIBRATION _IOWR(A90_CAL_IOCTL_MAGIC, 200, void *)
#define A90_AUDIO_DEALLOCATE_CALIBRATION _IOWR(A90_CAL_IOCTL_MAGIC, 201, void *)
#define A90_AUDIO_SET_CALIBRATION _IOWR(A90_CAL_IOCTL_MAGIC, 203, void *)

#define A90_ION_IOC_MAGIC 'I'
#define A90_ION_FLAG_CACHED 1U
#define A90_ION_SYSTEM_HEAP_ID 25U
#define A90_ION_SYSTEM_HEAP_MASK (1U << A90_ION_SYSTEM_HEAP_ID)

#define A90_AUDIO_CAL_TYPE_BASIC_SIZE 16
#define A90_AUDIO_CAL_BASIC_SIZE 32
#define A90_MAX_REPLAY_ENTRIES 8
#define A90_MAX_PAYLOAD_LEN (128U * 1024U)
#define A90_MAX_ENTRY_PATH 384

struct a90_ion_allocation_data {
    uint64_t len;
    uint32_t heap_id_mask;
    uint32_t flags;
    uint32_t fd;
    uint32_t unused;
};

#define A90_ION_IOC_ALLOC _IOWR(A90_ION_IOC_MAGIC, 0, struct a90_ion_allocation_data)

struct a90_audio_cal_basic {
    int32_t data_size;
    int32_t version;
    int32_t cal_type;
    int32_t cal_type_size;
    int32_t cal_hdr_version;
    int32_t buffer_number;
    int32_t cal_size;
    int32_t mem_handle;
};

struct a90_replay_entry {
    int32_t cal_type;
    int32_t buffer_number;
    char path[A90_MAX_ENTRY_PATH];
};

#ifdef A90_ENABLE_NATIVE_MULTICAL_EXECUTE
struct a90_replay_state {
    struct a90_replay_entry entry;
    uint8_t *payload;
    size_t payload_len;
    void *mapped;
    int ion_fd;
    int dmabuf_fd;
    bool allocated;
};
#endif

_Static_assert(sizeof(struct a90_audio_cal_basic) == A90_AUDIO_CAL_BASIC_SIZE,
               "audio_cal_basic scaffold must match the 32-byte kernel-consumed header");

static void usage(const char *argv0)
{
    fprintf(stderr,
            "usage: %s [--describe] [--execute --entry CAL_TYPE:BUFFER:PATH "
            "[--entry CAL_TYPE:BUFFER:PATH ...] --hold-sec N "
            "--ion-heap-mask HEX --ion-flags HEX]\n"
            "\n"
            "--execute is refused unless compiled with A90_ENABLE_NATIVE_MULTICAL_EXECUTE.\n",
            argv0);
}

static void print_describe_json(void)
{
    printf("{\n");
    printf("  \"run_id\": \"%s\",\n", A90_RUN_ID);
    printf("  \"build_tag\": \"%s\",\n", A90_BUILD_TAG);
    printf("  \"default_mode\": \"describe-only\",\n");
    printf("  \"execute_compiled_in\": %s,\n",
#ifdef A90_ENABLE_NATIVE_MULTICAL_EXECUTE
           "true"
#else
           "false"
#endif
    );
    printf("  \"native_calibration_ioctls_blocked_by_default\": true,\n");
    printf("  \"max_replay_entries\": %u,\n", A90_MAX_REPLAY_ENTRIES);
    printf("  \"max_payload_len\": %u,\n", A90_MAX_PAYLOAD_LEN);
    printf("  \"entry_format\": \"CAL_TYPE:BUFFER:PATH\",\n");
    printf("  \"sequence\": [\"allocate_each\", \"set_each\", \"hold\", \"deallocate_reverse\"],\n");
    printf("  \"keeps_msm_audio_cal_fd_open_across_probe\": true,\n");
    printf("  \"keeps_dmabuf_fds_open_across_probe\": true,\n");
    printf("  \"explicit_reverse_deallocate_cleanup\": true,\n");
    printf("  \"ion\": {\"device\": \"%s\", \"default_heap_mask\": \"0x%08x\", \"default_flags\": \"0x%08x\"}\n",
           A90_ION_PATH, A90_ION_SYSTEM_HEAP_MASK, A90_ION_FLAG_CACHED);
    printf("}\n");
}

static int parse_i32(const char *text, int32_t *value_out)
{
    char *end = NULL;
    long parsed;

    errno = 0;
    parsed = strtol(text, &end, 0);
    if (errno != 0 || !end || *end != '\0' || parsed < INT32_MIN || parsed > INT32_MAX)
        return -1;
    *value_out = (int32_t)parsed;
    return 0;
}

static int parse_entry(const char *spec, struct a90_replay_entry *entry)
{
    char local[A90_MAX_ENTRY_PATH + 64];
    char *first_colon;
    char *second_colon;
    size_t path_len;

    if (!spec || strlen(spec) >= sizeof(local))
        return -1;
    memset(local, 0, sizeof(local));
    memcpy(local, spec, strlen(spec));
    first_colon = strchr(local, ':');
    if (!first_colon)
        return -1;
    *first_colon = '\0';
    second_colon = strchr(first_colon + 1, ':');
    if (!second_colon)
        return -1;
    *second_colon = '\0';
    if (parse_i32(local, &entry->cal_type) != 0)
        return -1;
    if (parse_i32(first_colon + 1, &entry->buffer_number) != 0)
        return -1;
    if (entry->cal_type <= 0 || entry->buffer_number < 0)
        return -1;
    path_len = strlen(second_colon + 1);
    if (path_len == 0 || path_len >= sizeof(entry->path))
        return -1;
    memset(entry->path, 0, sizeof(entry->path));
    memcpy(entry->path, second_colon + 1, path_len);
    return 0;
}

static void fill_cal_packet(struct a90_audio_cal_basic *packet,
                            const struct a90_replay_entry *entry,
                            int32_t cal_size, int32_t mem_handle)
{
    memset(packet, 0, sizeof(*packet));
    packet->data_size = (int32_t)sizeof(*packet);
    packet->version = 0;
    packet->cal_type = entry->cal_type;
    packet->cal_type_size = A90_AUDIO_CAL_TYPE_BASIC_SIZE;
    packet->cal_hdr_version = 0;
    packet->buffer_number = entry->buffer_number;
    packet->cal_size = cal_size;
    packet->mem_handle = mem_handle;
}

#ifdef A90_ENABLE_NATIVE_MULTICAL_EXECUTE
static bool buffer_is_all_zero(const uint8_t *data, size_t len)
{
    size_t offset;

    for (offset = 0; offset < len; offset++) {
        if (data[offset] != 0)
            return false;
    }
    return true;
}

static int read_all_file(const char *path, uint8_t **data_out, size_t *size_out)
{
    int fd = -1;
    struct stat st;
    uint8_t *data = NULL;
    size_t done = 0;

    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        perror("open payload");
        return -1;
    }
    if (fstat(fd, &st) != 0) {
        perror("fstat payload");
        close(fd);
        return -1;
    }
    if (st.st_size <= 0 || st.st_size > (off_t)A90_MAX_PAYLOAD_LEN) {
        fprintf(stderr, "payload size out of bounds: %jd\n", (intmax_t)st.st_size);
        close(fd);
        return -1;
    }
    data = calloc(1, (size_t)st.st_size);
    if (!data) {
        perror("calloc payload");
        close(fd);
        return -1;
    }
    while (done < (size_t)st.st_size) {
        ssize_t read_count = read(fd, data + done, (size_t)st.st_size - done);
        if (read_count < 0) {
            if (errno == EINTR)
                continue;
            perror("read payload");
            free(data);
            close(fd);
            return -1;
        }
        if (read_count == 0) {
            fprintf(stderr, "short payload read\n");
            free(data);
            close(fd);
            return -1;
        }
        done += (size_t)read_count;
    }
    close(fd);
    if (buffer_is_all_zero(data, (size_t)st.st_size)) {
        fprintf(stderr, "payload is all-zero: %s\n", path);
        free(data);
        return -1;
    }
    *data_out = data;
    *size_out = (size_t)st.st_size;
    return 0;
}

static int ion_alloc_dmabuf(size_t len, uint32_t heap_mask, uint32_t flags,
                            int *ion_fd_out, int *dmabuf_fd_out)
{
    struct a90_ion_allocation_data alloc_data;
    int ion_fd = open(A90_ION_PATH, O_RDONLY | O_CLOEXEC);

    if (ion_fd < 0) {
        perror("open /dev/ion");
        return -1;
    }
    memset(&alloc_data, 0, sizeof(alloc_data));
    alloc_data.len = (uint64_t)len;
    alloc_data.heap_id_mask = heap_mask;
    alloc_data.flags = flags;
    if (ioctl(ion_fd, A90_ION_IOC_ALLOC, &alloc_data) != 0) {
        perror("ioctl ION_IOC_ALLOC");
        close(ion_fd);
        return -1;
    }
    if ((int)alloc_data.fd < 0) {
        fprintf(stderr, "ION_IOC_ALLOC returned invalid fd=%u\n", alloc_data.fd);
        close(ion_fd);
        return -1;
    }
    *ion_fd_out = ion_fd;
    *dmabuf_fd_out = (int)alloc_data.fd;
    return 0;
}

static int ioctl_cal(int fd, unsigned long request, struct a90_audio_cal_basic *packet,
                     const char *name)
{
    int rc = ioctl(fd, request, packet);

    if (rc != 0) {
        fprintf(stderr,
                "%s failed rc=%d errno=%d strerror=%s cal_type=%d buffer=%d cal_size=%d mem_handle=%d\n",
                name, rc, errno, strerror(errno), packet->cal_type, packet->buffer_number,
                packet->cal_size, packet->mem_handle);
        return -1;
    }
    fprintf(stderr, "%s ok cal_type=%d buffer=%d cal_size=%d mem_handle=%d\n",
            name, packet->cal_type, packet->buffer_number, packet->cal_size,
            packet->mem_handle);
    return 0;
}

static void init_state(struct a90_replay_state *state, const struct a90_replay_entry *entry)
{
    memset(state, 0, sizeof(*state));
    state->entry = *entry;
    state->mapped = MAP_FAILED;
    state->ion_fd = -1;
    state->dmabuf_fd = -1;
    state->allocated = false;
}

static void release_state(struct a90_replay_state *state)
{
    if (state->mapped != MAP_FAILED)
        munmap(state->mapped, state->payload_len);
    if (state->dmabuf_fd >= 0)
        close(state->dmabuf_fd);
    if (state->ion_fd >= 0)
        close(state->ion_fd);
    free(state->payload);
    state->payload = NULL;
}

static int prepare_state(struct a90_replay_state *state, uint32_t heap_mask, uint32_t ion_flags)
{
    if (read_all_file(state->entry.path, &state->payload, &state->payload_len) != 0)
        return -1;
    if (ion_alloc_dmabuf(state->payload_len, heap_mask, ion_flags,
                         &state->ion_fd, &state->dmabuf_fd) != 0)
        return -1;
    state->mapped = mmap(NULL, state->payload_len, PROT_READ | PROT_WRITE,
                         MAP_SHARED, state->dmabuf_fd, 0);
    if (state->mapped == MAP_FAILED) {
        perror("mmap dmabuf");
        return -1;
    }
    memcpy(state->mapped, state->payload, state->payload_len);
    if (msync(state->mapped, state->payload_len, MS_SYNC) != 0)
        perror("msync dmabuf");
    return 0;
}

static int execute_multical_replay(const struct a90_replay_entry *entries, size_t entry_count,
                                   unsigned int hold_sec, uint32_t heap_mask,
                                   uint32_t ion_flags)
{
    struct a90_replay_state states[A90_MAX_REPLAY_ENTRIES];
    size_t index;
    int cal_fd = -1;
    int ret = 1;

    if (entry_count == 0 || entry_count > A90_MAX_REPLAY_ENTRIES) {
        fprintf(stderr, "--entry count out of bounds: %zu\n", entry_count);
        return 2;
    }

    fprintf(stderr, "A90_ACDB_MULTICAL_REPLAY_START entries=%zu\n", entry_count);
    for (index = 0; index < entry_count; index++)
        init_state(&states[index], &entries[index]);

    for (index = 0; index < entry_count; index++) {
        if (prepare_state(&states[index], heap_mask, ion_flags) != 0)
            goto done;
    }

    cal_fd = open(A90_MSM_AUDIO_CAL_PATH, O_RDWR | O_CLOEXEC);
    if (cal_fd < 0) {
        perror("open /dev/msm_audio_cal");
        goto done;
    }

    for (index = 0; index < entry_count; index++) {
        struct a90_audio_cal_basic alloc_packet;
        struct a90_audio_cal_basic set_packet;

        fill_cal_packet(&alloc_packet, &states[index].entry, 0, states[index].dmabuf_fd);
        fill_cal_packet(&set_packet, &states[index].entry, (int32_t)states[index].payload_len,
                        states[index].dmabuf_fd);
        if (ioctl_cal(cal_fd, A90_AUDIO_ALLOCATE_CALIBRATION, &alloc_packet,
                      "AUDIO_ALLOCATE_CALIBRATION") != 0)
            goto done;
        states[index].allocated = true;
        fprintf(stderr, "A90_ACDB_MULTICAL_ALLOCATE_OK index=%zu cal_type=%d buffer=%d size=%zu\n",
                index, states[index].entry.cal_type, states[index].entry.buffer_number,
                states[index].payload_len);
        if (ioctl_cal(cal_fd, A90_AUDIO_SET_CALIBRATION, &set_packet,
                      "AUDIO_SET_CALIBRATION") != 0)
            goto done;
        fprintf(stderr, "A90_ACDB_MULTICAL_SET_OK index=%zu cal_type=%d buffer=%d size=%zu\n",
                index, states[index].entry.cal_type, states[index].entry.buffer_number,
                states[index].payload_len);
    }

    if (hold_sec > 0)
        sleep(hold_sec);
    ret = 0;

done:
    if (cal_fd >= 0) {
        for (index = entry_count; index > 0; index--) {
            size_t reverse_index = index - 1;
            if (states[reverse_index].allocated) {
                struct a90_audio_cal_basic dealloc_packet;
                fill_cal_packet(&dealloc_packet, &states[reverse_index].entry, 0,
                                states[reverse_index].dmabuf_fd);
                if (ioctl_cal(cal_fd, A90_AUDIO_DEALLOCATE_CALIBRATION, &dealloc_packet,
                              "AUDIO_DEALLOCATE_CALIBRATION") == 0) {
                    fprintf(stderr,
                            "A90_ACDB_MULTICAL_DEALLOCATE_OK index=%zu cal_type=%d buffer=%d\n",
                            reverse_index, states[reverse_index].entry.cal_type,
                            states[reverse_index].entry.buffer_number);
                    states[reverse_index].allocated = false;
                } else {
                    ret = 1;
                }
            }
        }
        close(cal_fd);
    }
    for (index = 0; index < entry_count; index++)
        release_state(&states[index]);
    fprintf(stderr, "A90_ACDB_MULTICAL_REPLAY_DONE rc=%d\n", ret);
    return ret;
}
#endif

int main(int argc, char **argv)
{
    bool describe = false;
    bool execute = false;
    struct a90_replay_entry entries[A90_MAX_REPLAY_ENTRIES];
    size_t entry_count = 0;
    unsigned int hold_sec = 0;
    uint32_t heap_mask = A90_ION_SYSTEM_HEAP_MASK;
    uint32_t ion_flags = A90_ION_FLAG_CACHED;

    static const struct option options[] = {
        {"describe", no_argument, NULL, 'd'},
        {"execute", no_argument, NULL, 'x'},
        {"entry", required_argument, NULL, 'e'},
        {"hold-sec", required_argument, NULL, 'H'},
        {"ion-heap-mask", required_argument, NULL, 'm'},
        {"ion-flags", required_argument, NULL, 'f'},
        {"help", no_argument, NULL, 'h'},
        {0, 0, 0, 0},
    };

    int opt;
    memset(entries, 0, sizeof(entries));
    while ((opt = getopt_long(argc, argv, "dxe:H:m:f:h", options, NULL)) != -1) {
        switch (opt) {
        case 'd':
            describe = true;
            break;
        case 'x':
            execute = true;
            break;
        case 'e':
            if (entry_count >= A90_MAX_REPLAY_ENTRIES ||
                parse_entry(optarg, &entries[entry_count]) != 0) {
                fprintf(stderr, "invalid --entry: %s\n", optarg ? optarg : "(null)");
                return 2;
            }
            entry_count++;
            break;
        case 'H':
            hold_sec = (unsigned int)strtoul(optarg, NULL, 0);
            break;
        case 'm':
            heap_mask = (uint32_t)strtoul(optarg, NULL, 0);
            break;
        case 'f':
            ion_flags = (uint32_t)strtoul(optarg, NULL, 0);
            break;
        case 'h':
            usage(argv[0]);
            return 0;
        default:
            usage(argv[0]);
            return 2;
        }
    }

    if (!execute || describe) {
        print_describe_json();
        return execute ? 2 : 0;
    }

#ifdef A90_ENABLE_NATIVE_MULTICAL_EXECUTE
    return execute_multical_replay(entries, entry_count, hold_sec, heap_mask, ion_flags);
#else
    fprintf(stderr,
            "A90 ACDB multi-cal replay execute mode is blocked in this scaffold build; "
            "compile-time A90_ENABLE_NATIVE_MULTICAL_EXECUTE is intentionally absent.\n");
    return 2;
#endif
}
