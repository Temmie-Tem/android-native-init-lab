/*
 * V2474 host-only scaffold for future native ACDB replay.
 *
 * Default builds intentionally do not execute calibration ioctls.  The live
 * replay code is compiled only with A90_ENABLE_NATIVE_CALIBRATION_EXECUTE after
 * the real payload bytes, length, SHA-256, mem_handle policy, and cleanup policy
 * are pinned in a later report.
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

#define A90_RUN_ID "V2474"
#define A90_BUILD_TAG "v2474-audio-acdb-replay-scaffold"
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

#define A90_CORE_CUSTOM_TOPOLOGIES_CAL_TYPE 39
#define A90_BUFFER_NUMBER_ZERO 0
#define A90_EXPECTED_TOPOLOGY_PAYLOAD_LEN 4916U
#define A90_AUDIO_CAL_TYPE_BASIC_SIZE 16
#define A90_AUDIO_CAL_BASIC_SIZE 32

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

_Static_assert(sizeof(struct a90_audio_cal_basic) == A90_AUDIO_CAL_BASIC_SIZE,
               "audio_cal_basic scaffold must match the 32-byte kernel-consumed header");

static void print_describe_json(void)
{
    printf("{\n");
    printf("  \"run_id\": \"%s\",\n", A90_RUN_ID);
    printf("  \"build_tag\": \"%s\",\n", A90_BUILD_TAG);
    printf("  \"default_mode\": \"describe-only\",\n");
    printf("  \"execute_compiled_in\": %s,\n",
#ifdef A90_ENABLE_NATIVE_CALIBRATION_EXECUTE
           "true"
#else
           "false"
#endif
    );
    printf("  \"native_calibration_ioctls_blocked_by_default\": true,\n");
    printf("  \"expected_payload_len\": %u,\n", A90_EXPECTED_TOPOLOGY_PAYLOAD_LEN);
    printf("  \"calibration\": {\n");
    printf("    \"device\": \"%s\",\n", A90_MSM_AUDIO_CAL_PATH);
    printf("    \"cal_type\": %d,\n", A90_CORE_CUSTOM_TOPOLOGIES_CAL_TYPE);
    printf("    \"buffer_number\": %d,\n", A90_BUFFER_NUMBER_ZERO);
    printf("    \"sequence\": [\"AUDIO_ALLOCATE_CALIBRATION\", \"AUDIO_SET_CALIBRATION\", \"AUDIO_DEALLOCATE_CALIBRATION\"],\n");
    printf("    \"keeps_msm_audio_cal_fd_open_across_probe\": true,\n");
    printf("    \"keeps_dmabuf_fd_open_across_probe\": true,\n");
    printf("    \"explicit_deallocate_cleanup\": true\n");
    printf("  },\n");
    printf("  \"ion\": {\n");
    printf("    \"device\": \"%s\",\n", A90_ION_PATH);
    printf("    \"alloc_ioctl\": \"ION_IOC_ALLOC\",\n");
    printf("    \"default_heap_mask\": \"0x%08x\",\n", A90_ION_SYSTEM_HEAP_MASK);
    printf("    \"default_flags\": \"0x%08x\"\n", A90_ION_FLAG_CACHED);
    printf("  }\n");
    printf("}\n");
}

static void usage(const char *argv0)
{
    fprintf(stderr,
            "usage: %s [--describe] [--execute --payload PATH --hold-sec N "
            "--ion-heap-mask HEX --ion-flags HEX]\n"
            "\n"
            "Default builds are host-only scaffold builds.  --execute is refused\n"
            "unless the binary is compiled with A90_ENABLE_NATIVE_CALIBRATION_EXECUTE.\n",
            argv0);
}

static void fill_cal_packet(struct a90_audio_cal_basic *packet, int32_t cal_size, int32_t mem_handle)
{
    memset(packet, 0, sizeof(*packet));
    packet->data_size = (int32_t)sizeof(*packet);
    packet->version = 0;
    packet->cal_type = A90_CORE_CUSTOM_TOPOLOGIES_CAL_TYPE;
    packet->cal_type_size = A90_AUDIO_CAL_TYPE_BASIC_SIZE;
    packet->cal_hdr_version = 0;
    packet->buffer_number = A90_BUFFER_NUMBER_ZERO;
    packet->cal_size = cal_size;
    packet->mem_handle = mem_handle;
}

#ifdef A90_ENABLE_NATIVE_CALIBRATION_EXECUTE
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
    if (st.st_size <= 0 || st.st_size > 1024 * 1024) {
        fprintf(stderr, "payload size out of scaffold bounds: %jd\n", (intmax_t)st.st_size);
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
        ssize_t rc = read(fd, data + done, (size_t)st.st_size - done);
        if (rc < 0) {
            if (errno == EINTR)
                continue;
            perror("read payload");
            free(data);
            close(fd);
            return -1;
        }
        if (rc == 0) {
            fprintf(stderr, "short payload read\n");
            free(data);
            close(fd);
            return -1;
        }
        done += (size_t)rc;
    }
    close(fd);
    *data_out = data;
    *size_out = (size_t)st.st_size;
    return 0;
}

static int ion_alloc_dmabuf(size_t len, uint32_t heap_mask, uint32_t flags, int *ion_fd_out, int *dmabuf_fd_out)
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

static int ioctl_cal(int fd, unsigned long request, struct a90_audio_cal_basic *packet, const char *name)
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
            name, packet->cal_type, packet->buffer_number, packet->cal_size, packet->mem_handle);
    return 0;
}

static int execute_replay(const char *payload_path, unsigned int hold_sec, uint32_t heap_mask, uint32_t ion_flags)
{
    uint8_t *payload = NULL;
    void *mapped = MAP_FAILED;
    size_t payload_len = 0;
    int ion_fd = -1;
    int dmabuf_fd = -1;
    int cal_fd = -1;
    bool allocated = false;
    int ret = 1;
    struct a90_audio_cal_basic alloc_packet;
    struct a90_audio_cal_basic set_packet;
    struct a90_audio_cal_basic dealloc_packet;

    if (!payload_path) {
        fprintf(stderr, "--payload is required for execute mode\n");
        return 2;
    }
    if (read_all_file(payload_path, &payload, &payload_len) != 0)
        goto done;
    if (payload_len != A90_EXPECTED_TOPOLOGY_PAYLOAD_LEN) {
        fprintf(stderr, "payload length %zu does not match expected %u\n",
                payload_len, A90_EXPECTED_TOPOLOGY_PAYLOAD_LEN);
        goto done;
    }
    if (ion_alloc_dmabuf(payload_len, heap_mask, ion_flags, &ion_fd, &dmabuf_fd) != 0)
        goto done;
    mapped = mmap(NULL, payload_len, PROT_READ | PROT_WRITE, MAP_SHARED, dmabuf_fd, 0);
    if (mapped == MAP_FAILED) {
        perror("mmap dmabuf");
        goto done;
    }
    memcpy(mapped, payload, payload_len);
    if (msync(mapped, payload_len, MS_SYNC) != 0)
        perror("msync dmabuf");

    cal_fd = open(A90_MSM_AUDIO_CAL_PATH, O_RDWR | O_CLOEXEC);
    if (cal_fd < 0) {
        perror("open /dev/msm_audio_cal");
        goto done;
    }

    fill_cal_packet(&alloc_packet, 0, dmabuf_fd);
    fill_cal_packet(&set_packet, (int32_t)payload_len, dmabuf_fd);
    fill_cal_packet(&dealloc_packet, 0, dmabuf_fd);

    if (ioctl_cal(cal_fd, A90_AUDIO_ALLOCATE_CALIBRATION, &alloc_packet,
                  "AUDIO_ALLOCATE_CALIBRATION") != 0)
        goto done;
    allocated = true;
    if (ioctl_cal(cal_fd, A90_AUDIO_SET_CALIBRATION, &set_packet,
                  "AUDIO_SET_CALIBRATION") != 0)
        goto done;

    if (hold_sec > 0)
        sleep(hold_sec);

    if (ioctl_cal(cal_fd, A90_AUDIO_DEALLOCATE_CALIBRATION, &dealloc_packet,
                  "AUDIO_DEALLOCATE_CALIBRATION") != 0)
        goto done;
    allocated = false;
    ret = 0;

done:
    if (allocated && cal_fd >= 0) {
        fill_cal_packet(&dealloc_packet, 0, dmabuf_fd);
        (void)ioctl_cal(cal_fd, A90_AUDIO_DEALLOCATE_CALIBRATION, &dealloc_packet,
                        "AUDIO_DEALLOCATE_CALIBRATION_cleanup");
    }
    if (cal_fd >= 0)
        close(cal_fd);
    if (mapped != MAP_FAILED)
        munmap(mapped, payload_len);
    if (dmabuf_fd >= 0)
        close(dmabuf_fd);
    if (ion_fd >= 0)
        close(ion_fd);
    free(payload);
    return ret;
}
#endif

int main(int argc, char **argv)
{
    bool describe = false;
    bool execute = false;
    const char *payload_path = NULL;
    unsigned int hold_sec = 0;
    uint32_t heap_mask = A90_ION_SYSTEM_HEAP_MASK;
    uint32_t ion_flags = A90_ION_FLAG_CACHED;

    static const struct option options[] = {
        {"describe", no_argument, NULL, 'd'},
        {"execute", no_argument, NULL, 'x'},
        {"payload", required_argument, NULL, 'p'},
        {"hold-sec", required_argument, NULL, 'H'},
        {"ion-heap-mask", required_argument, NULL, 'm'},
        {"ion-flags", required_argument, NULL, 'f'},
        {"help", no_argument, NULL, 'h'},
        {0, 0, 0, 0},
    };

    int opt;
    while ((opt = getopt_long(argc, argv, "dxp:H:m:f:h", options, NULL)) != -1) {
        switch (opt) {
        case 'd':
            describe = true;
            break;
        case 'x':
            execute = true;
            break;
        case 'p':
            payload_path = optarg;
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

#ifdef A90_ENABLE_NATIVE_CALIBRATION_EXECUTE
    return execute_replay(payload_path, hold_sec, heap_mask, ion_flags);
#else
    fprintf(stderr,
            "A90 ACDB replay execute mode is blocked in this host-only scaffold build; "
            "compile-time A90_ENABLE_NATIVE_CALIBRATION_EXECUTE is intentionally absent.\n");
    return 2;
#endif
}
