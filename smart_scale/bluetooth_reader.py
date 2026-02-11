import struct
import time
from bluepy.btle import Scanner, DefaultDelegate

class ScanDelegate(DefaultDelegate):
    def __init__(self, mac_address):
        DefaultDelegate.__init__(self)
        self.mac_address = mac_address
        self.stabilized_data = None

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if self.stabilized_data is not None:
            return

        if dev.addr == self.mac_address:
            for (adtype, desc, value) in dev.getScanData():
                if adtype == 22:
                    data = bytes.fromhex(value[4:])
                    if len(data) < 13:
                        continue
                    
                    ctrlByte1 = data[1]
                    isStabilized = ctrlByte1 & (1 << 5)
                    hasImpedance = ctrlByte1 & (1 << 1)

                    if isStabilized and hasImpedance:
                        print("Found stabilized measurement with impedance.")
                        self.stabilized_data = data
                        return

class BluetoothReader:
    def __init__(self, mac_address):
        self.mac_address = mac_address
        self.delegate = ScanDelegate(mac_address)

    def get_data(self, scan_duration=20.0):
        scanner = Scanner().withDelegate(self.delegate)
        self.delegate.stabilized_data = None  # Reset before each scan cycle
        
        print(f"Scanning for device with MAC {self.mac_address} for {scan_duration} seconds...")
        
        scanner.scan(scan_duration)
        
        print("Scanning finished.")
        return self.delegate.stabilized_data
