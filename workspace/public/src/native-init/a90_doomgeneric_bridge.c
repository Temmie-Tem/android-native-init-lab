#include "a90_doomgeneric_bridge.h"

#include "a90_helper.h"
#include "a90_run.h"

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <netinet/in.h>
#include <sys/stat.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_CANDIDATE
#define A90_DOOMGENERIC_BRIDGE_CANDIDATE "v3025-doomgeneric-command-bridge"
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_ENGINE
#define A90_DOOMGENERIC_BRIDGE_ENGINE "doomgeneric-private-link-v3025"
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_HELPER_PATH
#define A90_DOOMGENERIC_BRIDGE_HELPER_PATH "/bin/a90_doomgeneric_private_engine_v3024"
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT
#define A90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT "/cache/a90-runtime/pkg/doom/v3024/"
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_PATH
#define A90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_PATH "/cache/a90-runtime/pkg/doom/v3024/DOOM1.WAD"
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_EXPECTED_WAD_SHA256
#define A90_DOOMGENERIC_BRIDGE_EXPECTED_WAD_SHA256 ""
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_FRAME_PATH
#define A90_DOOMGENERIC_BRIDGE_FRAME_PATH "/tmp/a90-doomgeneric-frame.xbgr8888"
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_INPUT_STATE_PATH
#define A90_DOOMGENERIC_BRIDGE_INPUT_STATE_PATH "/tmp/a90-doomgeneric-input.state"
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_INPUT_SOCKET_PATH
#define A90_DOOMGENERIC_BRIDGE_INPUT_SOCKET_PATH ""
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_INPUT_UDP_PORT
#define A90_DOOMGENERIC_BRIDGE_INPUT_UDP_PORT 0U
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES
#define A90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES 67108864LL
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES
#define A90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES 300
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_FRAME_WIDTH
#define A90_DOOMGENERIC_BRIDGE_FRAME_WIDTH 640U
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_FRAME_HEIGHT
#define A90_DOOMGENERIC_BRIDGE_FRAME_HEIGHT 400U
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_FRAME_STRIDE
#define A90_DOOMGENERIC_BRIDGE_FRAME_STRIDE (A90_DOOMGENERIC_BRIDGE_FRAME_WIDTH * 4U)
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_FRAME_BYTES
#define A90_DOOMGENERIC_BRIDGE_FRAME_BYTES (A90_DOOMGENERIC_BRIDGE_FRAME_STRIDE * A90_DOOMGENERIC_BRIDGE_FRAME_HEIGHT)
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_INPUT
#define A90_DOOMGENERIC_BRIDGE_INPUT "serial-doompad-to-DG_GetKey"
#endif

#define A90_DOOMGENERIC_INPUT_PACKET_MAGIC 0x41394450U
#define A90_DOOMGENERIC_INPUT_PACKET_VERSION 1U

struct a90_doomgeneric_input_packet {
    uint32_t magic;
    uint32_t version;
    uint32_t seq;
    uint32_t mask;
    uint32_t active;
};

#ifndef A90_DOOMGENERIC_BRIDGE_LOOP_FRAME_MS
#define A90_DOOMGENERIC_BRIDGE_LOOP_FRAME_MS 50U
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_SOUND
#define A90_DOOMGENERIC_BRIDGE_SOUND "disabled-nosound-nomusic"
#endif

static bool doomgeneric_helper_present(const char *path) {
    struct stat st;

    if (path == NULL || path[0] == '\0') {
        return false;
    }
    if (lstat(path, &st) < 0) {
        return false;
    }
    return S_ISREG(st.st_mode);
}

static bool doomgeneric_helper_executable(const char *path) {
    if (!doomgeneric_helper_present(path)) {
        return false;
    }
    return access(path, X_OK) == 0;
}

static bool doomgeneric_is_hex_sha256(const char *text) {
    size_t index;

    if (text == NULL || strlen(text) != 64U) {
        return false;
    }
    for (index = 0; index < 64U; ++index) {
        if (!isxdigit((unsigned char)text[index])) {
            return false;
        }
    }
    return true;
}

