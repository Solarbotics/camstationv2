#Basic try to get the hand-scanner to show up and be read


try:
    import usb.core
    import usb.util
except ImportError:
    logging.warn('Failed to import usb')
    usb = None


def get_scale():
    device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    if device is None:
        return None

    if device.is_kernel_driver_active(0):
        device.detach_kernel_driver(0)

    device.set_configuration()

    return device
