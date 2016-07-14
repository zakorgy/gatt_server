#!/usr/bin/python

from gatt import *

mainloop = None

class TestAdvertisement(Advertisement):

    def __init__(self, bus, index):
        Advertisement.__init__(self, bus, index, 'peripheral')
        self.add_service_uuid('180F')
        self.add_service_uuid('180D')
        self.add_service_uuid('1234')
        # we need to comment a line, or the adwertised packet will be too long 
        # self.add_manufacturer_data(0xffff, [0x00, 0x01, 0x02, 0x03, 0x04])
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

    def ReadValue(self):
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

    def WriteValue(self, value):
        print('Heart Rate Control Point WriteValue called')

        if len(value) != 1:
            raise InvalidValueLengthException()

        byte = value[0]
        print('Control Point value: ' + repr(byte))

        if byte != 1:
            raise FailedException("0x80")

        print('Energy Expended field reset!')
        self.service.energy_expended = 0

class WriteTestService(Service):
    TEST_SERVICE_UUID = '1234'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.TEST_SERVICE_UUID, True)
        self.add_characteristic(WritableTestChracteristic(bus, 0, self))
        self.add_characteristic(NotWritableTestChracteristic(bus, 1, self))

class WritableTestChracteristic(Characteristic):
    TEST_CHAR_UUID = '2345'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.TEST_CHAR_UUID,
                ['read', 'write'],
                service)
        self.number = 42
        self.add_descriptor(WritableTestDescriptor(bus, 0, self))
        self.add_descriptor(NotWritableTestDescriptor(bus, 1, self))

    def ReadValue(self):
        print('WritableTestChracteristic Read: ' + repr(self.number))
        return [dbus.Byte(self.number)]

    def WriteValue(self, value):
        print('WritableTestChracteristic Write: ' + repr(value))
        if len(value) != 1:
            raise InvalidValueLengthException()
        self.number = value[0]

class NotWritableTestChracteristic(Characteristic):
    """
    This characteristic UUID is only blacklisted for write
    """
    TEST_CHAR_UUID = '2a02'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.TEST_CHAR_UUID,
                ['read', 'write'],
                service)
        self.number = 42
        self.add_descriptor(WritableTestDescriptor(bus, 0, self))
        self.add_descriptor(NotWritableTestDescriptor(bus, 1, self))

    def ReadValue(self):
        print('NotWritableTestChracteristic Read: ' + repr(self.number))
        return [dbus.Byte(self.number)]

    def WriteValue(self, value):
        print('NotWritableTestChracteristic Write: ' + repr(value))
        if len(value) != 1:
            raise InvalidValueLengthException()
        self.number = value[0]

class WritableTestDescriptor(Descriptor):
    TEST_DESC_UUID = '3456'

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(
                self, bus, index,
                self.TEST_DESC_UUID,
                ['read', 'write'],
                characteristic)
        self.number = 43

    def ReadValue(self):
        print('WritableTestDescriptor Read: ' + repr(self.number))
        return [dbus.Byte(self.number)]

    def WriteValue(self, value):
        print('WritableTestDescriptor Write: ' + repr(value))
        if len(value) != 1:
            raise InvalidValueLengthException()
        self.number = value[0]

class NotWritableTestDescriptor(Descriptor):
    """
    This descriptor UUID is only blacklisted for write
    """
    TEST_DESC_UUID = '2902'

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(
                self, bus, index,
                self.TEST_DESC_UUID,
                ['read', 'write'],
                characteristic)
        self.number = 43

    def ReadValue(self):
        print('NotWritableTestDescriptor Read: ' + repr(self.number))
        return [dbus.Byte(self.number)]

    def WriteValue(self, value):
        print('NotWritableTestDescriptor Write: ' + repr(value))
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

    app.add_service(BatteryService(bus, 0))
    app.add_service(HeartRateService(bus, 1))
    app.add_service(WriteTestService(bus, 2))

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
