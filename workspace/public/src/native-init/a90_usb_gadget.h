#ifndef A90_USB_GADGET_H
#define A90_USB_GADGET_H

#include <stdbool.h>
#include <stddef.h>

struct a90_usb_gadget_status {
    bool configfs_mounted;
    bool gadget_dir;
    bool acm_function;
    bool acm_link;
    bool adb_link;
    bool udc_bound;
    char udc[64];
};

int a90_usb_gadget_setup_acm(void);
int a90_usb_gadget_reset_acm(void);
int a90_usb_gadget_unbind(void);
int a90_usb_gadget_bind_default_udc(void);
int a90_usb_gadget_status(struct a90_usb_gadget_status *out);

#endif
