// SPDX-License-Identifier: GPL-2.0-only
/* Compiled only into the isolated g0q ML030 kernel and its fixed module. */
#ifndef G0Q_ML030_RPMH_H
#define G0Q_ML030_RPMH_H
#include <linux/types.h>
struct device;
struct rsc_drv;
struct rpmh_request;

int g0q_rpmh_begin(u64 deadline);
int g0q_unique_vrm(const char *name, u32 *address);
struct g0q_rpmh_report {
	u32 records, claimed, triggered, acknowledged, reclaimed;
	int error;
};
void g0q_rpmh_status(struct g0q_rpmh_report *report);
void g0q_rpmh_end(void);
int g0q_rpmh_remaining(void);
bool g0q_rpmh_deny_ordinary(void);
int g0q_rpmh_vrm(const struct device *dev, u32 address, u32 data);
int g0q_rsc_send(struct rsc_drv *drv, struct rpmh_request *request, u64 deadline,
		 bool *claimed, bool *triggered, bool *reclaimed);
struct icc_path;
/* ML034's two extra report words contain only fixed codes and scalar data. */
enum g0q_usb_reason {
	G0Q_USB_OK, G0Q_USB_HELD, G0Q_USB_RUN_STATE, G0Q_USB_NODE,
	G0Q_USB_DEVICE, G0Q_USB_LOCK, G0Q_USB_DRIVER, G0Q_USB_DATA,
	G0Q_USB_PM, G0Q_ICC_NODE, G0Q_ICC_PATH, G0Q_ICC_LENGTH,
	G0Q_ICC_LOCK, G0Q_ICC_REQUEST, G0Q_BCM_GLOBAL_LOCK,
	G0Q_BCM_VOTER, G0Q_BCM_LOCK, G0Q_BCM_PENDING,
	G0Q_BCM_UNKNOWN, G0Q_BCM_VALUES, G0Q_USB_CEILING,
};
struct g0q_usb_report { u32 code, detail; };
static inline int g0q_usb_fail(struct g0q_usb_report *r, u32 code, u32 detail, int rc)
{
	r->code = code;
	r->detail = detail;
	return rc;
}
static inline bool g0q_usb_retryable(u32 code)
{
	return code == G0Q_USB_LOCK || code == G0Q_ICC_LOCK ||
		code == G0Q_BCM_GLOBAL_LOCK || code == G0Q_BCM_LOCK;
}
int g0q_bcm_confirm_usb(struct g0q_usb_report *report);
int g0q_icc_confirm_usb(struct icc_path *path, const struct device *dev,
			struct g0q_usb_report *report);
int g0q_usb_cover(struct device **held, struct g0q_usb_report *report);
#endif
