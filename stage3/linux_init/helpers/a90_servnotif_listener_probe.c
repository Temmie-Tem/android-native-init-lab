#define _GNU_SOURCE

#include <arpa/inet.h>
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
#include <time.h>
#include <unistd.h>

#ifndef AF_QIPCRTR
#define AF_QIPCRTR 42
#endif

#ifndef SOCK_CLOEXEC
#define SOCK_CLOEXEC 02000000
#endif

#define HELPER_VERSION "a90_servnotif_listener_probe v1"
#define SERVNOTIF_SERVICE 66U
#define SERVNOTIF_INSTANCE_ENCODED 46081U
#define REGISTER_LISTENER_MSG_ID 0x0020U
#define STATE_UPDATED_IND_MSG_ID 0x0022U
#define ACK_MSG_ID 0x0023U
#define REGISTER_TXN_ID 1U
#define ACK_TXN_ID 2U
#define WLAN_PD_SERVICE_NAME "msm/modem/wlan_pd"

struct endpoint {
    bool found;
    unsigned int node;
    unsigned int port;
    unsigned int events;
    unsigned int timeout;
};

struct probe_result {
    bool response_seen;
    bool response_success;
    bool response_state_valid;
    uint32_t response_state;
    bool indication_seen;
    bool indication_valid;
    uint16_t indication_txn;
    uint32_t indication_state;
    bool ack_sent;
    bool ack_success;
    unsigned int packets;
};

static long monotonic_ms(void) {
    struct timespec timestamp;

    if (clock_gettime(CLOCK_MONOTONIC, &timestamp) != 0) {
        return 0;
    }
    return timestamp.tv_sec * 1000L + timestamp.tv_nsec / 1000000L;
}

static uint16_t read_le16_bytes(const uint8_t *data) {
    return (uint16_t)data[0] | ((uint16_t)data[1] << 8);
}

static uint32_t read_le32_bytes(const uint8_t *data) {
    return (uint32_t)data[0] |
           ((uint32_t)data[1] << 8) |
           ((uint32_t)data[2] << 16) |
           ((uint32_t)data[3] << 24);
}

static const char *state_name(uint32_t state) {
    switch (state) {
    case 0:
        return "unknown";
    case 1:
        return "down";
    case 2:
        return "up";
    case 0x2fffffffu:
        return "early-down";
    case 0x7fffffffu:
        return "uninit";
    default:
        return "other";
    }
}

static const char *qrtr_cmd_name(uint32_t command) {
    switch (command) {
    case QRTR_TYPE_DATA:
        return "data";
    case QRTR_TYPE_NEW_SERVER:
        return "new-server";
    case QRTR_TYPE_DEL_SERVER:
        return "del-server";
    case QRTR_TYPE_NEW_LOOKUP:
        return "new-lookup";
    case QRTR_TYPE_DEL_LOOKUP:
        return "del-lookup";
    default:
        return "other";
    }
}

static void print_hex(const char *key, const uint8_t *data, size_t length) {
    printf("%s=", key);
    for (size_t offset = 0; offset < length; offset++) {
        printf("%02x", data[offset]);
    }
    printf("\n");
}

static int open_qrtr_socket(void) {
    int fd = socket(AF_QIPCRTR, SOCK_DGRAM | SOCK_CLOEXEC, 0);

    if (fd >= 0) {
        return fd;
    }
    if (errno != EINVAL) {
        return -1;
    }
    fd = socket(AF_QIPCRTR, SOCK_DGRAM, 0);
    if (fd >= 0) {
        int flags = fcntl(fd, F_GETFD);

        if (flags >= 0) {
            (void)fcntl(fd, F_SETFD, flags | FD_CLOEXEC);
        }
    }
    return fd;
}