static bool doomgeneric_magic_ok(const char magic[5]) {
    return strcmp(magic, "IWAD") == 0 || strcmp(magic, "PWAD") == 0;
}

static void doomgeneric_fill_wad_stat(struct a90_doomgeneric_bridge_status *status) {
    struct stat st;

    if (status == NULL) {
        return;
    }
    if (lstat(status->runtime_wad_path, &st) < 0) {
        status->runtime_wad_present = false;
        status->runtime_wad_regular = false;
        status->runtime_wad_size_ok = false;
        status->runtime_wad_bytes = -1;
        return;
    }
    status->runtime_wad_present = true;
    status->runtime_wad_regular = S_ISREG(st.st_mode);
    status->runtime_wad_bytes = (long long)st.st_size;
    status->runtime_wad_size_ok = (
        status->runtime_wad_regular &&
        st.st_size > 0 &&
        (long long)st.st_size <= status->runtime_wad_max_bytes
    );
}

void a90_doomgeneric_bridge_get_status(struct a90_doomgeneric_bridge_status *status) {
    if (status == NULL) {
        return;
    }
    memset(status, 0, sizeof(*status));
    status->candidate = A90_DOOMGENERIC_BRIDGE_CANDIDATE;
    status->engine = A90_DOOMGENERIC_BRIDGE_ENGINE;
    status->helper_path = A90_DOOMGENERIC_BRIDGE_HELPER_PATH;
    status->runtime_wad_root = A90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT;
    status->runtime_wad_path = A90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_PATH;
    status->expected_wad_sha256 = A90_DOOMGENERIC_BRIDGE_EXPECTED_WAD_SHA256;
    status->frame_path = A90_DOOMGENERIC_BRIDGE_FRAME_PATH;
    status->input_state_path = A90_DOOMGENERIC_BRIDGE_INPUT_STATE_PATH;
    status->input_socket_path = A90_DOOMGENERIC_BRIDGE_INPUT_SOCKET_PATH;
    status->input_path = A90_DOOMGENERIC_BRIDGE_INPUT;
    status->sound_mode = A90_DOOMGENERIC_BRIDGE_SOUND;
    status->runtime_wad_max_bytes = A90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES;
    status->frame_width = A90_DOOMGENERIC_BRIDGE_FRAME_WIDTH;
    status->frame_height = A90_DOOMGENERIC_BRIDGE_FRAME_HEIGHT;
    status->frame_stride = A90_DOOMGENERIC_BRIDGE_FRAME_STRIDE;
    status->frame_bytes = A90_DOOMGENERIC_BRIDGE_FRAME_BYTES;
    status->loop_frame_ms = A90_DOOMGENERIC_BRIDGE_LOOP_FRAME_MS;
    status->input_udp_port = A90_DOOMGENERIC_BRIDGE_INPUT_UDP_PORT;
    status->helper_present = doomgeneric_helper_present(status->helper_path);
    status->helper_executable = doomgeneric_helper_executable(status->helper_path);
    doomgeneric_fill_wad_stat(status);
    status->wad_embedded_in_boot = false;
    status->visible_loop = true;
}

