#define _GNU_SOURCE
#include <arpa/inet.h>
#include <endian.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/qrtr.h>
#include <poll.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

#ifndef AF_QIPCRTR
#define AF_QIPCRTR 42
#endif

#define A90_SERVLOC_SERVICE 64U
#define A90_SERVLOC_INSTANCE_ENCODED 257U
#define A90_SERVLOC_GET_DOMAIN_LIST_MSG_ID 0x0021U
#define A90_SERVLOC_TXN_ID 1U
#define A90_SERVLOC_READBACK_MS 1500U
#define A90_SERVLOC_RESPONSE_MS 2500U

static long monotonic_ms(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) {
        return 0;
    }
    return (long)ts.tv_sec * 1000L + ts.tv_nsec / 1000000L;
}

static uint16_t read_le16_bytes(const uint8_t *data) {
    uint16_t value = 0;
    memcpy(&value, data, sizeof(value));
    return le16toh(value);
}

static uint32_t read_le32_bytes(const uint8_t *data) {
    uint32_t value = 0;
    memcpy(&value, data, sizeof(value));
    return le32toh(value);
}

static void print_hex(const char *key, const uint8_t *data, size_t len) {
    printf("%s=", key);
    for (size_t i = 0; i < len; i++) {
        printf("%02x", data[i]);
    }
    printf("\n");
}

static void print_ascii_escaped(const uint8_t *data, size_t len) {
    for (size_t i = 0; i < len; i++) {
        unsigned char ch = data[i];
        if (ch >= 0x20 && ch <= 0x7e && ch != '\\') {
            putchar(ch);
        } else if (ch == '\\') {
            printf("\\\\");
        } else {
            printf("\\x%02x", ch);
        }
    }
}

static int open_qrtr_socket(void) {
    int fd = socket(AF_QIPCRTR, SOCK_DGRAM | SOCK_CLOEXEC, 0);
    if (fd >= 0) {
        return fd;
    }
    if (errno == EINVAL) {
        fd = socket(AF_QIPCRTR, SOCK_DGRAM, 0);
        if (fd >= 0) {
            (void)fcntl(fd, F_SETFD, FD_CLOEXEC);
        }
    }
    return fd;
}

static int send_lookup(int fd, uint32_t cmd) {
    struct qrtr_ctrl_pkt packet;
    struct sockaddr_qrtr dest;
    ssize_t sent;

    memset(&packet, 0, sizeof(packet));
    packet.cmd = htole32(cmd);
    packet.server.service = htole32(A90_SERVLOC_SERVICE);
    packet.server.instance = htole32(A90_SERVLOC_INSTANCE_ENCODED);

    memset(&dest, 0, sizeof(dest));
    dest.sq_family = AF_QIPCRTR;
    dest.sq_node = QRTR_NODE_BCAST;
    dest.sq_port = QRTR_PORT_CTRL;

    sent = sendto(fd, &packet, sizeof(packet), 0, (const struct sockaddr *)&dest, sizeof(dest));
    if (sent < 0) {
        printf("a90_servloc_query.lookup_%s.rc=-1\n", cmd == QRTR_TYPE_NEW_LOOKUP ? "new" : "del");
        printf("a90_servloc_query.lookup_%s.errno=%d\n", cmd == QRTR_TYPE_NEW_LOOKUP ? "new" : "del", errno);
        printf("a90_servloc_query.lookup_%s.error=%s\n", cmd == QRTR_TYPE_NEW_LOOKUP ? "new" : "del", strerror(errno));
        return -1;
    }
    printf("a90_servloc_query.lookup_%s.rc=0\n", cmd == QRTR_TYPE_NEW_LOOKUP ? "new" : "del");
    printf("a90_servloc_query.lookup_%s.bytes=%zd\n", cmd == QRTR_TYPE_NEW_LOOKUP ? "new" : "del", sent);
    return 0;
}

