#!/usr/bin/python

from gatt import *

mainloop = None

class BatteryAdvertisement(Advertisement):

    def __init__(self, bus, index):
        Advertisement.__init__(self, bus, index, 'peripheral')
        self.add_service_uuid('180F')
        self.add_manufacturer_data(0xffff, [0x00, 0x01, 0x02, 0x03, 0x04])
        self.add_service_data('9999', [0x00, 0x01, 0x02, 0x03, 0x04])
        self.include_tx_power = True

class BatteryService(Service):
    BATTERY_UUID = '180f'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.BATTERY_UUID, True)
        self.add_characteristic(BatteryLevelCharacteristic(bus, 0, self))

class BatteryLevelCharacteristic(Characteristic):
    BATTERY_LVL_UUID = '2a19'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.BATTERY_LVL_UUID,
                ['read', 'write', 'notify'],
                service)
        self.notifying = False
        self.battery_lvl = 100
        self.charging = False
        GObject.timeout_add(5000, self.drain_battery)

    def notify_battery_level(self):
        if not self.notifying:
            return
        self.PropertiesChanged(
                GATT_CHRC_IFACE,
                { 'Value': [dbus.Byte(self.battery_lvl)] }, [])

    def drain_battery(self):
        if self.charging:
            if self.battery_lvl < 100:
                self.battery_lvl += 2
                if self.battery_lvl > 100:
                    self.battery_lvl = 100
            else:
                self.charging = False
        else:
            if self.battery_lvl > 0:
                self.battery_lvl -= 2
                if self.battery_lvl < 0:
                    self.battery_lvl = 0
            else:
                self.charging = True

        print('Battery Level drained: ' + repr(self.battery_lvl))
        self.notify_battery_level()
        return True

    def ReadValue(self):
        print('Battery Level read: ' + repr(self.battery_lvl))
        return [dbus.Byte(self.battery_lvl)]

    def WriteValue(self, value):
        print('Battery Level write')
        if len(value) != 1:
            raise InvalidValueLengthException()

        byte = value[0]
        print('write value: ' +repr(byte))
        if byte < 0 or byte > 100:
            raise NotPermittedException()
        self.battery_lvl = byte

    def StartNotify(self):
        if self.notifying:
            print('Already notifying, nothing to do')
            return

        self.notifying = True
        self.notify_battery_level()

    def StopNotify(self):
        if not self.notifying:
            print('Not notifying, nothing to do')
            return

        self.notifying = False

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

    battery_advertisement = BatteryAdvertisement(bus, 0)


    gatt_man = find_gatt_manager(bus)
    if not gatt_man:
        print('GattManager1 interface not found')
        return

    service_manager = find_gatt_interface(bus, gatt_man)

    app = Application(bus)

    app.add_service(BatteryService(bus, 0))

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
