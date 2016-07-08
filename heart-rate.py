#!/usr/bin/env python3

from gatt import *

mainloop = None

class HeartRateAdvertisement(Advertisement):

    def __init__(self, bus, index):
        Advertisement.__init__(self, bus, index, 'peripheral')
        self.add_service_uuid('180D')
        self.add_manufacturer_data(0xffff, [0x00, 0x01, 0x02, 0x03, 0x04])
        self.add_service_data('9999', [0x00, 0x01, 0x02, 0x03, 0x04])
        self.include_tx_power = True

class HeartRateService(Service):
    """
    Fake Heart Rate Service that simulates a fake heart beat and control point
    behavior.

    """
    HR_UUID = '0000180d-0000-1000-8000-00805f9b34fb'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.HR_UUID, True)
        self.add_characteristic(HeartRateMeasurementChrc(bus, 0, self))
        self.add_characteristic(BodySensorLocationChrc(bus, 1, self))
        self.add_characteristic(HeartRateControlPointChrc(bus, 2, self))
        self.energy_expended = 0


class HeartRateMeasurementChrc(Characteristic):
    HR_MSRMT_UUID = '00002a37-0000-1000-8000-00805f9b34fb'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.HR_MSRMT_UUID,
                ['notify'],
                service)
        self.notifying = False
        self.hr_ee_count = 0

    def hr_msrmt_cb(self):
        value = []
        value.append(dbus.Byte(0x06))

        value.append(dbus.Byte(randint(90, 130)))

        if self.hr_ee_count % 10 == 0:
            value[0] = dbus.Byte(value[0] | 0x08)
            value.append(dbus.Byte(self.service.energy_expended & 0xff))
            value.append(dbus.Byte((self.service.energy_expended >> 8) & 0xff))

        self.service.energy_expended = \
                min(0xffff, self.service.energy_expended + 1)
        self.hr_ee_count += 1

        print('Updating value: ' + repr(value))

        self.PropertiesChanged(GATT_CHRC_IFACE, { 'Value': value }, [])

        return self.notifying

    def _update_hr_msrmt_simulation(self):
        print('Update HR Measurement Simulation')

        if not self.notifying:
            return

        GObject.timeout_add(1000, self.hr_msrmt_cb)

    def StartNotify(self):
        if self.notifying:
            print('Already notifying, nothing to do')
            return

        self.notifying = True
        self._update_hr_msrmt_simulation()

    def StopNotify(self):
        if not self.notifying:
            print('Not notifying, nothing to do')
            return

        self.notifying = False
        self._update_hr_msrmt_simulation()


class BodySensorLocationChrc(Characteristic):
    BODY_SNSR_LOC_UUID = '00002a38-0000-1000-8000-00805f9b34fb'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.BODY_SNSR_LOC_UUID,
                ['read'],
                service)

    def ReadValue(self, options):
        # Return 'Chest' as the sensor location.
        return [ 0x01 ]

class HeartRateControlPointChrc(Characteristic):
    HR_CTRL_PT_UUID = '00002a39-0000-1000-8000-00805f9b34fb'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.HR_CTRL_PT_UUID,
                ['write'],
                service)

    def WriteValue(self, value, options):
        print('Heart Rate Control Point WriteValue called')

        if len(value) != 1:
            raise InvalidValueLengthException()

        byte = value[0]
        print('Control Point value: ' + repr(byte))

        if byte != 1:
            raise FailedException("0x80")

        print('Energy Expended field reset!')
        self.service.energy_expended = 0

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

    heart_rate_advertisement = HeartRateAdvertisement(bus, 0)


    gatt_man = find_gatt_manager(bus)
    if not gatt_man:
        print('GattManager1 interface not found')
        return

    service_manager = find_gatt_interface(bus, gatt_man)

    app = Application(bus)

    app.add_service(HeartRateService(bus, 0))

    mainloop = GObject.MainLoop()

    ad_manager.RegisterAdvertisement(heart_rate_advertisement.get_path(), {},
                                     reply_handler=register_ad_cb,
                                     error_handler=register_ad_error_cb)

    service_manager.RegisterApplication(app.get_path(), {},
                                    reply_handler=register_app_cb,
                                    error_handler=register_app_error_cb)

    mainloop.run()

if __name__ == '__main__':
    main()
