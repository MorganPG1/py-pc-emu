'''
IBM PC Emulator Project - MorganPG

floppy.fdc:

NEC µPD765 FDC (Floppy Disk Controller) Emulation
Should be mapped into IO Ports 0x3f2, 0x3f4 and 0x3f5

Main source: https://www.isdaman.com/alsos/hardware/fdc/floppy.htm
'''
#Imports 
from io_base.io import IODevice
from board.dma import DMAChannel

class UPD765_FDC(IODevice):
    def __init__(self, dma:DMAChannel):
        '''
        NEC µPD765 FDC (Floppy Disk Controller) Emulation
        
        :param self: The FDC object
        :param dma: The DMA Channel used for reading data
        :type dma: DMAChannel
        '''
        self.io_range = [
            0x3f2,
            0x3f4,
            0x3f5
        ]
        self.dma_enabled = False
        self.controllerEnabled = False
        self.motorActive = False
        self.receiving = False
    def write(self, port, value):
        match port:
            case 0x3F2: #DOR
                self.controllerEnabled = (value & 0b100) != 0
                self.motorActive = (value & 0b10000) != 0
            case 0x3F5:
                print(hex(value))
    def read(self, port):
        match port:
            case 0x3F4:
                resp = 0b10000000

                if not self.dma_enabled:
                    resp |= 0b100000
                if not self.receiving:
                    resp |= 0b1000000
                    
                return resp
        return 0xFF