static bool find_servloc_endpoint(uint32_t *node, uint32_t *port) {
    int fd = open_qrtr_socket();
    long deadline;
    unsigned int events = 0;

    *node = 0;
    *port = 0;
    if (fd < 0) {
        printf("a90_servloc_query.lookup_socket.rc=-1\n");
        printf("a90_servloc_query.lookup_socket.errno=%d\n", errno);
        printf("a90_servloc_query.lookup_socket.error=%s\n", strerror(errno));
        return false;
    }
    printf("a90_servloc_query.lookup_socket.rc=0\n");
    if (send_lookup(fd, QRTR_TYPE_NEW_LOOKUP) < 0) {
        close(fd);
        return false;
    }
    deadline = monotonic_ms() + A90_SERVLOC_READBACK_MS;
    while (events < 8U) {
        struct pollfd pfd = {.fd = fd, .events = POLLIN, .revents = 0};
        struct qrtr_ctrl_pkt packet;
        struct sockaddr_qrtr from;
        socklen_t from_len = sizeof(from);
        long now = monotonic_ms();
        int poll_rc;
        ssize_t received;
        uint32_t cmd = 0, service = 0, instance = 0, event_node = 0, event_port = 0;

        if (now >= deadline) {
            break;
        }
        poll_rc = poll(&pfd, 1, (int)(deadline - now));
        if (poll_rc == 0) {
            break;
        }
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            printf("a90_servloc_query.lookup_poll.rc=-1\n");
            printf("a90_servloc_query.lookup_poll.errno=%d\n", errno);
            break;
        }
        if ((pfd.revents & POLLIN) == 0) {
            printf("a90_servloc_query.lookup_event.%u.revents=%d\n", events, pfd.revents);
            if ((pfd.revents & (POLLERR | POLLHUP | POLLNVAL)) != 0) {
                break;
            }
            continue;
        }
        memset(&packet, 0, sizeof(packet));
        memset(&from, 0, sizeof(from));
        received = recvfrom(fd, &packet, sizeof(packet), 0, (struct sockaddr *)&from, &from_len);
        if (received < 0) {
            if (errno == EINTR) {
                continue;
            }
            printf("a90_servloc_query.lookup_recv.rc=-1\n");
            printf("a90_servloc_query.lookup_recv.errno=%d\n", errno);
            break;
        }
        if (received >= (ssize_t)sizeof(uint32_t)) {
            cmd = le32toh(packet.cmd);
        }
        if (received >= (ssize_t)sizeof(packet)) {
            service = le32toh(packet.server.service);
            instance = le32toh(packet.server.instance);
            event_node = le32toh(packet.server.node);
            event_port = le32toh(packet.server.port);
        }
        printf("a90_servloc_query.lookup_event.%u.bytes=%zd\n", events, received);
        printf("a90_servloc_query.lookup_event.%u.cmd=%u\n", events, cmd);
        printf("a90_servloc_query.lookup_event.%u.service=%u\n", events, service);
        printf("a90_servloc_query.lookup_event.%u.instance=%u\n", events, instance);
        printf("a90_servloc_query.lookup_event.%u.node=%u\n", events, event_node);
        printf("a90_servloc_query.lookup_event.%u.port=%u\n", events, event_port);
        events++;
        if (cmd == QRTR_TYPE_NEW_SERVER && service == A90_SERVLOC_SERVICE &&
            instance == A90_SERVLOC_INSTANCE_ENCODED && event_node != 0U && event_port != 0U) {
            *node = event_node;
            *port = event_port;
            break;
        }
        if (cmd == QRTR_TYPE_NEW_SERVER && service == 0U && instance == 0U && event_node == 0U && event_port == 0U) {
            break;
        }
    }
    (void)send_lookup(fd, QRTR_TYPE_DEL_LOOKUP);
    close(fd);
    printf("a90_servloc_query.lookup.events=%u\n", events);
    printf("a90_servloc_query.endpoint.found=%u\n", (*node != 0U && *port != 0U) ? 1U : 0U);
    printf("a90_servloc_query.endpoint.node=%u\n", *node);
    printf("a90_servloc_query.endpoint.port=%u\n", *port);
    return *node != 0U && *port != 0U;
}