int a90_doomgeneric_bridge_verify_wad(const char *expected_sha256,
                                      struct a90_doomgeneric_wad_check *check) {
    struct a90_doomgeneric_bridge_status status;
    struct stat st;
    const char *expected;
    int fd;
    ssize_t rd;
    int rc;

    if (check == NULL) {
        return -EINVAL;
    }
    memset(check, 0, sizeof(*check));
    a90_doomgeneric_bridge_get_status(&status);
    expected = (expected_sha256 != NULL && expected_sha256[0] != '\0') ?
        expected_sha256 :
        status.expected_wad_sha256;

    check->path = status.runtime_wad_path;
    check->expected_sha256 = expected;
    check->bytes = -1;
    snprintf(check->actual_sha256, sizeof(check->actual_sha256), "-");
    snprintf(check->magic, sizeof(check->magic), "----");
    check->expected_sha256_valid = doomgeneric_is_hex_sha256(expected);

    if (!check->expected_sha256_valid) {
        return -EINVAL;
    }
    if (lstat(status.runtime_wad_path, &st) < 0) {
        check->stat_errno = errno;
        return -errno;
    }
    check->present = true;
    check->regular = S_ISREG(st.st_mode);
    check->bytes = (long long)st.st_size;
    check->size_ok = (
        check->regular &&
        st.st_size > 0 &&
        (long long)st.st_size <= status.runtime_wad_max_bytes
    );
    if (!check->regular || !check->size_ok) {
        return -EIO;
    }

    fd = open(status.runtime_wad_path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return -errno;
    }
    rd = read(fd, check->magic, 4);
    close(fd);
    if (rd != 4) {
        return -EIO;
    }
    check->magic[4] = '\0';
    check->magic_ok = doomgeneric_magic_ok(check->magic);
    if (!check->magic_ok) {
        return -EIO;
    }

    rc = a90_helper_sha256_file(
        status.runtime_wad_path,
        check->actual_sha256,
        sizeof(check->actual_sha256)
    );
    check->sha256_checked = rc == 0;
    if (rc < 0) {
        snprintf(check->actual_sha256, sizeof(check->actual_sha256), "hash-error:%d", -rc);
        return rc;
    }
    check->sha256_match = strcasecmp(check->actual_sha256, expected) == 0;
    check->ok = (
        check->present &&
        check->regular &&
        check->size_ok &&
        check->magic_ok &&
        check->sha256_checked &&
        check->sha256_match
    );
    return check->ok ? 0 : -EIO;
}

int a90_doomgeneric_bridge_probe(int timeout_ms, struct a90_run_result *result) {
    struct a90_run_result local_result;
    struct a90_doomgeneric_bridge_status status;
    struct a90_run_config config;
    char *const argv[] = {
        (char *)A90_DOOMGENERIC_BRIDGE_HELPER_PATH,
        NULL,
    };
    pid_t pid = -1;
    int rc;

    if (result == NULL) {
        result = &local_result;
    }
    memset(result, 0, sizeof(*result));
    a90_doomgeneric_bridge_get_status(&status);
    if (!status.helper_executable) {
        if (result != NULL) {
            result->rc = -ENOENT;
            result->saved_errno = ENOENT;
        }
        return -ENOENT;
    }
    if (timeout_ms <= 0) {
        timeout_ms = 3000;
    }

    memset(&config, 0, sizeof(config));
    config.tag = "doomgeneric-probe";
    config.argv = argv;
    config.stdio_mode = A90_RUN_STDIO_NULL;
    config.setsid = true;
    config.kill_process_group = true;
    config.timeout_ms = timeout_ms;
    config.stop_timeout_ms = 1000;

    rc = a90_run_spawn(&config, &pid);
    if (rc < 0) {
        if (result != NULL) {
            result->rc = rc;
            result->saved_errno = -rc;
        }
        return rc;
    }
    rc = a90_run_wait(pid, &config, result);
    if (rc < 0) {
        return rc;
    }
    return result->rc;
}

static void doomgeneric_fill_frame_render(struct a90_doomgeneric_frame_render *render,
                                          const struct a90_doomgeneric_bridge_status *status) {
    struct stat st;

    if (render == NULL || status == NULL) {
        return;
    }
    memset(render, 0, sizeof(*render));
    render->path = status->frame_path;
    render->width = status->frame_width;
    render->height = status->frame_height;
    render->stride = status->frame_stride;
    render->expected_bytes = status->frame_bytes;
    render->bytes = -1;
    render->geometry_ok = (
        render->width == 640U &&
        render->height == 400U &&
        render->stride == render->width * 4U &&
        render->expected_bytes == render->stride * render->height
    );
    if (lstat(status->frame_path, &st) < 0) {
        render->stat_errno = errno;
        return;
    }
    render->present = true;
    render->regular = S_ISREG(st.st_mode);
    render->bytes = (long long)st.st_size;
    render->size_ok = render->regular && st.st_size == (off_t)render->expected_bytes;
    render->ok = render->geometry_ok && render->size_ok;
}