static int send_lookup(int fd, uint32_t command, uint32_t service, uint32_t instance, const char *prefix) {
    struct qrtr_ctrl_pkt packet;
    struct sockaddr_qrtr destination;
    ssize_t sent_bytes;

    memset(&packet, 0, sizeof(packet));
    packet.cmd = htole32(command);
    packet.server.service = htole32(service);
    packet.server.instance = htole32(instance);
    packet.server.node = 0;
    packet.server.port = 0;

    memset(&destination, 0, sizeof(destination));
    destination.sq_family = AF_QIPCRTR;
    destination.sq_node = QRTR_NODE_BCAST;
    destination.sq_port = QRTR_PORT_CTRL;

    sent_bytes = sendto(fd, &packet, sizeof(packet), 0, (const struct sockaddr *)&destination, sizeof(destination));
    if (sent_bytes < 0) {
        printf("%s.rc=-1\n", prefix);
        printf("%s.errno=%d\n", prefix, errno);
        printf("%s.error=%s\n", prefix, strerror(errno));
        return -1;
    }
    printf("%s.rc=0\n", prefix);
    printf("%s.bytes=%zd\n", prefix, sent_bytes);
    printf("%s.cmd=%u\n", prefix, command);
    printf("%s.service=%u\n", prefix, service);
    printf("%s.instance=%u\n", prefix, instance);
    return 0;
}

static int find_endpoint(struct endpoint *endpoint, unsigned int readback_ms) {
    int fd = open_qrtr_socket();
    long deadline = monotonic_ms() + (long)readback_ms;

    memset(endpoint, 0, sizeof(*endpoint));
    printf("servnotif.endpoint.socket.rc=%d\n", fd >= 0 ? 0 : -1);
    printf("servnotif.endpoint.af=%d\n", AF_QIPCRTR);
    if (fd < 0) {
        printf("servnotif.endpoint.socket.errno=%d\n", errno);
        printf("servnotif.endpoint.socket.error=%s\n", strerror(errno));
        return -1;
    }
    if (send_lookup(fd, QRTR_TYPE_NEW_LOOKUP, SERVNOTIF_SERVICE, SERVNOTIF_INSTANCE_ENCODED, "servnotif.endpoint.lookup_send") != 0) {
        close(fd);
        return -1;
    }
    while (endpoint->events < 8U) {
        struct pollfd poll_item;
        struct qrtr_ctrl_pkt packet;
        struct sockaddr_qrtr from;
        socklen_t from_len = sizeof(from);
        long now = monotonic_ms();
        int poll_rc;
        ssize_t received;
        uint32_t command = 0;
        uint32_t service = 0;
        uint32_t instance = 0;
        uint32_t node = 0;
        uint32_t port = 0;
        bool empty_event;

        if (now >= deadline) {
            endpoint->timeout = 1;
            break;
        }
        poll_item.fd = fd;
        poll_item.events = POLLIN;
        poll_item.revents = 0;
        poll_rc = poll(&poll_item, 1, (int)(deadline - now));
        if (poll_rc == 0) {
            endpoint->timeout = 1;
            break;
        }
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            printf("servnotif.endpoint.readback.rc=-1\n");
            printf("servnotif.endpoint.readback.errno=%d\n", errno);
            printf("servnotif.endpoint.readback.error=%s\n", strerror(errno));
            close(fd);
            return -1;
        }
        memset(&packet, 0, sizeof(packet));
        memset(&from, 0, sizeof(from));
        received = recvfrom(fd, &packet, sizeof(packet), 0, (struct sockaddr *)&from, &from_len);
        if (received < 0) {
            if (errno == EINTR) {
                continue;
            }
            printf("servnotif.endpoint.readback.rc=-1\n");
            printf("servnotif.endpoint.readback.errno=%d\n", errno);
            printf("servnotif.endpoint.readback.error=%s\n", strerror(errno));
            close(fd);
            return -1;
        }
        if (received >= (ssize_t)sizeof(uint32_t)) {
            command = le32toh(packet.cmd);
        }
        if (received >= (ssize_t)sizeof(packet)) {
            service = le32toh(packet.server.service);
            instance = le32toh(packet.server.instance);
            node = le32toh(packet.server.node);
            port = le32toh(packet.server.port);
        }
        empty_event = command == QRTR_TYPE_NEW_SERVER && service == 0 && instance == 0 && node == 0 && port == 0;
        printf("servnotif.endpoint.event.%u.bytes=%zd\n", endpoint->events, received);
        printf("servnotif.endpoint.event.%u.from.node=%u\n", endpoint->events, from.sq_node);
        printf("servnotif.endpoint.event.%u.from.port=%u\n", endpoint->events, from.sq_port);
        printf("servnotif.endpoint.event.%u.cmd=%u\n", endpoint->events, command);
        printf("servnotif.endpoint.event.%u.type=%s\n", endpoint->events, qrtr_cmd_name(command));
        printf("servnotif.endpoint.event.%u.service=%u\n", endpoint->events, service);
        printf("servnotif.endpoint.event.%u.instance=%u\n", endpoint->events, instance);
        printf("servnotif.endpoint.event.%u.node=%u\n", endpoint->events, node);
        printf("servnotif.endpoint.event.%u.port=%u\n", endpoint->events, port);
        printf("servnotif.endpoint.event.%u.empty=%u\n", endpoint->events, empty_event ? 1U : 0U);
        endpoint->events++;
        if (command == QRTR_TYPE_NEW_SERVER &&
            service == SERVNOTIF_SERVICE &&
            instance == SERVNOTIF_INSTANCE_ENCODED &&
            port != 0) {
            endpoint->found = true;
            endpoint->node = node;
            endpoint->port = port;
            break;
        }
        if (empty_event) {
            break;
        }
    }
    (void)send_lookup(fd, QRTR_TYPE_DEL_LOOKUP, SERVNOTIF_SERVICE, SERVNOTIF_INSTANCE_ENCODED, "servnotif.endpoint.del_lookup_send");
    close(fd);
    printf("servnotif.endpoint.readback.events=%u\n", endpoint->events);
    printf("servnotif.endpoint.readback.timeout=%u\n", endpoint->timeout);
    printf("servnotif.endpoint.found=%u\n", endpoint->found ? 1U : 0U);
    printf("servnotif.endpoint.node=%u\n", endpoint->node);
    printf("servnotif.endpoint.port=%u\n", endpoint->port);
    printf("servnotif.endpoint.status=%s\n", endpoint->found ? "found" : "not-found");
    return 0;
}

