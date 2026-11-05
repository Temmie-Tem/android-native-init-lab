// SPDX-License-Identifier: GPL-2.0-only
/* The two selected endpoints have identical fabric masks. Only look at the
 * USB consumer that owns the already active and PM-held controller. No UFS
 * request is created and no BCM/cache value is published by this check.
 */
#include <soc/qcom/g0q-ml030.h>
int g0q_icc_confirm_usb(struct icc_path *path, const struct device *dev)
{
	static const char *const nodes[] = {
		"chm_apps", "qns_gem_noc_cnoc", "qnm_gemnoc_cnoc", "qhs_usb3_0"
	};
	struct device_node *gem __free(device_node) =
		of_find_node_by_path("/soc@0/interconnect@19100000");
	struct device_node *cnoc __free(device_node) =
		of_find_node_by_path("/soc@0/interconnect@1500000");
	int rc = -EBUSY;

	if (!gem || !cnoc || g0q_rpmh_remaining() || IS_ERR_OR_NULL(path) ||
	    path->num_nodes != ARRAY_SIZE(nodes) || !mutex_trylock(&icc_bw_lock))
		return rc;
	for (unsigned int i = 0; i < ARRAY_SIZE(nodes); i++) {
		const struct icc_req *r = &path->reqs[i];
		size_t len = strlen(nodes[i]);
		if (r->dev != dev || !r->enabled || r->tag || r->peak_bw < 1000 ||
		    !r->node || !r->node->name || !r->node->provider ||
		    !r->node->provider->dev ||
		    r->node->provider->dev->of_node != (i < 2 ? gem : cnoc) ||
		    strncmp(r->node->name, nodes[i], len) || r->node->name[len] != '@' ||
		    strcmp(r->node->name + len + 1, dev_name(r->node->provider->dev)))
			goto out;
	}
	rc = g0q_bcm_confirm_usb();
out:
	mutex_unlock(&icc_bw_lock);
	return rc;
}
EXPORT_SYMBOL_GPL(g0q_icc_confirm_usb);
