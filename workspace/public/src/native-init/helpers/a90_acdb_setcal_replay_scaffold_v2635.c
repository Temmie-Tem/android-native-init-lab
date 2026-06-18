/*
 * V2635 scaffold for future native ACDB replay using exact SET-cal args.
 *
 * Default builds describe the contract only. Calibration ioctls are compiled in
 * only with A90_ENABLE_NATIVE_SETCAL_REPLAY_EXECUTE.
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

#define A90_RUN_ID "V2635"
#define A90_BUILD_TAG "v2635-audio-acdb-setcal-replay-scaffold"
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

#define A90_AUDIO_CAL_TYPE_SIZE 16
#define A90_AUDIO_CAL_BASIC_SIZE 32
#define A90_OFF_DATA_SIZE 0
#define A90_OFF_CAL_TYPE 8
#define A90_OFF_BUFFER_NUMBER 20
#define A90_OFF_CAL_SIZE 24
#define A90_OFF_MEM_HANDLE 28

#define A90_MAX_REPLAY_ENTRIES 16
#define A90_MAX_ARG_LEN 512U
#define A90_MAX_PAYLOAD_LEN (256U * 1024U)
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

enum a90_entry_kind {
    A90_ENTRY_BASIC_PAYLOAD = 1,
    A90_ENTRY_EXACT_SET = 2,
};

struct a90_replay_entry {
    enum a90_entry_kind kind;
    int32_t cal_type;
    int32_t buffer_number;
    bool has_payload;
    char arg_path[A90_MAX_ENTRY_PATH];
    char payload_path[A90_MAX_ENTRY_PATH];
};

#ifdef A90_ENABLE_NATIVE_SETCAL_REPLAY_EXECUTE
struct a90_replay_state {
    struct a90_replay_entry entry;
    uint8_t *arg;
    size_t arg_len;
    uint8_t *set_arg;
    uint8_t *alloc_arg;
    uint8_t *dealloc_arg;
    uint8_t *payload;
    size_t payload_len;
    void *mapped;
    int ion_fd;
    int dmabuf_fd;
    bool allocated;
};
#endif

_Static_assert(sizeof(struct a90_audio_cal_basic) == A90_AUDIO_CAL_BASIC_SIZE,
               "basic audio cal packet must stay 32 bytes");

static void usage(const char *argv0)
{
    fprintf(stderr,
            "usage: %s [--describe] [--execute]\n"
            "  [--basic-payload CAL_TYPE:BUFFER:PAYLOAD]\n"
            "  [--exact-set ARG[:PAYLOAD]] [--hold-sec N]\n"
            "  [--ion-heap-mask HEX] [--ion-flags HEX]\n\n"
            "--execute is refused unless compiled with A90_ENABLE_NATIVE_SETCAL_REPLAY_EXECUTE.\n",
            argv0);
}

static void print_describe_json(void)
{
    printf("{\n");
    printf("  \"run_id\": \"%s\",\n", A90_RUN_ID);
    printf("  \"build_tag\": \"%s\",\n", A90_BUILD_TAG);
    printf("  \"default_mode\": \"describe-only\",\n");
    printf("  \"execute_compiled_in\": %s,\n",
#ifdef A90_ENABLE_NATIVE_SETCAL_REPLAY_EXECUTE
           "true"
#else
           "false"
#endif
    );
    printf("  \"entry_formats\": [\"--basic-payload CAL_TYPE:BUFFER:PAYLOAD\", \"--exact-set ARG[:PAYLOAD]\"],\n");
    printf("  \"exact_set_arg_replay\": true,\n");
    printf("  \"header_only_set_arg_replay\": true,\n");
    printf("  \"header_only_exact_arg_preserves_nonzero_cal_size\": true,\n");
    printf("  \"header_only_zero_cal_size_neutralizes_positive_mem_handle\": true,\n");
    printf("  \"fresh_dmabuf_handle_patch_offset\": %u,\n", A90_OFF_MEM_HANDLE);
    printf("  \"cal_size_patch_offset\": %u,\n", A90_OFF_CAL_SIZE);
    printf("  \"sequence\": [\"prepare_payloads\", \"set_each\", \"hold\", \"deallocate_payload_entries_reverse\"],\n");
    printf("  \"keeps_msm_audio_cal_fd_open_across_probe\": true,\n");
    printf("  \"keeps_dmabuf_fds_open_across_probe\": true,\n");
    printf("  \"native_calibration_ioctls_blocked_by_default\": true,\n");
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

static int copy_path(char *dst, size_t dst_len, const char *src)
{
    size_t src_len;

    if (!src)
        return -1;
    src_len = strlen(src);
    if (src_len == 0 || src_len >= dst_len)
        return -1;
    memset(dst, 0, dst_len);
    memcpy(dst, src, src_len);
    return 0;
}

static int parse_basic_payload(const char *spec, struct a90_replay_entry *entry)
{
    char local[A90_MAX_ENTRY_PATH + 64];
    char *first_colon;
    char *second_colon;

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
    memset(entry, 0, sizeof(*entry));
    entry->kind = A90_ENTRY_BASIC_PAYLOAD;
    entry->has_payload = true;
    if (parse_i32(local, &entry->cal_type) != 0 ||
        parse_i32(first_colon + 1, &entry->buffer_number) != 0 ||
        entry->cal_type <= 0 || entry->buffer_number < 0 ||
        copy_path(entry->payload_path, sizeof(entry->payload_path), second_colon + 1) != 0)
        return -1;
    return 0;
}

static int parse_exact_set(const char *spec, struct a90_replay_entry *entry)
{
    char local[(A90_MAX_ENTRY_PATH * 2) + 4];
    char *colon;

    if (!spec || strlen(spec) >= sizeof(local))
        return -1;
    memset(local, 0, sizeof(local));
    memcpy(local, spec, strlen(spec));
    colon = strchr(local, ':');
    memset(entry, 0, sizeof(*entry));
    entry->kind = A90_ENTRY_EXACT_SET;
    if (colon) {
        *colon = '\0';
        entry->has_payload = true;
        if (copy_path(entry->payload_path, sizeof(entry->payload_path), colon + 1) != 0)
            return -1;
    }
    if (copy_path(entry->arg_path, sizeof(entry->arg_path), local) != 0)
        return -1;
    return 0;
}

static int32_t read_le_i32(const uint8_t *data, size_t len, size_t off)
{
    uint32_t value;

    if (off + sizeof(value) > len)
        return INT32_MIN;
    memcpy(&value, data + off, sizeof(value));
    return (int32_t)value;
}

static void write_le_i32(uint8_t *data, size_t len, size_t off, int32_t value)
{
    uint32_t raw = (uint32_t)value;

    if (off + sizeof(raw) <= len)
        memcpy(data + off, &raw, sizeof(raw));
}

static void fill_basic_packet(struct a90_audio_cal_basic *packet, int32_t cal_type,
                              int32_t buffer_number, int32_t cal_size, int32_t mem_handle)
{
    memset(packet, 0, sizeof(*packet));
    packet->data_size = (int32_t)sizeof(*packet);
    packet->version = 0;
    packet->cal_type = cal_type;
    packet->cal_type_size = A90_AUDIO_CAL_TYPE_SIZE;
    packet->cal_hdr_version = 0;
    packet->buffer_number = buffer_number;
    packet->cal_size = cal_size;
    packet->mem_handle = mem_handle;
}

#ifdef A90_ENABLE_NATIVE_SETCAL_REPLAY_EXECUTE
static bool buffer_is_all_zero(const uint8_t *data, size_t len)
{
    size_t offset;

    for (offset = 0; offset < len; offset++) {
        if (data[offset] != 0)
            return false;
    }
    return true;
}

static int read_all_file(const char *path, size_t max_len, uint8_t **data_out, size_t *size_out)
{
    int fd = -1;
    struct stat st;
    uint8_t *data = NULL;
    size_t done = 0;

    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        perror("open input");
        return -1;
    }
    if (fstat(fd, &st) != 0) {
        perror("fstat input");
        close(fd);
        return -1;
    }
    if (st.st_size <= 0 || st.st_size > (off_t)max_len) {
        fprintf(stderr, "input size out of bounds: %s size=%jd max=%zu\n",
                path, (intmax_t)st.st_size, max_len);
        close(fd);
        return -1;
    }
    data = calloc(1, (size_t)st.st_size);
    if (!data) {
        perror("calloc input");
        close(fd);
        return -1;
    }
    while (done < (size_t)st.st_size) {
        ssize_t rc = read(fd, data + done, (size_t)st.st_size - done);
        if (rc < 0) {
            if (errno == EINTR)
                continue;
            perror("read input");
            free(data);
            close(fd);
            return -1;
        }
        if (rc == 0) {
            fprintf(stderr, "short read: %s\n", path);
            free(data);
            close(fd);
            return -1;
        }
        done += (size_t)rc;
    }
    close(fd);
    if (buffer_is_all_zero(data, (size_t)st.st_size)) {
        fprintf(stderr, "input is all-zero: %s\n", path);
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
    *ion_fd_out = ion_fd;
    *dmabuf_fd_out = (int)alloc_data.fd;
    return 0;
}

static int ioctl_cal(int fd, unsigned long request, const void *packet,
                     size_t packet_len, const char *name)
{
    int32_t cal_type = read_le_i32(packet, packet_len, A90_OFF_CAL_TYPE);
    int32_t buffer_number = read_le_i32(packet, packet_len, A90_OFF_BUFFER_NUMBER);
    int32_t cal_size = read_le_i32(packet, packet_len, A90_OFF_CAL_SIZE);
    int32_t mem_handle = read_le_i32(packet, packet_len, A90_OFF_MEM_HANDLE);
    int rc = ioctl(fd, request, packet);
    int saved_errno = rc == 0 ? 0 : errno;

    fprintf(stderr,
            "A90_ACDB_SETCAL_IOCTL_RESULT name=%s request=0x%lx rc=%d errno=%d strerror=%s cal_type=%d buffer=%d cal_size=%d mem_handle=%d arg_len=%zu\n",
            name, request, rc, saved_errno, strerror(saved_errno), cal_type,
            buffer_number, cal_size, mem_handle, packet_len);

    if (rc != 0) {
        fprintf(stderr,
                "%s failed rc=%d errno=%d strerror=%s cal_type=%d buffer=%d cal_size=%d mem_handle=%d arg_len=%zu\n",
                name, rc, saved_errno, strerror(saved_errno), cal_type, buffer_number, cal_size,
                mem_handle, packet_len);
        return -1;
    }
    fprintf(stderr, "%s ok cal_type=%d buffer=%d cal_size=%d mem_handle=%d arg_len=%zu\n",
            name, cal_type, buffer_number, cal_size, mem_handle, packet_len);
    return 0;
}

static void init_state(struct a90_replay_state *state, const struct a90_replay_entry *entry)
{
    memset(state, 0, sizeof(*state));
    state->entry = *entry;
    state->mapped = MAP_FAILED;
    state->ion_fd = -1;
    state->dmabuf_fd = -1;
}

static void release_state(struct a90_replay_state *state)
{
    if (state->mapped != MAP_FAILED)
        munmap(state->mapped, state->payload_len);
    if (state->dmabuf_fd >= 0)
        close(state->dmabuf_fd);
    if (state->ion_fd >= 0)
        close(state->ion_fd);
    free(state->arg);
    free(state->set_arg);
    free(state->alloc_arg);
    free(state->dealloc_arg);
    free(state->payload);
}

static int validate_exact_arg(struct a90_replay_state *state)
{
    int32_t data_size;
    int32_t cal_type;
    int32_t cal_size;

    if (read_all_file(state->entry.arg_path, A90_MAX_ARG_LEN, &state->arg, &state->arg_len) != 0)
        return -1;
    if (state->arg_len < A90_AUDIO_CAL_BASIC_SIZE) {
        fprintf(stderr, "exact arg too short: %s len=%zu\n", state->entry.arg_path, state->arg_len);
        return -1;
    }
    data_size = read_le_i32(state->arg, state->arg_len, A90_OFF_DATA_SIZE);
    cal_type = read_le_i32(state->arg, state->arg_len, A90_OFF_CAL_TYPE);
    cal_size = read_le_i32(state->arg, state->arg_len, A90_OFF_CAL_SIZE);
    if (data_size != (int32_t)state->arg_len || cal_type <= 0 || cal_size < 0) {
        fprintf(stderr, "invalid exact arg header: data_size=%d len=%zu cal_type=%d cal_size=%d\n",
                data_size, state->arg_len, cal_type, cal_size);
        return -1;
    }
    state->entry.cal_type = cal_type;
    state->entry.buffer_number = read_le_i32(state->arg, state->arg_len, A90_OFF_BUFFER_NUMBER);
    if (state->entry.has_payload && cal_size <= 0) {
        fprintf(stderr, "exact arg has payload path but cal_size=%d\n", cal_size);
        return -1;
    }
    return 0;
}

static int prepare_payload_state(struct a90_replay_state *state,
                                 uint32_t heap_mask, uint32_t ion_flags)
{
    if (read_all_file(state->entry.payload_path, A90_MAX_PAYLOAD_LEN,
                      &state->payload, &state->payload_len) != 0)
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

static int prepare_state(struct a90_replay_state *state,
                         uint32_t heap_mask, uint32_t ion_flags)
{
    if (state->entry.kind == A90_ENTRY_BASIC_PAYLOAD) {
        if (prepare_payload_state(state, heap_mask, ion_flags) != 0)
            return -1;
        state->arg_len = sizeof(struct a90_audio_cal_basic);
        state->set_arg = calloc(1, state->arg_len);
        state->alloc_arg = calloc(1, state->arg_len);
        state->dealloc_arg = calloc(1, state->arg_len);
        if (!state->set_arg || !state->alloc_arg || !state->dealloc_arg)
            return -1;
        fill_basic_packet((struct a90_audio_cal_basic *)state->set_arg, state->entry.cal_type,
                          state->entry.buffer_number, (int32_t)state->payload_len,
                          state->dmabuf_fd);
        fill_basic_packet((struct a90_audio_cal_basic *)state->alloc_arg, state->entry.cal_type,
                          state->entry.buffer_number, 0, state->dmabuf_fd);
        fill_basic_packet((struct a90_audio_cal_basic *)state->dealloc_arg, state->entry.cal_type,
                          state->entry.buffer_number, 0, state->dmabuf_fd);
        return 0;
    }

    if (validate_exact_arg(state) != 0)
        return -1;
    state->set_arg = calloc(1, state->arg_len);
    if (!state->set_arg)
        return -1;
    memcpy(state->set_arg, state->arg, state->arg_len);
    if (!state->entry.has_payload) {
        int32_t cal_size = read_le_i32(state->set_arg, state->arg_len, A90_OFF_CAL_SIZE);
        int32_t mem_handle = read_le_i32(state->set_arg, state->arg_len, A90_OFF_MEM_HANDLE);
        if (cal_size == 0 && mem_handle >= 0) {
            write_le_i32(state->set_arg, state->arg_len, A90_OFF_MEM_HANDLE, -1);
            fprintf(stderr,
                    "A90_ACDB_SETCAL_HEADER_MEM_HANDLE_NEUTRALIZED cal_type=%d buffer=%d original_mem_handle=%d arg_len=%zu\n",
                    state->entry.cal_type, state->entry.buffer_number, mem_handle,
                    state->arg_len);
        }
        fprintf(stderr,
                "A90_ACDB_SETCAL_HEADER_ONLY_EXACT_ARG cal_type=%d buffer=%d cal_size=%d arg_len=%zu\n",
                state->entry.cal_type, state->entry.buffer_number,
                read_le_i32(state->set_arg, state->arg_len, A90_OFF_CAL_SIZE),
                state->arg_len);
        return 0;
    }
    if (prepare_payload_state(state, heap_mask, ion_flags) != 0)
        return -1;
    if ((int32_t)state->payload_len != read_le_i32(state->arg, state->arg_len, A90_OFF_CAL_SIZE)) {
        fprintf(stderr, "payload length does not match exact arg cal_size cal_type=%d payload=%zu arg=%d\n",
                state->entry.cal_type, state->payload_len,
                read_le_i32(state->arg, state->arg_len, A90_OFF_CAL_SIZE));
        return -1;
    }
    state->alloc_arg = calloc(1, state->arg_len);
    state->dealloc_arg = calloc(1, state->arg_len);
    if (!state->alloc_arg || !state->dealloc_arg)
        return -1;
    memcpy(state->alloc_arg, state->arg, state->arg_len);
    memcpy(state->dealloc_arg, state->arg, state->arg_len);
    write_le_i32(state->set_arg, state->arg_len, A90_OFF_MEM_HANDLE, state->dmabuf_fd);
    write_le_i32(state->set_arg, state->arg_len, A90_OFF_CAL_SIZE, (int32_t)state->payload_len);
    write_le_i32(state->alloc_arg, state->arg_len, A90_OFF_MEM_HANDLE, state->dmabuf_fd);
    write_le_i32(state->alloc_arg, state->arg_len, A90_OFF_CAL_SIZE, 0);
    write_le_i32(state->dealloc_arg, state->arg_len, A90_OFF_MEM_HANDLE, state->dmabuf_fd);
    write_le_i32(state->dealloc_arg, state->arg_len, A90_OFF_CAL_SIZE, 0);
    return 0;
}

static int execute_replay(const struct a90_replay_entry *entries, size_t entry_count,
                          unsigned int hold_sec, uint32_t heap_mask, uint32_t ion_flags)
{
    struct a90_replay_state states[A90_MAX_REPLAY_ENTRIES];
    size_t index;
    int cal_fd = -1;
    int ret = 1;

    if (entry_count == 0 || entry_count > A90_MAX_REPLAY_ENTRIES) {
        fprintf(stderr, "--entry count out of bounds: %zu\n", entry_count);
        return 2;
    }
    fprintf(stderr, "A90_ACDB_SETCAL_REPLAY_START entries=%zu\n", entry_count);
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
        if (states[index].entry.has_payload) {
            if (ioctl_cal(cal_fd, A90_AUDIO_ALLOCATE_CALIBRATION, states[index].alloc_arg,
                          states[index].arg_len, "AUDIO_ALLOCATE_CALIBRATION") != 0)
                goto done;
            states[index].allocated = true;
            fprintf(stderr, "A90_ACDB_SETCAL_ALLOCATE_OK index=%zu cal_type=%d size=%zu\n",
                    index, states[index].entry.cal_type, states[index].payload_len);
        }
        if (ioctl_cal(cal_fd, A90_AUDIO_SET_CALIBRATION, states[index].set_arg,
                      states[index].arg_len, "AUDIO_SET_CALIBRATION") != 0)
            goto done;
        fprintf(stderr, "A90_ACDB_SETCAL_SET_OK index=%zu cal_type=%d kind=%d has_payload=%d\n",
                index, states[index].entry.cal_type, states[index].entry.kind,
                states[index].entry.has_payload ? 1 : 0);
    }
    if (hold_sec > 0)
        sleep(hold_sec);
    ret = 0;

done:
    if (cal_fd >= 0) {
        for (index = entry_count; index > 0; index--) {
            size_t reverse_index = index - 1;
            if (states[reverse_index].allocated) {
                if (ioctl_cal(cal_fd, A90_AUDIO_DEALLOCATE_CALIBRATION,
                              states[reverse_index].dealloc_arg,
                              states[reverse_index].arg_len,
                              "AUDIO_DEALLOCATE_CALIBRATION") == 0) {
                    fprintf(stderr, "A90_ACDB_SETCAL_DEALLOCATE_OK index=%zu cal_type=%d\n",
                            reverse_index, states[reverse_index].entry.cal_type);
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
    fprintf(stderr, "A90_ACDB_SETCAL_REPLAY_DONE rc=%d\n", ret);
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
    int opt;

    static const struct option options[] = {
        {"describe", no_argument, NULL, 'd'},
        {"execute", no_argument, NULL, 'x'},
        {"basic-payload", required_argument, NULL, 'b'},
        {"exact-set", required_argument, NULL, 'e'},
        {"hold-sec", required_argument, NULL, 'H'},
        {"ion-heap-mask", required_argument, NULL, 'm'},
        {"ion-flags", required_argument, NULL, 'f'},
        {"help", no_argument, NULL, 'h'},
        {0, 0, 0, 0},
    };

    memset(entries, 0, sizeof(entries));
    while ((opt = getopt_long(argc, argv, "dxb:e:H:m:f:h", options, NULL)) != -1) {
        switch (opt) {
        case 'd':
            describe = true;
            break;
        case 'x':
            execute = true;
            break;
        case 'b':
            if (entry_count >= A90_MAX_REPLAY_ENTRIES ||
                parse_basic_payload(optarg, &entries[entry_count]) != 0) {
                fprintf(stderr, "invalid --basic-payload: %s\n", optarg ? optarg : "(null)");
                return 2;
            }
            entry_count++;
            break;
        case 'e':
            if (entry_count >= A90_MAX_REPLAY_ENTRIES ||
                parse_exact_set(optarg, &entries[entry_count]) != 0) {
                fprintf(stderr, "invalid --exact-set: %s\n", optarg ? optarg : "(null)");
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
        default:
            usage(argv[0]);
            return opt == 'h' ? 0 : 2;
        }
    }
    if (describe || !execute) {
        print_describe_json();
        if (!execute)
            return 0;
    }
#ifndef A90_ENABLE_NATIVE_SETCAL_REPLAY_EXECUTE
    if (execute) {
        fprintf(stderr, "execute mode is blocked in this scaffold build\n");
        return 3;
    }
#else
    if (execute)
        return execute_replay(entries, entry_count, hold_sec, heap_mask, ion_flags);
#endif
    return 0;
}
