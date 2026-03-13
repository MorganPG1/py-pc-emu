from io_base.io import IODevice
from unicorn import Uc

class CPU():
    def __init__(self) -> None:
        '''
        The base class for a CPU
        
        :param self: The CPU object
        '''
        self.mu:Uc
        '''The internal Uc object (provided by the unicorn library) used for code execution and memory management in the CPU'''

        pass

    def bindIOPorts(self, ports:list[int], ioDevice:IODevice):
        '''
        Binds a list of I/O Ports to the I/O device (note: you should probably be using addIODevice)
        
        :param self: The CPU object
        :param ports: A list of the I/O Ports to bind to the I/O device
        :type ports: list[int]
        :param ioDevice: The I/O Device to bind to the ports
        :type ioDevice: IODevice
        '''
        pass
    
    def addIODevice(self, ioDevice:IODevice):
        '''
        Adds an I/O device to the CPU's I/O.

        :param self: The CPU object
        :param ioDevice: The I/O Device to add.
        :type ioDevice: IODevice
        '''
        pass

    def addIODevices(self, ioDevices:list[IODevice]):
        '''
        The same as addIODevice except it adds a list of IODevices

        :param self: The CPU object
        :param ioDevices: A list of I/O Devices to add.
        :type ioDevices: list[IODevice]
        '''
        pass
    
    def step(self, count:int):
        '''
        Steps the CPU Forward

        :param self: The CPU Object
        :param count: The number of instructions to execute.
        :type count: int
        '''
        pass

    def interrupts_enabled(self) -> bool:
        '''
        Returns true if interrupts are enabled, else false
        :param self: The CPU object
        '''
        return True

    def call_int(self, interrupt:int) -> None:
        '''
        Calls an interrupt

        :param self: The CPU object
        :param interrupt: The interrupt number
        :type interrupt: int
        '''
        pass