static void build_register_request(uint8_t *request, size_t *request_len, uint16_t txn_id, uint8_t enable) {
    const char service_name[] = WLAN_PD_SERVICE_NAME;
    size_t name_len = sizeof(service_name) - 1U;
    size_t payload_len = 4U + 3U + name_len;
    size_t offset = 0;

    request[offset++] = 0x00;
    request[offset++] = (uint8_t)(txn_id & 0xffU);
    request[offset++] = (uint8_t)((txn_id >> 8) & 0xffU);
    request[offset++] = (uint8_t)(REGISTER_LISTENER_MSG_ID & 0xffU);
    request[offset++] = (uint8_t)((REGISTER_LISTENER_MSG_ID >> 8) & 0xffU);
    request[offset++] = (uint8_t)(payload_len & 0xffU);
    request[offset++] = (uint8_t)((payload_len >> 8) & 0xffU);
    request[offset++] = 0x01;
    request[offset++] = 0x01;
    request[offset++] = 0x00;
    request[offset++] = enable;
    request[offset++] = 0x02;
    request[offset++] = (uint8_t)(name_len & 0xffU);
    request[offset++] = (uint8_t)((name_len >> 8) & 0xffU);
    memcpy(request + offset, service_name, name_len);
    offset += name_len;
    *request_len = offset;
}

static void build_ack_request(uint8_t *request, size_t *request_len, uint16_t txn_id, uint16_t indication_txn) {
    const char service_name[] = WLAN_PD_SERVICE_NAME;
    size_t name_len = sizeof(service_name) - 1U;
    size_t payload_len = 3U + name_len + 5U;
    size_t offset = 0;

    request[offset++] = 0x00;
    request[offset++] = (uint8_t)(txn_id & 0xffU);
    request[offset++] = (uint8_t)((txn_id >> 8) & 0xffU);
    request[offset++] = (uint8_t)(ACK_MSG_ID & 0xffU);
    request[offset++] = (uint8_t)((ACK_MSG_ID >> 8) & 0xffU);
    request[offset++] = (uint8_t)(payload_len & 0xffU);
    request[offset++] = (uint8_t)((payload_len >> 8) & 0xffU);
    request[offset++] = 0x01;
    request[offset++] = (uint8_t)(name_len & 0xffU);
    request[offset++] = (uint8_t)((name_len >> 8) & 0xffU);
    memcpy(request + offset, service_name, name_len);
    offset += name_len;
    request[offset++] = 0x02;
    request[offset++] = 0x02;
    request[offset++] = 0x00;
    request[offset++] = (uint8_t)(indication_txn & 0xffU);
    request[offset++] = (uint8_t)((indication_txn >> 8) & 0xffU);
    *request_len = offset;
}

