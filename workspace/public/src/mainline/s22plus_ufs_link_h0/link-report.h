/* The opt-in v4 report keeps the 23-field/256-byte transport. Its explicit
 * tag prevents interpretation as v3; the certificate is set only by the
 * reviewed post-unwind module path. This header performs no device operation.
 */
#ifndef G0Q_LINK_REPORT_H
#define G0Q_LINK_REPORT_H
#define G0Q_REPORT_V4_TAG 0x40000000U
#define G0Q_PRE_EFFECT_CERT 0x00010000U
#define G0Q_REPORT_FIELDS 23

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
	    values[21] != (G0Q_REPORT_V4_TAG | G0Q_PRE_EFFECT_CERT) || values[22])
		return 0;
	/* Stage, reached UFS state, fixed RPMh history/error and exported USB
	 * references are all zero; the module certifies its internal unwind.
	 */
	for (unsigned int i = 1; i <= 18; i++)
		if (values[i])
			return 0;
	return 1;
}
#endif
