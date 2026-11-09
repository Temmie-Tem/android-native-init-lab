// SPDX-License-Identifier: GPL-2.0-only
/* The two selected endpoints have identical fabric masks. Only look at the
 * USB consumer that owns the already active and PM-held controller. No UFS
 * request is created and no BCM/cache value is published by this check.
 */
#include <soc/qcom/g0q-ml030.h>
int g0q_icc_confirm_usb(struct icc_path *path, const struct device *dev,
			struct g0q_usb_report *report)
{
	static const char *const nodes[] = {
		"chm_apps", "qns_gem_noc_cnoc", "qnm_gemnoc_cnoc", "qhs_usb3_0"
	};
	struct device_node *gem __free(device_node) =
		of_find_node_by_path("/soc@0/interconnect@19100000");
	struct device_node *cnoc __free(device_node) =
		of_find_node_by_path("/soc@0/interconnect@1500000");
	int rc = g0q_rpmh_remaining();

	if (rc)
		return g0q_usb_fail(report, G0Q_USB_RUN_STATE, (u32)rc, rc);
	if (!gem || !cnoc)
		return g0q_usb_fail(report, G0Q_ICC_NODE, (!gem) | ((!cnoc) << 1), -ENODEV);
	if (IS_ERR_OR_NULL(path))
		return g0q_usb_fail(report, G0Q_ICC_PATH, path ? (u32)PTR_ERR(path) : 0,
				    path ? PTR_ERR(path) : -ENODEV);
	if (path->num_nodes != ARRAY_SIZE(nodes))
		return g0q_usb_fail(report, G0Q_ICC_LENGTH, path->num_nodes, -EINVAL);
	if (!mutex_trylock(&icc_bw_lock))
		return g0q_usb_fail(report, G0Q_ICC_LOCK, 0, -EBUSY);
	for (unsigned int i = 0; i < ARRAY_SIZE(nodes); i++) {
		const struct icc_req *r = &path->reqs[i];
		size_t len = strlen(nodes[i]);
		u32 flags = (r->dev != dev) | ((!r->enabled) << 1) |
			(!!r->tag << 2) | ((r->peak_bw < 1000) << 3);
		if (!r->node || !r->node->name || !r->node->provider || !r->node->provider->dev)
			flags |= 1U << 4;
		else {
			if (r->node->provider->dev->of_node != (i < 2 ? gem : cnoc))
				flags |= 1U << 5;
			if (strncmp(r->node->name, nodes[i], len) || r->node->name[len] != '@' ||
			    strcmp(r->node->name + len + 1, dev_name(r->node->provider->dev)))
				flags |= 1U << 6;
		}
		if (flags) {
			rc = g0q_usb_fail(report, G0Q_ICC_REQUEST, (i << 16) | flags, -EBUSY);
			goto out;
		}
	}
	rc = g0q_bcm_confirm_usb(report);
out:
	mutex_unlock(&icc_bw_lock);
	return rc;
}
EXPORT_SYMBOL_GPL(g0q_icc_confirm_usb);