static void parse_register_response(const uint8_t *packet, size_t received, struct probe_result *result) {
    uint8_t message_type;
    uint16_t txn_id;
    uint16_t msg_id;
    uint16_t msg_len;
    size_t end;
    size_t offset = 7;
    unsigned int result_valid = 0;
    uint16_t qmi_result = 0xffffU;
    uint16_t qmi_error = 0xffffU;
    bool state_valid = false;
    uint32_t state = 0;

    if (received < 7U) {
        printf("servnotif.register_response_parse=short-header\n");
        return;
    }
    message_type = packet[0];
    txn_id = read_le16_bytes(packet + 1);
    msg_id = read_le16_bytes(packet + 3);
    msg_len = read_le16_bytes(packet + 5);
    end = 7U + (size_t)msg_len;
    if (end > received) {
        end = received;
    }
    printf("servnotif.register_response.type=%u\n", (unsigned int)message_type);
    printf("servnotif.register_response.txn_id=%u\n", (unsigned int)txn_id);
    printf("servnotif.register_response.msg_id=%u\n", (unsigned int)msg_id);
    printf("servnotif.register_response.msg_len=%u\n", (unsigned int)msg_len);
    while (offset + 3U <= end) {
        uint8_t tlv_type = packet[offset++];
        uint16_t tlv_len = read_le16_bytes(packet + offset);
        const uint8_t *tlv_data;

        offset += sizeof(uint16_t);
        if (offset + (size_t)tlv_len > end) {
            printf("servnotif.register_response_parse=truncated\n");
            return;
        }
        tlv_data = packet + offset;
        if (tlv_type == 0x02U && tlv_len >= 4U) {
            qmi_result = read_le16_bytes(tlv_data);
            qmi_error = read_le16_bytes(tlv_data + 2);
            result_valid = 1;
        } else if (tlv_type == 0x10U && tlv_len >= 4U) {
            state = read_le32_bytes(tlv_data);
            state_valid = true;
        }
        offset += tlv_len;
    }
    result->response_seen = true;
    result->response_success = message_type == 2U &&
                               msg_id == REGISTER_LISTENER_MSG_ID &&
                               txn_id == REGISTER_TXN_ID &&
                               result_valid &&
                               qmi_result == 0U;
    result->response_state_valid = state_valid;
    result->response_state = state;
    printf("servnotif.register_response_parse=complete\n");
    printf("servnotif.register_response.qmi_result_valid=%u\n", result_valid);
    printf("servnotif.register_response.qmi_result=%u\n", (unsigned int)qmi_result);
    printf("servnotif.register_response.qmi_error=%u\n", (unsigned int)qmi_error);
    printf("servnotif.register_response.curr_state_valid=%u\n", state_valid ? 1U : 0U);
    printf("servnotif.register_response.curr_state=0x%08x\n", state);
    printf("servnotif.register_response.curr_state_name=%s\n", state_name(state));
    printf("servnotif.register_response.success=%u\n", result->response_success ? 1U : 0U);
}

static void parse_indication(const uint8_t *packet, size_t received, struct probe_result *result) {
    uint8_t message_type;
    uint16_t msg_id;
    uint16_t msg_len;
    size_t end;
    size_t offset = 7;
    bool state_valid = false;
    bool service_name_valid = false;
    bool txn_valid = false;
    uint32_t state = 0;
    uint16_t indication_txn = 0;

    if (received < 7U) {
        printf("servnotif.indication_parse=short-header\n");
        return;
    }
    message_type = packet[0];
    msg_id = read_le16_bytes(packet + 3);
    msg_len = read_le16_bytes(packet + 5);
    end = 7U + (size_t)msg_len;
    if (end > received) {
        end = received;
    }
    while (offset + 3U <= end) {
        uint8_t tlv_type = packet[offset++];
        uint16_t tlv_len = read_le16_bytes(packet + offset);
        const uint8_t *tlv_data;

        offset += sizeof(uint16_t);
        if (offset + (size_t)tlv_len > end) {
            printf("servnotif.indication_parse=truncated\n");
            return;
        }
        tlv_data = packet + offset;
        if (tlv_type == 0x01U && tlv_len >= 4U) {
            state = read_le32_bytes(tlv_data);
            state_valid = true;
        } else if (tlv_type == 0x02U) {
            service_name_valid = true;
        } else if (tlv_type == 0x03U && tlv_len >= 2U) {
            indication_txn = read_le16_bytes(tlv_data);
            txn_valid = true;
        }
        offset += tlv_len;
    }
    result->indication_seen = true;
    result->indication_valid = message_type == 4U &&
                               msg_id == STATE_UPDATED_IND_MSG_ID &&
                               state_valid &&
                               service_name_valid &&
                               txn_valid;
    result->indication_txn = indication_txn;
    result->indication_state = state;
    printf("servnotif.indication_parse=complete\n");
    printf("servnotif.indication.valid=%u\n", result->indication_valid ? 1U : 0U);
    printf("servnotif.indication.curr_state_valid=%u\n", state_valid ? 1U : 0U);
    printf("servnotif.indication.curr_state=0x%08x\n", state);
    printf("servnotif.indication.curr_state_name=%s\n", state_name(state));
    printf("servnotif.indication.transaction_id_valid=%u\n", txn_valid ? 1U : 0U);
    printf("servnotif.indication.transaction_id=%u\n", (unsigned int)indication_txn);
}

