#!/usr/bin/env python3

from gatt import *

mainloop = None

class TestAdvertisement(Advertisement):

    def __init__(self, bus, index):
        Advertisement.__init__(self, bus, index, 'peripheral')
        self.add_service_uuid('1234')
        self.add_manufacturer_data(0xffff, [0x00, 0x01, 0x02, 0x03, 0x04])
        self.add_service_data('9999', [0x00, 0x01, 0x02, 0x03, 0x04])
        self.include_tx_power = True

class TestService(Service):
    TEST_SERVICE_UUID = '1234'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.TEST_SERVICE_UUID, True)
        self.add_characteristic(TestCharacteristic1(bus, 0, self))
        self.add_characteristic(TestCharacteristic2(bus, 1, self))

class TestCharacteristic1(Characteristic):
    TEST_CHAR_UUID = '2345'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.TEST_CHAR_UUID,
                ['read', 'write'],
                service)
        self.number = 42
        self.add_descriptor(TestDescriptor1(bus, 0, self))
        self.add_descriptor(TestDescriptor2(bus, 1, self))

    def ReadValue(self, options):
        print('TestCharacteristic1 Read: ' + repr(self.number))
        return [dbus.Byte(self.number)]

    def WriteValue(self, value, options):
        print('TestCharacteristic1 Write: ' + repr(value))
        if len(value) != 1:
            raise InvalidValueLengthException()
        self.number = value[0]

class TestCharacteristic2(Characteristic):
    """
    This characteristic UUID is blacklisted for write but not for read
    """
    TEST_CHAR_UUID = '2a02'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.TEST_CHAR_UUID,
                ['read', 'write'],
                service)
        self.number = 42
        self.add_descriptor(TestDescriptor1(bus, 0, self))
        self.add_descriptor(TestDescriptor2(bus, 1, self))

    def ReadValue(self, options):
        print('TestCharacteristic1 Read: ' + repr(self.number))
        return [dbus.Byte(self.number)]

    def WriteValue(self, value, options):
        print('TestCharacteristic1 Write: ' + repr(value))
        if len(value) != 1:
            raise InvalidValueLengthException()
        self.number = value[0]

class TestCharacteristic2(Characteristic):
    """
    This characteristic UUID is blacklisted for write but not for read
    """
    TEST_CHAR_UUID = '2a02'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.TEST_CHAR_UUID,
                ['read', 'write'],
                service)
        self.number = 42

    def ReadValue(self, options):
        print('TestCharacteristic1 Read: ' + repr(self.number))
        return [dbus.Byte(self.number)]

    def WriteValue(self, value, options):
        print('TestCharacteristic1 Write: ' + repr(value))
        if len(value) != 1:
            raise InvalidValueLengthException()
        self.number = value[0]

class TestDescriptor1(Descriptor):
    TEST_DESC_UUID = '3456'

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(
                self, bus, index,
                self.TEST_DESC_UUID,
                ['read', 'write'],
                characteristic)
        self.number = 43

    def ReadValue(self, options):
        print('TestDescriptor1 Read: ' + repr(self.number))
        return [dbus.Byte(self.number)]

    def WriteValue(self, value, options):
        print('TestDescriptor1 Write: ' + repr(value))
        if len(value) != 1:
            raise InvalidValueLengthException()
        self.number = value[0]

class TestDescriptor2(Descriptor):
    """
    This descriptor UUID is blacklisted for write but not for read
    """
    TEST_DESC_UUID = '2902'

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(
                self, bus, index,
                self.TEST_DESC_UUID,
                ['read', 'write'],
                characteristic)
        self.number = 43

    def ReadValue(self, options):
        print('TestDescriptor2 Read: ' + repr(self.number))
        return [dbus.Byte(self.number)]

    def WriteValue(self, value, options):
        print('TestDescriptor2 Write: ' + repr(value))
        if len(value) != 1:
            raise InvalidValueLengthException()
        self.number = value[0]

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

    battery_advertisement = TestAdvertisement(bus, 0)


    gatt_man = find_gatt_manager(bus)
    if not gatt_man:
        print('GattManager1 interface not found')
        return

    service_manager = find_gatt_interface(bus, gatt_man)

    app = Application(bus)

    app.add_service(TestService(bus, 0))

    mainloop = GObject.MainLoop()

    ad_manager.RegisterAdvertisement(battery_advertisement.get_path(), {},
                                     reply_handler=register_ad_cb,
                                     error_handler=register_ad_error_cb)

    service_manager.RegisterApplication(app.get_path(), {},
                                    reply_handler=register_app_cb,
                                    error_handler=register_app_error_cb)

    mainloop.run()

if __name__ == '__main__':
    main()


