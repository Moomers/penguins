#!/usr/bin/python

import usb, usb.core, usb.util

Vendor_ID = 0x1ffb
Product_ID = 0x0098

class SimpleMotorController(object):
    """Represents a single motor controller connected via USB

    Allows talking to it"""
    def __init__(self, device):
        """Accepts the libusb device object for the controller"""
        self.device = device
        self.serial_number = usb.util.get_string(self.device, 128, self.device.iSerialNumber)
        self.manufacturer = usb.util.get_string(self.device, 128, self.device.iManufacturer)
        self.product = usb.util.get_string(self.device, 128, self.device.iProduct)

class SmcUsbDriver(object):
    """Driver for the Pololu Simple Motor Controllers over USB"""
    def __init__(self, left_controller, right_controller):
        self.motors = {
                'left':left_controller,
                'right':right_controller,
                }

        #make the controller ready to run
        pass


if __name__ == '__main__':
    devices = usb.core.find(idVendor = Vendor_ID, idProduct = Product_ID, find_all = True)

    controllers = []
    for device in devices:
        controllers.append(SimpleMotorController(device))

    #find the left and right controllers
    #pass them in the right order to the driver object
    #get some info from the driver object about speed, and then exit
    notes = """
            T:  Bus=02 Lev=02 Prnt=02 Port=01 Cnt=01 Dev#= 96 Spd=12  MxCh= 0
            D:  Ver= 2.00 Cls=ef(misc ) Sub=02 Prot=01 MxPS=64 #Cfgs=  1
            P:  Vendor=1ffb ProdID=0098 Rev=01.03
            S:  Manufacturer=Pololu Corporation
            S:  Product=Pololu Simple High-Power Motor Controller 18v15
            S:  SerialNumber=3000-6D06-3142-3732-6271-2243
            C:  #Ifs= 3 Cfg#= 1 Atr=c0 MxPwr=100mA
            I:  If#= 0 Alt= 0 #EPs= 1 Cls=02(commc) Sub=02 Prot=01 Driver=cdc_acm
            I:  If#= 1 Alt= 0 #EPs= 2 Cls=0a(data ) Sub=00 Prot=00 Driver=cdc_acm
            I:  If#= 2 Alt= 0 #EPs= 0 Cls=ff(vend.) Sub=07 Prot=01 Driver=(none)

            d = usb.core.find(idVendor = 0x1ffb, idProduct=0x0098, find_all = True)[0]"""