static void parse_ack_response(const uint8_t *packet, size_t received, struct probe_result *result) {
    uint8_t message_type;
    uint16_t txn_id;
    uint16_t msg_id;
    uint16_t msg_len;
    size_t end;
    size_t offset = 7;
    unsigned int result_valid = 0;
    uint16_t qmi_result = 0xffffU;
    uint16_t qmi_error = 0xffffU;

    if (received < 7U) {
        printf("servnotif.ack_response_parse=short-header\n");
        return;
    }
    message_type = packet[0];
    txn_id = read_le16_bytes(packet + 1);
    msg_id = read_le16_bytes(packet + 3);
    msg_len = read_le16_bytes(packet + 5);
    end = 7U + (size_t)msg_len;
    if (end > received) {
        end = received;
    }
    while (offset + 3U <= end) {
        uint8_t tlv_type = packet[offset++];
        uint16_t tlv_len = read_le16_bytes(packet + offset);
        const uint8_t *tlv_data;

        offset += sizeof(uint16_t);
        if (offset + (size_t)tlv_len > end) {
            break;
        }
        tlv_data = packet + offset;
        if (tlv_type == 0x02U && tlv_len >= 4U) {
            qmi_result = read_le16_bytes(tlv_data);
            qmi_error = read_le16_bytes(tlv_data + 2);
            result_valid = 1;
        }
        offset += tlv_len;
    }
    result->ack_success = message_type == 2U &&
                          msg_id == ACK_MSG_ID &&
                          txn_id == ACK_TXN_ID &&
                          result_valid &&
                          qmi_result == 0U;
    printf("servnotif.ack_response.qmi_result_valid=%u\n", result_valid);
    printf("servnotif.ack_response.qmi_result=%u\n", (unsigned int)qmi_result);
    printf("servnotif.ack_response.qmi_error=%u\n", (unsigned int)qmi_error);
    printf("servnotif.ack_response.success=%u\n", result->ack_success ? 1U : 0U);
}

