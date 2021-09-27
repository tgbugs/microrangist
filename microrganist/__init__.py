#!/usr/bin/env python

""" Kernel needs CONFIG_INPUT_UINPUT set and/or load the uinput
module. Install pyusb and python-evdev. Run as root. """

import usb.core
import usb.util
import evdev
from evdev import ecodes

dev = usb.core.find(idVendor=0x05f3, idProduct=0x00ff)

if dev is None:
    raise ValueError('dev not found')

# get an endpoint instance
cfg = dev.get_active_configuration()

intf = cfg[(0,0)]

end_in = usb.util.find_descriptor(
    intf,
    # match the first IN endpoint
    custom_match = \
    lambda e: \
        usb.util.endpoint_direction(e.bEndpointAddress) == \
        usb.util.ENDPOINT_IN)

# lol nice bitmask
left   = 0b001
mid    = 0b010
right  = 0b100

# set your keybindings here
key_map = {
    left: ecodes.KEY_LEFTALT,
    mid: ecodes.KEY_LEFTCTRL,
    right: ecodes.KEY_LEFTSHIFT,
}

ui = evdev.uinput.UInput(
    name='VEC Footpedal Keyboard',
)

try:
    if dev.is_kernel_driver_active(intf.index):
        dev.detach_kernel_driver(intf.index)
        usb.util.claim_interface(dev, intf.index)
    previous_state = 0
    while True:
        try:
            data = dev.read(end_in.bEndpointAddress, end_in.wMaxPacketSize, 5000)
            # use a 5 second timeout which is quite infrequent
            # enough to start blocking again and limits shutdown time

            state, _ = data
            diff = state ^ previous_state

            l = diff & left
            dl = l & state
            lop = (l, dl)

            m = diff & mid
            dm = (m & state) >> 1
            mop = (m, dm)

            r = diff & right
            dr = (r & state) >> 2
            dop = (r, dr)

            previous_state = state

            for k, dk in [lop, mop, dop]:
                if k:
                    key = key_map[k]
                    ui.write(evdev.ecodes.EV_KEY, key, dk)
                    ui.syn()

        except usb.core.USBTimeoutError as e:
            pass
        except usb.core.USBError as e:
            print(e, type(e))

finally:
    usb.util.release_interface(dev, intf.index)
    dev.attach_kernel_driver(intf.index)
