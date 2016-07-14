#!/usr/bin/python

from gatt import *

from adafruit_i2c import Adafruit_I2C

mainloop = None

class LEDAdvertisement(Advertisement):

    def __init__(self, bus, index):
        Advertisement.__init__(self, bus, index, 'peripheral')
        self.add_service_uuid('180F')
        self.add_manufacturer_data(0xffff, [0x00, 0x01, 0x02, 0x03, 0x04])
        self.add_service_data('9999', [0x00, 0x01, 0x02, 0x03, 0x04])
        self.include_tx_power = True


class LEDService(Service):
    """
    i2c LED wrapper Service.

    """
    LED_UUID = '180f' #battery

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.LED_UUID, True)
        self.add_characteristic(LEDBoardCharacteristic(bus, 0, self))

class LEDBoardCharacteristic(Characteristic):
    """
    i2cset/i2cget wrapper Characteristic.

    """
    LED_BOARD_UUID = '2a19' #battery_level

    def __init__(self, bus, index, service):
        self.led_list = []
        self.i2cbus = Adafruit_I2C(address=114, busnum=1, debug=True)
        self.i2cbus.readList(00, 16)
        Characteristic.__init__(
                self, bus, index,
                self.LED_BOARD_UUID,
                ['read', 'write'],
                service)

    def ReadLEDList(self):
        self.led_list = self.i2cbus.readList(00, 16)

    def WriteLEDList(self):
        self.i2cbus.writeList(00, self.led_list)

    def ReadValue(self):
        self.ReadLEDList()
        print('LEDBoardCharacteristic read: ' + repr(self.led_list))
        return [dbus.Byte(x) for x in self.led_list]

    def WriteValue(self, value):
        print('LEDBoardCharacteristic Write: ' + repr(value))
        if len(value) != 16:
            raise InvalidValueLengthException()
        self.led_list = value
        self.WriteLEDList()

def register_app_cb():
    print('GATT application registered')


def register_app_error_cb(error):
    print('Failed to register application: ' + str(error))
    mainloop.quit()

def register_ad_cb():
    print 'Advertisement registered'


def register_ad_error_cb(error):
    print 'Failed to register advertisement: ' + str(error)
    mainloop.quit()

def main():
    global mainloop

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()

    ad_man = find_ad_manager(bus)
    if not ad_man:
        print 'LEAdvertisingManager1 interface not found'
        return

    ad_man_props = find_interface(bus, ad_man, "org.freedesktop.DBus.Properties")

    ad_man_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))

    ad_manager = find_ad_interface(bus, ad_man)

    led_advertisement = LEDAdvertisement(bus, 0)


    gatt_man = find_gatt_manager(bus)
    if not gatt_man:
        print('GattManager1 interface not found')
        return

    service_manager = find_gatt_interface(bus, gatt_man)

    app = Application(bus)

    app.add_service(LEDService(bus, 0))

    mainloop = GObject.MainLoop()

    ad_manager.RegisterAdvertisement(led_advertisement.get_path(), {},
                                     reply_handler=register_ad_cb,
                                     error_handler=register_ad_error_cb)

    service_manager.RegisterApplication(app.get_path(), {},
                                    reply_handler=register_app_cb,
                                    error_handler=register_app_error_cb)

    mainloop.run()

if __name__ == '__main__':
    main()
