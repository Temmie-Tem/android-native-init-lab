/* The opt-in v4 report keeps the 23-field/256-byte transport. Its explicit
 * tag prevents interpretation as v3; the certificate is set only by the
 * reviewed post-unwind module path. This header performs no device operation.
 */
#ifndef G0Q_LINK_REPORT_H
#define G0Q_LINK_REPORT_H
#define G0Q_REPORT_V4_TAG 0x40000000U
#define G0Q_REPORT_V5_TAG 0x50000000U
#define G0Q_REPORT_V6_TAG 0x60000000U
#define G0Q_REPORT_V7_TAG 0x70000000U
#define G0Q_REPORT_V8_TAG 0x80000000U
#define G0Q_REPORT_V9_TAG 0x90000000U
#define G0Q_REPORT_V10_TAG 0xa0000000U
#define G0Q_REPORT_V11_TAG 0xb0000000U
#define G0Q_PRE_EFFECT_CERT 0x00010000U
#if defined(G0Q_HCE_HANDOFF) && defined(G0Q_HCI_SNAPSHOT)
#error "HCE handoff and diagnostic-only snapshot are distinct report modes"
#endif
#if defined(G0Q_RESET_CONFIG) && (!defined(G0Q_HCE_HANDOFF) || !defined(G0Q_PRE_EFFECT_RETURN))
#error "Dedicated reset configuration requires HCE handoff and explicit return"
#endif
#if defined(G0Q_DISABLED_UCRDY) && !defined(G0Q_RESET_CONFIG)
#error "Disabled UCRDY semantics require the dedicated-reset handoff mode"
#endif
#if defined(G0Q_STALE_UCCS_ACK) && !defined(G0Q_DISABLED_UCRDY)
#error "Initial completion acknowledgement requires the V8 handoff mode"
#endif
#if defined(G0Q_CFG1_DIAGNOSTICS) && !defined(G0Q_STALE_UCCS_ACK)
#error "CFG1 diagnostics require the V9 initial acknowledgement mode"
#endif
#if defined(G0Q_CFG1_ORDERED_SELECTION) && !defined(G0Q_CFG1_DIAGNOSTICS)
#error "Ordered CFG1 selection requires the V10 diagnostic mode"
#endif
#if defined(G0Q_LINK_IRQ_DIAGNOSTICS) && !defined(G0Q_CFG1_ORDERED_SELECTION)
#error "Link IRQ diagnostics require ordered CFG1 selection"
#endif
#if defined(G0Q_UPSTREAM_LINK) && !defined(G0Q_LINK_IRQ_DIAGNOSTICS)
#error "Upstream link tolerance requires the V12 link IRQ diagnostics"
#endif
#if defined(G0Q_STORAGE_READ) && !defined(G0Q_UPSTREAM_LINK)
#error "The read-only storage stage requires the V13 upstream link"
#endif
#if defined(G0Q_STORAGE_HEADER) && !defined(G0Q_STORAGE_READ)
#error "The response-header storage report requires the V14 storage stage"
#endif
#ifdef G0Q_STORAGE_HEADER
/* V15 appends the last response's header bytes 8-11 to V14's fields. */
#define G0Q_REPORT_TAG 0xf0000000U
#define G0Q_REPORT_FIELDS 55
#define G0Q_REPORT_BYTES 512U
#elif defined(G0Q_STORAGE_READ)
/* V14 appends 16 storage fields; its envelope is 512 bytes. */
#define G0Q_REPORT_TAG 0xe0000000U
#define G0Q_REPORT_FIELDS 54
#define G0Q_REPORT_BYTES 512U
#elif defined(G0Q_UPSTREAM_LINK)
#define G0Q_REPORT_TAG 0xd0000000U
#define G0Q_REPORT_FIELDS 38
#elif defined(G0Q_LINK_IRQ_DIAGNOSTICS)
#define G0Q_REPORT_TAG 0xc0000000U
#define G0Q_REPORT_FIELDS 33
#elif defined(G0Q_CFG1_ORDERED_SELECTION)
#define G0Q_REPORT_TAG G0Q_REPORT_V11_TAG
#define G0Q_REPORT_FIELDS 33
#elif defined(G0Q_CFG1_DIAGNOSTICS)
#define G0Q_REPORT_TAG G0Q_REPORT_V10_TAG
#define G0Q_REPORT_FIELDS 33
#elif defined(G0Q_STALE_UCCS_ACK)
#define G0Q_REPORT_TAG G0Q_REPORT_V9_TAG
#define G0Q_REPORT_FIELDS 30
#elif defined(G0Q_DISABLED_UCRDY)
#define G0Q_REPORT_TAG G0Q_REPORT_V8_TAG
#define G0Q_REPORT_FIELDS 30
#elif defined(G0Q_RESET_CONFIG)
#define G0Q_REPORT_TAG G0Q_REPORT_V7_TAG
#define G0Q_REPORT_FIELDS 30
#elif defined(G0Q_HCE_HANDOFF)
#define G0Q_REPORT_TAG G0Q_REPORT_V6_TAG
#define G0Q_REPORT_FIELDS 30
#elif defined(G0Q_HCI_SNAPSHOT)
#define G0Q_REPORT_TAG G0Q_REPORT_V5_TAG
#define G0Q_REPORT_FIELDS 30
#else
#define G0Q_REPORT_TAG G0Q_REPORT_V4_TAG
#define G0Q_REPORT_FIELDS 23
#endif

