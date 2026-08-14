/*
 * P3.18 runtime replacement for the P3.17 terminal publisher.
 *
 * This source is materialized in place of the P3.17 p317_publish() function,
 * after the P3.18 latch parser, bounded banner writer, and envelope-v4
 * encoder definitions.  The exposure gate is armed and read back before the
 * sole UDC bind.  A terminal banner attempt is bounded before the Carrier is
 * committed, so its exact result is retained in that same terminal envelope.
 */

#define P318_LATCH_GATE_PATH \
	"/sys/module/s22plus_dwc3_event_latch/parameters/expose_gate"
#define P318_LATCH_SNAPSHOT_PATH \
	"/sys/module/s22plus_dwc3_event_latch/parameters/snapshot"
#define P318_LATCH_VALUE_CAPACITY 256U

static struct s22plus_max77705_p318_latch_snapshot p318_gate_baseline;
static int p318_gate_baseline_ready;

static long p318_read_latch_snapshot(
		struct s22plus_max77705_p318_latch_snapshot *snapshot)
{
	char value[P318_LATCH_VALUE_CAPACITY];
	size_t length = 0U;
	long rc;

	if (snapshot == NULL)
		return -P260_EPROTO;
	rc = p282_read_file(
		P318_LATCH_SNAPSHOT_PATH, value, sizeof(value), &length);
	if (rc != 0)
		return rc;
	return s22plus_p318_parse_latch_snapshot(value, length, snapshot) == 0
		? 0 : -P260_EPROTO;
}

static long p318_read_exposure_gate(void)
{
	char value[4];
	size_t length = 0U;
	long rc = p282_read_file(
		P318_LATCH_GATE_PATH, value, sizeof(value), &length);

	if (rc != 0)
		return rc;
	return s22plus_p318_exposure_gate_readback_valid(value, length) != 0
		? 0 : -P260_EPROTO;
}

static long p318_arm_exposure_gate(void)
{
	struct s22plus_max77705_p318_latch_snapshot before = {0};
	struct s22plus_max77705_p318_latch_snapshot after = {0};
	long rc = p318_read_latch_snapshot(&before);

	if (rc != 0)
		return rc;
	if (before.install_valid != 1U || before.gate_valid != 0U ||
	    before.event_valid != 0U)
		return -P260_EPROTO;
	rc = p282_write_control(P318_LATCH_GATE_PATH, "1\n");
	if (rc != 0)
		return rc;
	rc = p318_read_exposure_gate();
	if (rc != 0)
		return rc;
	rc = p318_read_latch_snapshot(&after);
	if (rc != 0)
		return rc;
	if (after.install_valid != 1U || after.gate_valid != 1U ||
	    after.event_valid != 0U || after.install_ns != before.install_ns ||
	    after.gate_ns < after.install_ns ||
	    after.pre_gate_events < before.pre_gate_events)
		return -P260_EPROTO;
	p318_gate_baseline = after;
	p318_gate_baseline_ready = 1;
	return 0;
}

static long p318_capture_terminal_latch(
	struct s22plus_max77705_p318_latch_snapshot *snapshot)
{
	long rc;

	if (p318_gate_baseline_ready == 0)
		return -P260_EPROTO;
	rc = p318_read_exposure_gate();

	if (rc != 0)
		return rc;
	rc = p318_read_latch_snapshot(snapshot);
	if (rc != 0)
		return rc;
	return snapshot->install_valid == 1U &&
		snapshot->gate_valid == 1U &&
		snapshot->install_ns == p318_gate_baseline.install_ns &&
		snapshot->gate_ns == p318_gate_baseline.gate_ns &&
		snapshot->pre_gate_events ==
			p318_gate_baseline.pre_gate_events
		? 0 : -P260_EPROTO;
}

#ifndef S22PLUS_P318_RUNTIME_HELPER_ONLY
static struct s22plus_p318_banner_result p318_terminal_banner(int tty_fd)
{
	struct s22plus_p318_banner_result result = {
		.outcome = S22PLUS_P318_BANNER_NOT_ATTEMPTED,
		.error_class = S22PLUS_P318_BANNER_ERROR_NONE,
		.bytes_written = 0U,
	};

	if (tty_fd >= 0)
		result = s22plus_p318_banner_attempt(tty_fd);
	return result;
}

static __attribute__((noreturn)) void p317_publish(
	int tty_fd, const struct p316_diag_observation *input)
{
	struct p316_diag_observation observation;
	struct s22plus_max77705_p318_latch_snapshot latch = {0};
	const struct s22plus_max77705_p318_latch_snapshot *latch_pointer = NULL;
	struct s22plus_p318_banner_result banner;
	uint8_t envelope[S22PLUS_MAX77705_ENVELOPE_SIZE];
	uint16_t detail = 0U;
	long latch_rc = 0;
	int rc;

	if (input == NULL)
		p290_fail_next(P313_DETAIL_TERMINAL_DOMAIN_CONTRADICTION);
	observation = *input;
	banner = p318_terminal_banner(tty_fd);
	if (observation.result_valid != 0U) {
		latch_rc = p318_capture_terminal_latch(&latch);
		if (latch_rc == 0) {
			latch_pointer = &latch;
		} else {
			observation.semantic_kind =
				S22PLUS_MAX77705_SEMANTIC_TERMINAL;
			observation.semantic_code =
				S22PLUS_MAX77705_TERMINAL_SYNC_CONTRADICTION;
			observation.result_valid = 0U;
			observation.observer_site =
				S22PLUS_MAX77705_P318_OBSERVER_SITE_TIMING_LATCH;
			observation.observer_error_class =
				p316_observer_error_class(latch_rc);
		}
	}
	rc = s22plus_max77705_p318_encode_envelope(
		&observation.binding, &g_p317_exec,
		observation.semantic_kind, observation.semantic_code,
		observation.observer_site, observation.observer_error_class,
		observation.result_valid ? &observation.result : NULL,
		observation.result_valid ? &observation.summary : NULL,
		latch_pointer, &banner, envelope, &detail);
	if (rc != 0)
		p290_fail_next(P313_DETAIL_TERMINAL_DOMAIN_CONTRADICTION);
	p316_bypass_to_pair();
	long publish_rc = s22_max77705_checkpoint_payload_progress_position(
		&g_checkpoint, 105U, S22PLUS_MAX77705_A_DETAIL, envelope);
	if (publish_rc == 0)
		publish_rc = s22_max77705_checkpoint_payload_terminal_position(
			&g_checkpoint, 106U, detail, envelope + 64U);
	if (publish_rc != 0)
		p292_park_after_checkpoint_error(publish_rc);
	p290_park_after_confirmed_publication();
}
#endif