static int run_probe(unsigned int readback_ms, unsigned int response_ms) {
    struct endpoint endpoint;
    uint8_t register_request[96];
    size_t register_request_len = 0;
    int fd;
    struct sockaddr_qrtr destination;
    ssize_t sent_bytes;
    long deadline;
    struct probe_result result;

    memset(&result, 0, sizeof(result));
    build_register_request(register_request, &register_request_len, REGISTER_TXN_ID, 1U);
    printf("servnotif.probe.begin=1\n");
    printf("servnotif.probe.version=%s\n", HELPER_VERSION);
    printf("servnotif.probe.service=%u\n", SERVNOTIF_SERVICE);
    printf("servnotif.probe.instance=%u\n", SERVNOTIF_INSTANCE_ENCODED);
    printf("servnotif.probe.service_name=%s\n", WLAN_PD_SERVICE_NAME);
    printf("servnotif.probe.qmi_payload=1\n");
    printf("servnotif.probe.wifi_hal=0\n");
    printf("servnotif.probe.scan_connect_linkup=0\n");
    printf("servnotif.probe.credentials=0\n");
    printf("servnotif.probe.dhcp_routing=0\n");
    printf("servnotif.probe.external_ping=0\n");
    print_hex("servnotif.register_request_hex", register_request, register_request_len);
    if (find_endpoint(&endpoint, readback_ms) != 0 || !endpoint.found) {
        printf("servnotif.probe.result=no-endpoint\n");
        printf("servnotif.probe.end=1\n");
        return 2;
    }
    fd = open_qrtr_socket();
    if (fd < 0) {
        printf("servnotif.socket.rc=-1\n");
        printf("servnotif.socket.errno=%d\n", errno);
        printf("servnotif.socket.error=%s\n", strerror(errno));
        printf("servnotif.probe.result=socket-failed\n");
        printf("servnotif.probe.end=1\n");
        return 2;
    }
    memset(&destination, 0, sizeof(destination));
    destination.sq_family = AF_QIPCRTR;
    destination.sq_node = endpoint.node;
    destination.sq_port = endpoint.port;
    sent_bytes = sendto(fd, register_request, register_request_len, 0, (const struct sockaddr *)&destination, sizeof(destination));
    if (sent_bytes < 0) {
        printf("servnotif.register_send.rc=-1\n");
        printf("servnotif.register_send.errno=%d\n", errno);
        printf("servnotif.register_send.error=%s\n", strerror(errno));
        close(fd);
        printf("servnotif.probe.result=send-failed\n");
        printf("servnotif.probe.end=1\n");
        return 2;
    }
    printf("servnotif.register_send.rc=0\n");
    printf("servnotif.register_send.bytes=%zd\n", sent_bytes);
    printf("servnotif.register_send.node=%u\n", endpoint.node);
    printf("servnotif.register_send.port=%u\n", endpoint.port);
    deadline = monotonic_ms() + (long)response_ms;
    while (result.packets < 12U) {
        struct pollfd poll_item;
        struct sockaddr_qrtr from;
        socklen_t from_len = sizeof(from);
        uint8_t packet[4096];
        long now = monotonic_ms();
        int poll_rc;
        ssize_t received;
        uint8_t packet_type = 0;
        uint16_t packet_txn = 0;
        uint16_t packet_msg = 0;
        char packet_hex_key[96];

        if (now >= deadline) {
            break;
        }
        poll_item.fd = fd;
        poll_item.events = POLLIN;
        poll_item.revents = 0;
        poll_rc = poll(&poll_item, 1, (int)(deadline - now));
        if (poll_rc == 0) {
            break;
        }
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            printf("servnotif.recv.errno=%d\n", errno);
            printf("servnotif.recv.error=%s\n", strerror(errno));
            close(fd);
            printf("servnotif.probe.result=response-poll-failed\n");
            printf("servnotif.probe.end=1\n");
            return 2;
        }
        memset(&from, 0, sizeof(from));
        received = recvfrom(fd, packet, sizeof(packet), 0, (struct sockaddr *)&from, &from_len);
        if (received < 0) {
            if (errno == EINTR) {
                continue;
            }
            printf("servnotif.recv.errno=%d\n", errno);
            printf("servnotif.recv.error=%s\n", strerror(errno));
            close(fd);
            printf("servnotif.probe.result=response-recv-failed\n");
            printf("servnotif.probe.end=1\n");
            return 2;
        }
        if (received >= 7) {
            packet_type = packet[0];
            packet_txn = read_le16_bytes(packet + 1);
            packet_msg = read_le16_bytes(packet + 3);
        }
        printf("servnotif.packet.%u.bytes=%zd\n", result.packets, received);
        printf("servnotif.packet.%u.from.node=%u\n", result.packets, from.sq_node);
        printf("servnotif.packet.%u.from.port=%u\n", result.packets, from.sq_port);
        printf("servnotif.packet.%u.type=%u\n", result.packets, (unsigned int)packet_type);
        printf("servnotif.packet.%u.txn_id=%u\n", result.packets, (unsigned int)packet_txn);
        printf("servnotif.packet.%u.msg_id=%u\n", result.packets, (unsigned int)packet_msg);
        snprintf(packet_hex_key, sizeof(packet_hex_key), "servnotif.packet.%u.hex", result.packets);
        print_hex(packet_hex_key, packet, (size_t)received);
        if (packet_type == 2U && packet_txn == REGISTER_TXN_ID && packet_msg == REGISTER_LISTENER_MSG_ID) {
            parse_register_response(packet, (size_t)received, &result);
        } else if (packet_type == 4U && packet_msg == STATE_UPDATED_IND_MSG_ID) {
            uint8_t ack_request[96];
            size_t ack_request_len = 0;
            ssize_t ack_sent_bytes;

            parse_indication(packet, (size_t)received, &result);
            if (result.indication_valid) {
                build_ack_request(ack_request, &ack_request_len, ACK_TXN_ID, result.indication_txn);
                print_hex("servnotif.ack_request_hex", ack_request, ack_request_len);
                ack_sent_bytes = sendto(fd, ack_request, ack_request_len, 0, (const struct sockaddr *)&destination, sizeof(destination));
                result.ack_sent = ack_sent_bytes == (ssize_t)ack_request_len;
                printf("servnotif.ack_send.rc=%d\n", result.ack_sent ? 0 : -1);
                printf("servnotif.ack_send.bytes=%zd\n", ack_sent_bytes);
            }
        } else if (packet_type == 2U && packet_txn == ACK_TXN_ID && packet_msg == ACK_MSG_ID) {
            parse_ack_response(packet, (size_t)received, &result);
        }
        result.packets++;
        if (result.indication_seen && (!result.indication_valid || result.ack_success)) {
            break;
        }
    }
    close(fd);
    printf("servnotif.response_seen=%u\n", result.response_seen ? 1U : 0U);
    printf("servnotif.response_success=%u\n", result.response_success ? 1U : 0U);
    printf("servnotif.response_curr_state_valid=%u\n", result.response_state_valid ? 1U : 0U);
    printf("servnotif.response_curr_state=0x%08x\n", result.response_state);
    printf("servnotif.response_curr_state_name=%s\n", state_name(result.response_state));
    printf("servnotif.indication_seen=%u\n", result.indication_seen ? 1U : 0U);
    printf("servnotif.indication_valid=%u\n", result.indication_valid ? 1U : 0U);
    printf("servnotif.indication_curr_state=0x%08x\n", result.indication_state);
    printf("servnotif.indication_curr_state_name=%s\n", state_name(result.indication_state));
    printf("servnotif.ack_sent=%u\n", result.ack_sent ? 1U : 0U);
    printf("servnotif.ack_success=%u\n", result.ack_success ? 1U : 0U);
    printf("servnotif.packets=%u\n", result.packets);
    printf("servnotif.probe.result=%s\n", result.response_seen ? (result.response_success ? "listener-response-success" : "listener-response-error") : "no-response");
    printf("servnotif.probe.end=1\n");
    return result.response_seen ? 0 : 3;
}

