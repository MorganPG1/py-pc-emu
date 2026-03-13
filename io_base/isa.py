'''
IBM PC Emulator Project - MorganPG

io_base.isa

ISA Bus Emulation
Handles interaction between the CPU and ISA Bus Devices
'''

class ISADevice():

    def __init__(self) -> None:
        '''
        The base class for an ISA Device

        :param self: The ISA Device
        '''

        self.mem_range:tuple[int,int]
        '''The range of memory addresses this ISA device takes up in the format (start, end)'''
    
    def writeMem(self, addr:int, value:int) -> None:
        '''
        Writes data to a memory address in the ISA Device.

        :param self: The ISA Device
        :param addr: The offset from the start of the memory range.
        :param value: The value to store in the memory address.
        :type addr: int
        :type value: int
        '''
        pass
    
    def readMem(self, addr:int) -> int:
        '''
        Returns the value stored at the memory address in the ISA Device.

        :param self: The ISA Device
        :param addr: The offset from the start of the memory range.
        :type addr: int
        :return: The data stored in the memory address
        :rtype: int
        '''
        return 0xFF
class ISABus():
    def __init__(self) -> None:
        '''
        ISA Bus Emulation

        :param self: The ISABus object
        '''
        self.devices:list[ISADevice] = []
        
        pass
    def write(self, addr:int, value:int) -> None:
        '''
        Writes data to the ISA Bus
        
        :param self: The ISABus object
        :param addr: The physical memory address to write to
        :type addr: int
        :param value: The data at the memory address
        :type value: int
        '''
        for dev in self.devices:
            start = dev.mem_range[0]
            end = dev.mem_range[1]
            if addr >= start and addr < end:
                offset = addr-start
                dev.writeMem(
                    offset,
                    value
                )

        pass

    def read(self, addr:int) -> int:
        '''
        Reads data from the ISA Bus
        
        :param self: The ISABus object
        :param addr: The physical memory address to read from
        :type addr: int
        :return: The data at the memory address
        :rtype: int
        '''
        for dev in self.devices:
            start = dev.mem_range[0]
            end = dev.mem_range[1]
            if addr >= start and addr < end:
                offset = addr-start
                return dev.readMem(offset)
        return 0xFF
    
    def addDevice(self, device:ISADevice) -> None:
        '''
        Adds a device to the ISABus

        :param self: The ISABus object
        :param device: The ISA Device
        :type device: ISADevice
        '''
        self.devices.append(device)
