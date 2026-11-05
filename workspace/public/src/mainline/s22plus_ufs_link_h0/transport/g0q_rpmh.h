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
int g0q_bcm_confirm_usb(void);
int g0q_icc_confirm_usb(struct icc_path *path, const struct device *dev);
int g0q_usb_cover(struct device **held);
#endif