int a90_doomgeneric_bridge_read_frame_render(struct a90_doomgeneric_frame_render *render) {
    struct a90_doomgeneric_bridge_status status;

    if (render == NULL) {
        return -EINVAL;
    }
    a90_doomgeneric_bridge_get_status(&status);
    doomgeneric_fill_frame_render(render, &status);
    return render->ok ? 0 : -EIO;
}

int a90_doomgeneric_bridge_write_input_state(const struct a90_doomgeneric_input_state *input) {
    struct a90_doomgeneric_bridge_status status;
    int fd;
    int rc;

    if (input == NULL) {
        return -EINVAL;
    }
    a90_doomgeneric_bridge_get_status(&status);
    fd = open(status.input_state_path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd < 0) {
        return -errno;
    }
    rc = dprintf(fd,
                 "seq=%u\n"
                 "forward=%d\n"
                 "back=%d\n"
                 "left=%d\n"
                 "right=%d\n"
                 "fire=%d\n"
                 "use=%d\n"
                 "menu=%d\n"
                 "run=%d\n"
                 "active=%d\n",
                 input->seq,
                 input->forward ? 1 : 0,
                 input->back ? 1 : 0,
                 input->left ? 1 : 0,
                 input->right ? 1 : 0,
                 input->fire ? 1 : 0,
                 input->use ? 1 : 0,
                 input->menu ? 1 : 0,
                 input->run ? 1 : 0,
                 input->active ? 1 : 0);
    if (close(fd) < 0 && rc >= 0) {
        return -errno;
    }
    return rc < 0 ? -EIO : 0;
}

static uint32_t doomgeneric_input_mask(const struct a90_doomgeneric_input_state *input) {
    uint32_t mask = 0U;

    if (input == NULL) {
        return 0U;
    }
    if (input->forward) {
        mask |= 1U << 0;
    }
    if (input->back) {
        mask |= 1U << 1;
    }
    if (input->left) {
        mask |= 1U << 2;
    }
    if (input->right) {
        mask |= 1U << 3;
    }
    if (input->fire) {
        mask |= 1U << 4;
    }
    if (input->use) {
        mask |= 1U << 5;
    }
    if (input->menu) {
        mask |= 1U << 6;
    }
    if (input->run) {
        mask |= 1U << 7;
    }
    return mask;
}

int a90_doomgeneric_bridge_send_input_socket(const struct a90_doomgeneric_input_state *input) {
    struct a90_doomgeneric_bridge_status status;
    struct sockaddr_un addr;
    struct a90_doomgeneric_input_packet packet;
    int fd;
    int saved_errno;
    size_t path_len;
    ssize_t sent;

    if (input == NULL) {
        return -EINVAL;
    }
    a90_doomgeneric_bridge_get_status(&status);
    if (status.input_socket_path == NULL || status.input_socket_path[0] == '\0') {
        return -ENOENT;
    }
    path_len = strlen(status.input_socket_path);
    if (path_len == 0U || path_len >= sizeof(addr.sun_path)) {
        return -ENAMETOOLONG;
    }
    fd = socket(AF_UNIX, SOCK_DGRAM, 0);
    if (fd < 0) {
        return -errno;
    }
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    snprintf(addr.sun_path, sizeof(addr.sun_path), "%s", status.input_socket_path);

    memset(&packet, 0, sizeof(packet));
    packet.magic = A90_DOOMGENERIC_INPUT_PACKET_MAGIC;
    packet.version = A90_DOOMGENERIC_INPUT_PACKET_VERSION;
    packet.seq = input->seq;
    packet.mask = doomgeneric_input_mask(input);
    packet.active = input->active ? 1U : 0U;

    sent = sendto(fd,
                  &packet,
                  sizeof(packet),
                  MSG_DONTWAIT,
                  (const struct sockaddr *)&addr,
                  sizeof(addr));
    saved_errno = errno;
    close(fd);
    if (sent != (ssize_t)sizeof(packet)) {
        return sent < 0 ? -saved_errno : -EIO;
    }
    return 0;
}

