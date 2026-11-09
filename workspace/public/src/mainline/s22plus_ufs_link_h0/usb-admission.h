// SPDX-License-Identifier: GPL-2.0-only
/* One begin, one coverage phase, then at most one overlay/rail/probe sequence.
 * Leaf checks never retry while retaining their outer locks or references.
 */
static int cover_usb(struct device **held, u32 *word, u32 *detail, u64 run_deadline)
{
	struct g0q_usb_report report = {};
	u64 ceiling = ktime_get_boottime_ns() + 250ULL * NSEC_PER_MSEC;
	u32 attempts = 0, first_lock = 0;
	int rc;

	if (run_deadline < ceiling)
		ceiling = run_deadline;
	for (;;) {
		u64 now;
		unsigned long usec;

		rc = g0q_rpmh_remaining();
		if (rc) {
			g0q_usb_fail(&report, G0Q_USB_RUN_STATE, (u32)rc, rc);
			break;
		}
		if (ktime_get_boottime_ns() >= ceiling) {
			rc = g0q_usb_fail(&report, G0Q_USB_CEILING, 0, -ETIMEDOUT);
			break;
		}
		attempts++;
		rc = g0q_usb_cover(held, &report);
		if (!rc) {
			rc = g0q_rpmh_remaining();
			if (rc)
				g0q_usb_fail(&report, G0Q_USB_RUN_STATE, (u32)rc, rc);
			else if (ktime_get_boottime_ns() >= ceiling)
				rc = g0q_usb_fail(&report, G0Q_USB_CEILING, 0, -ETIMEDOUT);
			if (rc) {
				pm_runtime_put_noidle(*held);
				put_device(*held);
				*held = NULL;
			}
			break;
		}
		if (rc != -EBUSY || !g0q_usb_retryable(report.code))
			break;
		if (!first_lock)
			first_lock = report.code;
		/* Every unsuccessful leaf has already released all PM/device refs
		 * and USB/ICC/BCM locks. No hardware action has started.
		 */
		rc = g0q_rpmh_remaining();
		if (rc) {
			g0q_usb_fail(&report, G0Q_USB_RUN_STATE, (u32)rc, rc);
			break;
		}
		rc = -EBUSY;
		now = ktime_get_boottime_ns();
		if (attempts == 25 || now >= ceiling)
			break;
		usec = (ceiling - now) / NSEC_PER_USEC;
		if (usec > 10000)
			usec = 10000;
		if (!usec)
			break;
		usleep_range(usec / 2, usec);
	}
	*word = report.code | (first_lock << 8) | (attempts << 16);
	*detail = report.detail;
	return rc;
}