#ifndef G0Q_REPORT_BYTES
#define G0Q_REPORT_BYTES 256U
#endif
/* Signed fields: operation rc, RPMh error and (V14, V15) the storage rc. */
#define G0Q_SIGNED_FIELD(i) ((i) == 0 || (i) == 16 || (G0Q_REPORT_FIELDS >= 54 && (i) == 38))

static inline int g0q_report_parse(const unsigned char *data, unsigned int size,
				 long long values[G0Q_REPORT_FIELDS])
{
	unsigned int pos = 0;
	if (!size || size > G0Q_REPORT_BYTES)
		return -1;
	for (unsigned int i = 0; i < G0Q_REPORT_FIELDS; i++) {
		unsigned long long value = 0;
		unsigned int first, negative = 0;
		if (pos < size && data[pos] == '-') {
			if (!G0Q_SIGNED_FIELD(i))
				return -1;
			negative = 1;
			pos++;
		}
		first = pos;
		while (pos < size && data[pos] >= '0' && data[pos] <= '9') {
			if (pos - first == 10 || (pos > first && data[first] == '0'))
				return -1;
			value = value * 10 + data[pos++] - '0';
		}
		if (pos == first || (negative && !value) ||
		    value > (negative ? 2147483648ULL : G0Q_SIGNED_FIELD(i) ? 2147483647ULL : 4294967295ULL) ||
		    pos >= size || data[pos++] != (i + 1 == G0Q_REPORT_FIELDS ? '\n' : ' '))
			return -1;
		values[i] = negative ? -(long long)value : (long long)value;
	}
	return pos == size ? 0 : -1;
}

static inline int g0q_pre_effect_fields(const long long values[G0Q_REPORT_FIELDS])
{
	unsigned int code = (unsigned int)values[19] & 255;
	if (values[0] >= 0 || values[0] < -4095 || code <= 2 || code > 20 ||
	    values[21] != (G0Q_REPORT_TAG | G0Q_PRE_EFFECT_CERT) || values[22])
		return 0;
	for (unsigned int i = 23; i < G0Q_REPORT_FIELDS; i++)
		if (values[i])
			return 0;
	/* Stage, reached UFS state, fixed RPMh history/error and exported USB
	 * references are all zero; the module certifies its internal unwind.
	 */
	for (unsigned int i = 1; i <= 18; i++)
		if (values[i])
			return 0;
	return 1;
}

#ifdef G0Q_HCE_HANDOFF
static inline int g0q_handoff_complete_fields(const long long values[G0Q_REPORT_FIELDS])
{
	unsigned int flags = (unsigned int)values[23] & 8191;
	unsigned int polls = ((unsigned int)values[23] >> 13) & 127;
	unsigned int elapsed = (unsigned int)values[23] >> 20;
#ifdef G0Q_DISABLED_UCRDY
	const long long observed_hcs = 8LL << 22;
#else
	const long long observed_hcs = 0;
#endif
#ifdef G0Q_STALE_UCCS_ACK
	unsigned int ack = (unsigned int)values[22] >> 28;
	const long long ack_mask = 0xf0000000LL;
	if ((ack != 0 && ack != 15) || (ack && (flags != 8191 || values[26] != 0x400)))
		return 0;
#else
	const long long ack_mask = 0;
#endif
#ifdef G0Q_CFG1_ORDERED_SELECTION
	if ((values[30] != 1 && values[30] != 3) ||
	    !!(values[32] & 1) != (values[30] == 3))
		return 0;
#elif defined(G0Q_CFG1_DIAGNOSTICS)
	if (values[30] != 3 || !(values[32] & 1))
		return 0;
#endif
#ifdef G0Q_UPSTREAM_LINK
	/* Success carries a completion sample; only UCCS/ULSS/UIC_ERROR were
	 * admitted. UEC reads exist only after UIC_ERROR, as a register prefix. */
	{
		long long seen = values[33], mask = values[34], irq = values[7];
		/* Completion result zero; post-link HCS present without HEI/DEI. */
		if (values[8] || (values[9] & 0x31) != 1 ||
		    !(irq & 0x400) || (irq & ~0x504LL) || (irq & ~seen) ||
		    !(seen & 0x400) || (seen & ~0x504LL) ||
		    (mask != 0 && mask != 1 && mask != 3 && mask != 7 && mask != 15 && mask != 31) ||
		    (!(seen & 4) && mask))
			return 0;
		if ((!(mask & 1) && values[35]) || (!(mask & 2) && values[36]) ||
		    (!(mask & 4) && (values[37] & 0x1010007LL)) ||
		    (!(mask & 8) && (values[37] & 0x20203f8LL)) ||
		    (!(mask & 16) && (values[37] & 0x4040400LL)) ||
		    (values[37] & ~0x70707ffLL))
			return 0;
	}
#endif
	if (values[1] != 6 || values[21] != G0Q_REPORT_TAG ||
	    (values[22] & ~(observed_hcs | ack_mask)) != 0x7ff ||
	    values[27] || values[28] || values[29])
		return 0;
	if (values[23] == 1)
		return !values[24] && !values[25] && !values[26];
	return flags == 8191 && polls > 0 && elapsed < 1000 && values[24] == 1 &&
		(values[25] & 8) && !(values[25] & 0x30) &&
		(values[26] == 0 || values[26] == 0x400);
}
#endif
#endif