static void usage(FILE *stream) {
    fprintf(stream,
            "usage: a90_servnotif_listener_probe --allow-service-notifier-listener-probe "
            "[--readback-ms N] [--response-ms N]\n");
}

int main(int argc, char **argv) {
    bool allow_probe = false;
    unsigned int readback_ms = 10000;
    unsigned int response_ms = 15000;

    for (int arg_index = 1; arg_index < argc; arg_index++) {
        if (strcmp(argv[arg_index], "--allow-service-notifier-listener-probe") == 0) {
            allow_probe = true;
        } else if (strcmp(argv[arg_index], "--readback-ms") == 0 && arg_index + 1 < argc) {
            readback_ms = (unsigned int)strtoul(argv[++arg_index], NULL, 10);
        } else if (strcmp(argv[arg_index], "--response-ms") == 0 && arg_index + 1 < argc) {
            response_ms = (unsigned int)strtoul(argv[++arg_index], NULL, 10);
        } else if (strcmp(argv[arg_index], "--version") == 0) {
            printf("%s\n", HELPER_VERSION);
            return 0;
        } else if (strcmp(argv[arg_index], "--help") == 0) {
            usage(stdout);
            return 0;
        } else {
            usage(stderr);
            return 2;
        }
    }
    printf("servnotif.probe.allow=%u\n", allow_probe ? 1U : 0U);
    if (!allow_probe) {
        printf("servnotif.probe.result=blocked\n");
        printf("servnotif.probe.reason=missing-allow-service-notifier-listener-probe\n");
        return 2;
    }
    if (readback_ms < 1000 || readback_ms > 60000 || response_ms < 1000 || response_ms > 60000) {
        printf("servnotif.probe.result=invalid-timeout\n");
        return 2;
    }
    return run_probe(readback_ms, response_ms);
}
