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
#ifdef G0Q_STALE_UCCS_ACK
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

static inline int g0q_report_parse(const unsigned char *data, unsigned int size,
				 long long values[G0Q_REPORT_FIELDS])
{
	unsigned int pos = 0;
	if (!size || size > 256)
		return -1;
	for (unsigned int i = 0; i < G0Q_REPORT_FIELDS; i++) {
		unsigned long long value = 0;
		unsigned int first, negative = 0;
		if (pos < size && data[pos] == '-') {
			if (i != 0 && i != 16)
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
		    value > (negative ? 2147483648ULL : (i == 0 || i == 16) ? 2147483647ULL : 4294967295ULL) ||
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