int a90_doomgeneric_bridge_render_frame(int frames,
                                        const char *expected_sha256,
                                        int timeout_ms,
                                        struct a90_doomgeneric_wad_check *check,
                                        struct a90_doomgeneric_frame_render *render,
                                        struct a90_run_result *result) {
    struct a90_run_result local_result;
    struct a90_doomgeneric_bridge_status status;
    struct a90_run_config config;
    char frames_arg[16];
    char *const argv[] = {
        (char *)A90_DOOMGENERIC_BRIDGE_HELPER_PATH,
        (char *)"--wad-frame-dump",
        (char *)A90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_PATH,
        (char *)"--frames",
        frames_arg,
        (char *)"--output",
        (char *)A90_DOOMGENERIC_BRIDGE_FRAME_PATH,
        NULL,
    };
    pid_t pid = -1;
    int rc;

    if (frames <= 0 || frames > A90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES) {
        return -EINVAL;
    }
    rc = a90_doomgeneric_bridge_verify_wad(expected_sha256, check);
    if (rc < 0) {
        return rc;
    }
    if (result == NULL) {
        result = &local_result;
    }
    memset(result, 0, sizeof(*result));
    a90_doomgeneric_bridge_get_status(&status);
    if (render != NULL) {
        doomgeneric_fill_frame_render(render, &status);
        render->present = false;
        render->regular = false;
        render->size_ok = false;
        render->ok = false;
        render->bytes = -1;
    }
    if (!status.helper_executable) {
        result->rc = -ENOENT;
        result->saved_errno = ENOENT;
        return -ENOENT;
    }
    if (timeout_ms <= 0) {
        timeout_ms = 15000;
    }
    snprintf(frames_arg, sizeof(frames_arg), "%d", frames);
    (void)unlink(status.frame_path);

    memset(&config, 0, sizeof(config));
    config.tag = "doomgeneric-sd-wad-frame";
    config.argv = argv;
    config.stdio_mode = A90_RUN_STDIO_NULL;
    config.setsid = true;
    config.kill_process_group = true;
    config.timeout_ms = timeout_ms;
    config.stop_timeout_ms = 1000;

    rc = a90_run_spawn(&config, &pid);
    if (rc < 0) {
        result->rc = rc;
        result->saved_errno = -rc;
        return rc;
    }
    rc = a90_run_wait(pid, &config, result);
    if (rc < 0) {
        doomgeneric_fill_frame_render(render, &status);
        return rc;
    }
    doomgeneric_fill_frame_render(render, &status);
    if (result->rc != 0) {
        return result->rc;
    }
    return render == NULL || render->ok ? 0 : -EIO;
}

