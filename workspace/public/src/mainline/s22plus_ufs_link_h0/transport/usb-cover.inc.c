// SPDX-License-Identifier: GPL-2.0-only
#include <linux/of_platform.h>
#include <soc/qcom/g0q-ml030.h>
int g0q_usb_cover(struct device **held)
{
	struct device_node *np __free(device_node) = of_find_node_by_path("/soc@0/usb@a600000");
	struct platform_device *pdev;
	struct device *dev;
	struct dwc3 *dwc;
	struct dwc3_qcom *qcom;
	int rc;

	if (*held || g0q_rpmh_remaining() || !np ||
	    !of_device_is_compatible(np, "qcom,sm8450-dwc3"))
		return -ENODEV;
	pdev = of_find_device_by_node(np);
	if (!pdev)
		return -ENODEV;
	dev = &pdev->dev;
	rc = -EBUSY;
	if (!device_trylock(dev))
		goto put;
	if (!dev->driver || strcmp(dev->driver->name, "dwc3-qcom"))
		goto unlock;
	dwc = dev_get_drvdata(dev);
	if (!dwc)
		goto unlock;
	qcom = to_dwc3_qcom(dwc);
	if (qcom->dev != dev || pm_runtime_get_if_active(dev) != 1)
		goto unlock;
	rc = g0q_icc_confirm_usb(qcom->icc_path_apps, dev);
	if (!rc) {
		*held = dev;
		device_unlock(dev);
		return 0;
	}
	pm_runtime_put_noidle(dev);
unlock:
	device_unlock(dev);
put:
	put_device(dev);
	return rc;
}
EXPORT_SYMBOL_GPL(g0q_usb_cover);
