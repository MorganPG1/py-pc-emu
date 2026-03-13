'''
IBM PC Emulator Project - MorganPG

io_base.io

I/O Device Emulation
Handles interaction between the CPU and I/O Devices

Sources I used for I/O port addresses:
https://wiki.preterhuman.net/XT,_AT_and_PS/2_I/O_port_addresses
https://www.stanislavs.org/helppc/ports.html
'''
class IODevice():
    #Base class for IO Devices
    def __init__(self) -> None:
        '''
        Base class for all I/O Devices to inherit from
        
        :param self: The IODevice object
        '''
        self.io_range:range|list[int] = []
        '''A list of I/O Ports the device uses'''
        
        pass

    def read(self, port:int) -> int:
        '''
        I/O Read handler for the IODevice

        :param self: The IODevice 
        :param port: The I/O port being read
        :type port: int
        :return: The data from the I/O port
        :rtype: int
        '''
        #Read from the IO Port
        return 0xFF

    def write(self,port:int, value:int) -> None:
        '''
        I/O Write handler for the IODevice

        :param self: The IODevice
        :param port: The I/O port being written to
        :type port: int
        :param value: The data to store in the I/O port
        :type value: int
        '''
        #Write to the IO Port
        pass