int a90_doomgeneric_bridge_play(int frames,
                                const char *expected_sha256,
                                int timeout_ms,
                                struct a90_doomgeneric_wad_check *check,
                                struct a90_run_result *result) {
    struct a90_run_result local_result;
    struct a90_doomgeneric_bridge_status status;
    struct a90_run_config config;
    char frames_arg[16];
    char *const argv[] = {
        (char *)A90_DOOMGENERIC_BRIDGE_HELPER_PATH,
        (char *)"--wad-smoke",
        (char *)A90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_PATH,
        (char *)"--frames",
        frames_arg,
        NULL,
    };
    pid_t pid = -1;
    int rc;

    if (frames <= 0 || frames > A90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES) {
        return -EINVAL;
    }
    rc = a90_doomgeneric_bridge_verify_wad(expected_sha256, check);
    if (rc < 0) {
        return rc;
    }
    if (result == NULL) {
        result = &local_result;
    }
    memset(result, 0, sizeof(*result));
    a90_doomgeneric_bridge_get_status(&status);
    if (!status.helper_executable) {
        result->rc = -ENOENT;
        result->saved_errno = ENOENT;
        return -ENOENT;
    }
    if (timeout_ms <= 0) {
        timeout_ms = 15000;
    }
    snprintf(frames_arg, sizeof(frames_arg), "%d", frames);

    memset(&config, 0, sizeof(config));
    config.tag = "doomgeneric-sd-wad-smoke";
    config.argv = argv;
    config.stdio_mode = A90_RUN_STDIO_NULL;
    config.setsid = true;
    config.kill_process_group = true;
    config.timeout_ms = timeout_ms;
    config.stop_timeout_ms = 1000;

    rc = a90_run_spawn(&config, &pid);
    if (rc < 0) {
        result->rc = rc;
        result->saved_errno = -rc;
        return rc;
    }
    rc = a90_run_wait(pid, &config, result);
    if (rc < 0) {
        return rc;
    }
    return result->rc;
}

int a90_doomgeneric_bridge_start_frame_loop_helper(int frames,
                                                   const char *expected_sha256,
                                                   int frame_ms,
                                                   struct a90_doomgeneric_wad_check *check,
                                                   pid_t *pid_out) {
    struct a90_doomgeneric_bridge_status status;
    struct a90_run_config config;
    char frames_arg[16];
    char frame_ms_arg[16];
    char udp_port_arg[16];
    char *argv[18];
    size_t arg_index = 0U;
    int rc;

    if (pid_out == NULL || frames < 0 || frames > A90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES) {
        return -EINVAL;
    }
    if (frame_ms <= 0 || frame_ms > 250) {
        frame_ms = (int)A90_DOOMGENERIC_BRIDGE_LOOP_FRAME_MS;
    }
    rc = a90_doomgeneric_bridge_verify_wad(expected_sha256, check);
    if (rc < 0) {
        return rc;
    }
    a90_doomgeneric_bridge_get_status(&status);
    if (!status.helper_executable) {
        return -ENOENT;
    }
    snprintf(frames_arg, sizeof(frames_arg), "%d", frames);
    snprintf(frame_ms_arg, sizeof(frame_ms_arg), "%d", frame_ms);
    (void)unlink(status.frame_path);

    argv[arg_index++] = (char *)status.helper_path;
    argv[arg_index++] = (char *)"--wad-frame-loop";
    argv[arg_index++] = (char *)status.runtime_wad_path;
    argv[arg_index++] = (char *)"--frames";
    argv[arg_index++] = frames_arg;
    argv[arg_index++] = (char *)"--output";
    argv[arg_index++] = (char *)status.frame_path;
    argv[arg_index++] = (char *)"--input-state";
    argv[arg_index++] = (char *)status.input_state_path;
    argv[arg_index++] = (char *)"--frame-ms";
    argv[arg_index++] = frame_ms_arg;
    if (status.input_socket_path != NULL && status.input_socket_path[0] != '\0') {
        argv[arg_index++] = (char *)"--input-socket";
        argv[arg_index++] = (char *)status.input_socket_path;
    }
    if (status.input_udp_port > 0U && status.input_udp_port <= 65535U) {
        snprintf(udp_port_arg, sizeof(udp_port_arg), "%u", status.input_udp_port);
        argv[arg_index++] = (char *)"--input-udp";
        argv[arg_index++] = udp_port_arg;
    }
    argv[arg_index] = NULL;

    memset(&config, 0, sizeof(config));
    config.tag = "doomgeneric-sd-wad-frame-loop";
    config.argv = argv;
    config.stdio_mode = A90_RUN_STDIO_NULL;
    config.setsid = false;
    config.kill_process_group = false;
    config.timeout_ms = 0;
    config.stop_timeout_ms = 1000;

    return a90_run_spawn(&config, pid_out);
}
