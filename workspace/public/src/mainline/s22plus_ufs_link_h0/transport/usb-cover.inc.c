// SPDX-License-Identifier: GPL-2.0-only
#include <linux/of_platform.h>
#include <soc/qcom/g0q-ml030.h>
int g0q_usb_cover(struct device **held, struct g0q_usb_report *report)
{
	struct device_node *np __free(device_node) = of_find_node_by_path("/soc@0/usb@a600000");
	struct platform_device *pdev;
	struct device *dev;
	struct dwc3 *dwc;
	struct dwc3_qcom *qcom;
	int rc;

	*report = (struct g0q_usb_report) {};
	if (*held)
		return g0q_usb_fail(report, G0Q_USB_HELD, 0, -EINVAL);
	rc = g0q_rpmh_remaining();
	if (rc)
		return g0q_usb_fail(report, G0Q_USB_RUN_STATE, (u32)rc, rc);
	if (!np || !of_device_is_compatible(np, "qcom,sm8450-dwc3"))
		return g0q_usb_fail(report, G0Q_USB_NODE, np ? 2 : 1, -ENODEV);
	pdev = of_find_device_by_node(np);
	if (!pdev)
		return g0q_usb_fail(report, G0Q_USB_DEVICE, 0, -ENODEV);
	dev = &pdev->dev;
	rc = g0q_usb_fail(report, G0Q_USB_LOCK, 0, -EBUSY);
	if (!device_trylock(dev))
		goto put;
	if (!dev->driver || strcmp(dev->driver->name, "dwc3-qcom")) {
		rc = g0q_usb_fail(report, G0Q_USB_DRIVER, dev->driver ? 2 : 1, -ENODEV);
		goto unlock;
	}
	dwc = dev_get_drvdata(dev);
	if (!dwc) {
		rc = g0q_usb_fail(report, G0Q_USB_DATA, 1, -ENODEV);
		goto unlock;
	}
	qcom = to_dwc3_qcom(dwc);
	if (qcom->dev != dev) {
		rc = g0q_usb_fail(report, G0Q_USB_DATA, 2, -ENODEV);
		goto unlock;
	}
	rc = pm_runtime_get_if_active(dev);
	if (rc != 1) {
		rc = g0q_usb_fail(report, G0Q_USB_PM, (u32)rc, rc < 0 ? rc : -EBUSY);
		goto unlock;
	}
	rc = g0q_icc_confirm_usb(qcom->icc_path_apps, dev, report);
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