static int parse_domain_entry(unsigned int index, const uint8_t *data, size_t len, size_t *offset, unsigned int *wlan_like) {
    uint8_t name_len;
    const uint8_t *name;
    uint32_t instance_id;
    uint8_t service_data_valid;
    uint32_t service_data;
    bool contains_wlan = false;

    if (*offset >= len) {
        printf("a90_servloc_query.domain.%u.status=truncated-before-name-len\n", index);
        return 0;
    }
    name_len = data[(*offset)++];
    if (*offset + (size_t)name_len + 9U > len) {
        printf("a90_servloc_query.domain.%u.name_len=%u\n", index, (unsigned int)name_len);
        printf("a90_servloc_query.domain.%u.status=truncated-entry\n", index);
        return 0;
    }
    name = data + *offset;
    for (uint8_t i = 0; i < name_len; i++) {
        if (i + 3U < name_len && name[i] == 'w' && name[i + 1U] == 'l' && name[i + 2U] == 'a' && name[i + 3U] == 'n') {
            contains_wlan = true;
        }
    }
    *offset += name_len;
    instance_id = read_le32_bytes(data + *offset);
    *offset += sizeof(uint32_t);
    service_data_valid = data[(*offset)++];
    service_data = read_le32_bytes(data + *offset);
    *offset += sizeof(uint32_t);
    if (contains_wlan) {
        (*wlan_like)++;
    }
    printf("a90_servloc_query.domain.%u.name_len=%u\n", index, (unsigned int)name_len);
    printf("a90_servloc_query.domain.%u.name=", index);
    print_ascii_escaped(name, name_len);
    printf("\n");
    printf("a90_servloc_query.domain.%u.instance_id=%u\n", index, instance_id);
    printf("a90_servloc_query.domain.%u.service_data_valid=%u\n", index, (unsigned int)service_data_valid);
    printf("a90_servloc_query.domain.%u.service_data=%u\n", index, service_data);
    printf("a90_servloc_query.domain.%u.contains_wlan=%u\n", index, contains_wlan ? 1U : 0U);
    printf("a90_servloc_query.domain.%u.status=parsed\n", index);
    return 0;
}

static bool parse_response(const uint8_t *packet, size_t received, unsigned int *domain_count_out, unsigned int *wlan_like_out) {
    uint8_t message_type;
    uint16_t txn_id;
    uint16_t msg_id;
    uint16_t msg_len;
    size_t end;
    size_t offset = 7;
    unsigned int tlv_count = 0;
    unsigned int result_valid = 0;
    uint16_t result = 0xffffU;
    uint16_t error = 0xffffU;
    unsigned int total_domains_valid = 0;
    unsigned int db_rev_count_valid = 0;
    unsigned int domain_list_valid = 0;
    uint16_t total_domains = 0;
    uint16_t db_rev_count = 0;
    unsigned int domain_count = 0;
    unsigned int wlan_like = 0;

    *domain_count_out = 0;
    *wlan_like_out = 0;
    if (received < 7U) {
        printf("a90_servloc_query.response_parse=short-header\n");
        printf("a90_servloc_query.response_bytes=%zu\n", received);
        return false;
    }
    message_type = packet[0];
    txn_id = read_le16_bytes(packet + 1);
    msg_id = read_le16_bytes(packet + 3);
    msg_len = read_le16_bytes(packet + 5);
    end = 7U + (size_t)msg_len;
    if (end > received) {
        end = received;
    }
    printf("a90_servloc_query.response.type=%u\n", (unsigned int)message_type);
    printf("a90_servloc_query.response.txn_id=%u\n", (unsigned int)txn_id);
    printf("a90_servloc_query.response.msg_id=%u\n", (unsigned int)msg_id);
    printf("a90_servloc_query.response.msg_len=%u\n", (unsigned int)msg_len);
    printf("a90_servloc_query.response.body_available=%zu\n", end > 7U ? end - 7U : 0U);
    while (offset + 3U <= end) {
        uint8_t tlv_type = packet[offset++];
        uint16_t tlv_len = read_le16_bytes(packet + offset);
        const uint8_t *tlv_data;
        char key[96];

        offset += sizeof(uint16_t);
        if (offset + (size_t)tlv_len > end) {
            printf("a90_servloc_query.tlv.%u.type=0x%02x\n", tlv_count, (unsigned int)tlv_type);
            printf("a90_servloc_query.tlv.%u.len=%u\n", tlv_count, (unsigned int)tlv_len);
            printf("a90_servloc_query.tlv.%u.status=truncated\n", tlv_count);
            break;
        }
        tlv_data = packet + offset;
        printf("a90_servloc_query.tlv.%u.type=0x%02x\n", tlv_count, (unsigned int)tlv_type);
        printf("a90_servloc_query.tlv.%u.len=%u\n", tlv_count, (unsigned int)tlv_len);
        printf("a90_servloc_query.tlv.%u.status=parsed\n", tlv_count);
        snprintf(key, sizeof(key), "a90_servloc_query.tlv.%u.hex", tlv_count);
        print_hex(key, tlv_data, tlv_len);
        if (tlv_type == 0x02U && tlv_len >= 4U) {
            result = read_le16_bytes(tlv_data);
            error = read_le16_bytes(tlv_data + 2);
            result_valid = 1;
        } else if (tlv_type == 0x10U && tlv_len >= 2U) {
            total_domains = read_le16_bytes(tlv_data);
            total_domains_valid = 1;
        } else if (tlv_type == 0x11U && tlv_len >= 2U) {
            db_rev_count = read_le16_bytes(tlv_data);
            db_rev_count_valid = 1;
        } else if (tlv_type == 0x12U && tlv_len >= 1U) {
            size_t domain_offset = 1;
            uint8_t wire_count = tlv_data[0];

            domain_list_valid = 1;
            domain_count = wire_count;
            printf("a90_servloc_query.domain_list.wire_count=%u\n", (unsigned int)wire_count);
            for (unsigned int i = 0; i < (unsigned int)wire_count && i < 32U; i++) {
                parse_domain_entry(i, tlv_data, tlv_len, &domain_offset, &wlan_like);
                if (domain_offset >= tlv_len) {
                    break;
                }
            }
            printf("a90_servloc_query.domain_list.bytes_consumed=%zu\n", domain_offset);
        }
        offset += tlv_len;
        tlv_count++;
    }
    *domain_count_out = domain_count;
    *wlan_like_out = wlan_like;
    printf("a90_servloc_query.response_parse=complete\n");
    printf("a90_servloc_query.tlv_count=%u\n", tlv_count);
    printf("a90_servloc_query.qmi_result_valid=%u\n", result_valid);
    printf("a90_servloc_query.qmi_result=%u\n", (unsigned int)result);
    printf("a90_servloc_query.qmi_error=%u\n", (unsigned int)error);
    printf("a90_servloc_query.total_domains_valid=%u\n", total_domains_valid);
    printf("a90_servloc_query.total_domains=%u\n", (unsigned int)total_domains);
    printf("a90_servloc_query.db_rev_count_valid=%u\n", db_rev_count_valid);
    printf("a90_servloc_query.db_rev_count=%u\n", (unsigned int)db_rev_count);
    printf("a90_servloc_query.domain_list_valid=%u\n", domain_list_valid);
    printf("a90_servloc_query.domain_count=%u\n", domain_count);
    printf("a90_servloc_query.wlan_like_domains=%u\n", wlan_like);
    printf("a90_servloc_query.success=%u\n", (message_type == 2U && msg_id == A90_SERVLOC_GET_DOMAIN_LIST_MSG_ID && txn_id == A90_SERVLOC_TXN_ID && result_valid && result == 0U) ? 1U : 0U);
    return message_type == 2U && msg_id == A90_SERVLOC_GET_DOMAIN_LIST_MSG_ID && txn_id == A90_SERVLOC_TXN_ID && result_valid && result == 0U;
}

int main(void) {
    static const uint8_t request[] = {
        0x00, 0x01, 0x00, 0x21, 0x00, 0x11, 0x00,
        0x01, 0x07, 0x00, 0x77, 0x6c, 0x61, 0x6e, 0x2f, 0x66, 0x77,
        0x10, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00,
    };
    uint32_t node = 0, port = 0;
    int fd;
    struct sockaddr_qrtr dest;
    ssize_t sent;
    long deadline;
    unsigned int packets = 0;
    bool response_seen = false;
    bool response_success = false;
    unsigned int domain_count = 0;
    unsigned int wlan_like = 0;

    printf("a90_servloc_query.version=1\n");
    printf("a90_servloc_query.service=64\n");
    printf("a90_servloc_query.instance=257\n");
    printf("a90_servloc_query.service_name=wlan/fw\n");
    printf("a90_servloc_query.wifi_hal=0\n");
    printf("a90_servloc_query.scan_connect_linkup=0\n");
    printf("a90_servloc_query.credentials=0\n");
    printf("a90_servloc_query.dhcp_routing=0\n");
    printf("a90_servloc_query.external_ping=0\n");
    print_hex("a90_servloc_query.request_hex", request, sizeof(request));

    if (!find_servloc_endpoint(&node, &port)) {
        printf("a90_servloc_query.send_attempted=0\n");
        printf("a90_servloc_query.result=no-endpoint\n");
        return 2;
    }
    fd = open_qrtr_socket();
    if (fd < 0) {
        printf("a90_servloc_query.socket.rc=-1\n");
        printf("a90_servloc_query.socket.errno=%d\n", errno);
        printf("a90_servloc_query.socket.error=%s\n", strerror(errno));
        printf("a90_servloc_query.result=socket-failed\n");
        return 2;
    }
    printf("a90_servloc_query.socket.rc=0\n");
    memset(&dest, 0, sizeof(dest));
    dest.sq_family = AF_QIPCRTR;
    dest.sq_node = node;
    dest.sq_port = port;
    sent = sendto(fd, request, sizeof(request), 0, (const struct sockaddr *)&dest, sizeof(dest));
    if (sent < 0) {
        printf("a90_servloc_query.send_attempted=1\n");
        printf("a90_servloc_query.send.rc=-1\n");
        printf("a90_servloc_query.send.errno=%d\n", errno);
        printf("a90_servloc_query.send.error=%s\n", strerror(errno));
        printf("a90_servloc_query.result=send-failed\n");
        close(fd);
        return 2;
    }
    printf("a90_servloc_query.send_attempted=1\n");
    printf("a90_servloc_query.send.rc=0\n");
    printf("a90_servloc_query.send.bytes=%zd\n", sent);
    printf("a90_servloc_query.send.node=%u\n", node);
    printf("a90_servloc_query.send.port=%u\n", port);

    deadline = monotonic_ms() + A90_SERVLOC_RESPONSE_MS;
    while (packets < 8U) {
        struct pollfd pfd = {.fd = fd, .events = POLLIN, .revents = 0};
        struct sockaddr_qrtr from;
        socklen_t from_len = sizeof(from);
        uint8_t packet[4096];
        long now = monotonic_ms();
        int poll_rc;
        ssize_t received;
        uint8_t response_type = 0;
        uint16_t response_txn = 0;
        uint16_t response_msg = 0;
        char key[96];

        if (now >= deadline) {
            break;
        }
        poll_rc = poll(&pfd, 1, (int)(deadline - now));
        if (poll_rc == 0) {
            break;
        }
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            printf("a90_servloc_query.response.rc=-1\n");
            printf("a90_servloc_query.response.errno=%d\n", errno);
            printf("a90_servloc_query.result=response-poll-failed\n");
            close(fd);
            return 2;
        }
        if ((pfd.revents & POLLIN) == 0) {
            printf("a90_servloc_query.packet.%u.revents=%d\n", packets, pfd.revents);
            if ((pfd.revents & (POLLERR | POLLHUP | POLLNVAL)) != 0) {
                break;
            }
            continue;
        }
        memset(&from, 0, sizeof(from));
        received = recvfrom(fd, packet, sizeof(packet), 0, (struct sockaddr *)&from, &from_len);
        if (received < 0) {
            if (errno == EINTR) {
                continue;
            }
            printf("a90_servloc_query.response.rc=-1\n");
            printf("a90_servloc_query.response.errno=%d\n", errno);
            printf("a90_servloc_query.result=response-recv-failed\n");
            close(fd);
            return 2;
        }
        if (received >= 7) {
            response_type = packet[0];
            response_txn = read_le16_bytes(packet + 1);
            response_msg = read_le16_bytes(packet + 3);
        }
        printf("a90_servloc_query.packet.%u.bytes=%zd\n", packets, received);
        printf("a90_servloc_query.packet.%u.from.node=%u\n", packets, from.sq_node);
        printf("a90_servloc_query.packet.%u.from.port=%u\n", packets, from.sq_port);
        printf("a90_servloc_query.packet.%u.type=%u\n", packets, (unsigned int)response_type);
        printf("a90_servloc_query.packet.%u.txn_id=%u\n", packets, (unsigned int)response_txn);
        printf("a90_servloc_query.packet.%u.msg_id=%u\n", packets, (unsigned int)response_msg);
        snprintf(key, sizeof(key), "a90_servloc_query.packet.%u.hex", packets);
        print_hex(key, packet, (size_t)received);
        if (response_type == 2U && response_txn == A90_SERVLOC_TXN_ID && response_msg == A90_SERVLOC_GET_DOMAIN_LIST_MSG_ID) {
            response_seen = true;
            response_success = parse_response(packet, (size_t)received, &domain_count, &wlan_like);
            break;
        }
        packets++;
    }
    close(fd);
    printf("a90_servloc_query.response_seen=%u\n", response_seen ? 1U : 0U);
    printf("a90_servloc_query.response_success=%u\n", response_success ? 1U : 0U);
    printf("a90_servloc_query.domain_count=%u\n", domain_count);
    printf("a90_servloc_query.wlan_like_domains=%u\n", wlan_like);
    printf("a90_servloc_query.result=%s\n", response_seen ? (response_success ? "domain-list-response-success" : "domain-list-response-error") : "no-response");
    return response_success ? 0 : 1;
}
