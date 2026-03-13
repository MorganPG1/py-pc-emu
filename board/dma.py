'''
IBM PC Emulator Project - MorganPG

board.dma:

Intel 8237 DMA (Direct Memory Access) Emulation
Should be mapped into IO Ports 0x00-0x0F and 0x81-0x83 

Sources:
https://wiki.osdev.org/ISA_DMA
http://bos.asmhackers.net/docs/dma/docs/dmaprogramming.pdf
'''

'''
0000	r/w	DMA channel 0  address	byte  0, then byte 1.
0001	r/w	DMA channel 0 word count byte 0, then byte 1.
0002	r/w	DMA channel 1  address	byte  0, then byte 1.
0003	r/w	DMA channel 1 word count byte 0, then byte 1.
0004	r/w	DMA channel 2  address	byte  0, then byte 1.
0005	r/w	DMA channel 2 word count byte 0, then byte 1.
0006	r/w	DMA channel 3  address	byte  0, then byte 1.
0007	r/w	DMA channel 3 word count byte 0, then byte 1.

0008	r	DMA channel 0-3 status register
		 bit 7 = 1  channel 3 request
		 bit 6 = 1  channel 2 request
		 bit 5 = 1  channel 1 request
		 bit 4 = 1  channel 0 request
		 bit 3 = 1  channel terminal count on channel 3
		 bit 2 = 1  channel terminal count on channel 2
		 bit 1 = 1  channel terminal count on channel 1
		 bit 0 = 1  channel terminal count on channel 0

0008	w	DMA channel 0-3 command register
		 bit 7 = 1  DACK sense active high
		       = 0  DACK sense active low
		 bit 6 = 1  DREQ sense active high
		       = 0  DREQ sense active low
		 bit 5 = 1  extended write selection
		       = 0  late write selection
		 bit 4 = 1  rotating priority
		       = 0  fixed priority
		 bit 3 = 1  compressed timing
		       = 0  normal timing
		 bit 2 = 1  enable controller
		       = 0  enable memory-to-memory

0009	w	DMA write request register

000A	r/w	DMA channel 0-3 mask register
		 bit 7-3 = 0   reserved
		 bit 2	 = 0   clear mask bit
			 = 1   set mask bit
		 bit 1-0 = 00  channel 0 select
			 = 01  channel 1 select
			 = 10  channel 2 select
			 = 11  channel 3 select

000B	w	DMA channel 0-3 mode register
		 bit 7-6 = 00  demand mode
			 = 01  single mode
			 = 10  block mode
			 = 11  cascade mode
		 bit 5	 = 0   address increment select
			 = 1   address decrement select
		 bit 3-2 = 00  verify operation
			 = 01  write to memory
			 = 10  read from memory
			 = 11  reserved
		 bit 1-0 = 00  channel 0 select
			 = 01  channel 1 select
			 = 10  channel 2 select
			 = 11  channel 3 select

000C	w	DMA clear byte pointer flip-flop
000D	r	DMA read temporary register
000D	w	DMA master clear
000E	w	DMA clear mask register
000F	w	DMA write mask register
'''
#Imports
from io_base.io import IODevice
from unicorn import Uc
from enum import IntFlag
#Enums
class TRANSFER_MODE:
    SELF_TEST = 0 #Self test, probably not needed?
    DEV_TO_MEM = 1
    MEM_TO_DEV = 2

class CHANNEL_STATUS(IntFlag):
    CH0_TC = 1 << 0
    CH1_TC = 1 << 1
    CH2_TC = 1 << 2
    CH3_TC = 1 << 3
    CH0_REQ = 1 << 4
    CH1_REQ = 1 << 5
    CH2_REQ = 1 << 6
    CH3_REQ = 1 << 7

class DMATransfer():
    '''
    Handles DMA Transfers from both device to memory and memory to device
    '''
    def __init__(self, address:int, mode:int, count:int=0, buffer:bytes|None=None, reverse:bool=False) -> None:
        '''
        Handles DMA Transfers from both device to memory and memory to device
        
        :param self: The DMATransfer object
        :param address: The physical system memory address the transfer should begin at.
        :type address: int
        :param mode: The transfer mode
        :type mode: int
        :param count: The number of bytes to transfer (only needed if MEM_TO_DEV is used)
        :type count: int
        :param buffer: The data to transfer (only needed if DEV_TO_MEM is used)
        :type buffer: bytes | None
        :param reverse: If true, data is transfered in reverse
        :type reverse: bool
        '''
        self.address = address
    
        if mode == TRANSFER_MODE.MEM_TO_DEV:
            self.buffer = bytes()
        elif isinstance(buffer, bytes):
            self.buffer = buffer
        else:
            self.buffer = bytes()

        if mode == TRANSFER_MODE.DEV_TO_MEM:
            self.count = len(self.buffer)
        else:
            self.count = count
        pass

        if reverse:
            self.address -= self.count
            self.buffer = self.buffer[::-1]

    def transferToMem(self, uc:Uc) -> None:
        '''
        Transfers the buffer into system memory.

        :param self: The DMATransfer object
        :param uc: The Uc object (found with cpu.mu)
        :type uc: Uc
        '''
        uc.mem_write(self.address, self.buffer)
    def transferToDev(self, uc:Uc) -> bytes:
        '''
        Returns the data that should be transferred into the device's memory

        :param self: The DMATransfer object
        :param uc: The Uc object (found with cpu.mu)
        :type uc: Uc
        :return: The buffer to be transferred into the device
        :rtype: bytes
        '''
        self.buffer = uc.mem_read(self.address, self.count)
        return self.buffer
    
class DMAChannel():
    '''
    DMA Channel emulation
    '''
    def __init__(self) -> None:
        '''
        DMA Channel emulation

        :param self: The DMAChannel object
        '''
        self.requested = False
        self.tc = False
        self.masked = False
        self.auto = False
        self.reverse = False
        self.address = 0
        self.page = 0

        self.wordCount = 0
        self.mode = 0

        self.buffer:bytes = bytes()

    def initiateTransfer(self, buffer:bytes|None=None) -> DMATransfer|None:
        '''
        Initiates the DMA Transfer and returns the DMATransfer object

        :param self: The DMAChannel object
        :param buffer: The buffer (only needed if going from device to memory)
        :type buffer: bytes | None
        :return: The DMA Transfer (or none if the channel is masked)
        :rtype: DMATransfer | None
        '''
        if self.masked:
            self.requested = True
            return DMATransfer(
                (self.page << 16) | self.address,
                self.mode,
                self.wordCount,
                buffer,
                self.reverse
            )
        else:
            return
    def completeTransfer(self):
        '''
        Should be called after a DMA Transfer has completed, resets internal registers.

        :param self: The DMAChannel object
        '''
        if not self.auto:
            self.address = 0
        self.wordCount = 0
        self.tc = True
        

    

class DMA_8237(IODevice):
    '''
    Intel 8237 DMA (Direct Memory Access) Emulation
    '''

    def __init__(self):
        '''
        Intel 8237 DMA (Direct Memory Access) Emulation

        :param self: The DMA_8237 object
        '''

        self.channels = [
            DMAChannel(), #Channel 0 - DRAM Refresh
            DMAChannel(), #Channel 1 - Perpipheral
            DMAChannel(), #Channel 2 - Floppy
            DMAChannel(), #Channel 3 - Hard Disk
        ]
        self.flipFlop = False
        self.buffer = 0
        self.io_range = list(range(0x0, 0x10)) + list(range(0x81,0x84))

    def write(self, port: int, value: int):
        '''
        I/O Write handler for the DMA

        :param self: The DMA_8237 object
        :param port: The I/O port being written to
        :type port: int
        :param value: The data to store in the I/O port
        :type value: int
        '''
        if port < 0x08:
            channelNum = port // 2
            wordCnt = bool(port % 2) #True: Word count, False: Address
            
            channel = self.channels[channelNum]

            if self.flipFlop:
                val = (value << 8) | self.buffer #MSB
                if wordCnt:
                    channel.wordCount = val + 1
                else:
                    channel.address = val
            else:
                self.buffer = value #Store LSB temporarily
            
            self.flipFlop = not self.flipFlop
        else:
            match port:
                case 0x81:
                    self.channels[2].page = value
                case 0x82:
                    self.channels[3].page = value
                case 0x83:
                    self.channels[1].page = value
                case 0xA:
                    #Single channel mask
                    channel = value & 0b11
                    mask = (value & 0b100) >> 2
                    self.channels[channel].masked = bool(mask)
                case 0xB:
                    '''                                        
                    000B	w	DMA channel 0-3 mode register
                            bit 7-6 = 00  demand mode
                                = 01  single mode
                                = 10  block mode
                                = 11  cascade mode
                            bit 5	 = 0   address increment select
                                = 1   address decrement select
                            bit 3-2 = 00  verify operation
                                = 01  write to memory
                                = 10  read from memory
                                = 11  reserved
                            bit 1-0 = 00  channel 0 select
                                = 01  channel 1 select
                                = 10  channel 2 select
                                = 11  channel 3 select
                    '''
                    channel = value & 0b11
                    transferMode = (value & 0b1100) >> 2
                    reverse = bool((value & 0b100000) >> 5)
                    self.channels[channel].mode = transferMode
                    self.channels[channel].reverse = reverse
                case 0xC:
                    self.flipFlop = False
    def read(self, port: int) -> int:
        '''
        I/O Read handler for the DMA

        :param self: The DMA_8237 object
        :param port: The I/O port being read
        :type port: int
        :return: The data from the I/O port
        :rtype: int
        '''
        if port < 0x08:
            channelNum = port // 2
            wordCnt = bool(port % 2) #True: Word count, False: Address

            channel = self.channels[channelNum]

            self.flipFlop = not self.flipFlop

            if wordCnt:
                value = channel.wordCount - 1
            else:
                value = channel.address

            if not self.flipFlop:
                #print(f"DMA Read {port} FlipFlop {not self.flipFlop} : {(value & 0b1111111100000000) >> 8}")
                return (value & 0b1111111100000000) >> 8
            else:
                
                #print(f"DMA Read {port} FlipFlop {not self.flipFlop} : {(value & 0b0000000011111111)}")
                return (value & 0b0000000011111111)
        else:
            match port:
                case 0x8:
                    status = 0
                    if self.channels[0].tc: status |= CHANNEL_STATUS.CH0_TC
                    if self.channels[1].tc: status |= CHANNEL_STATUS.CH1_TC
                    if self.channels[2].tc: status |= CHANNEL_STATUS.CH2_TC
                    if self.channels[3].tc: status |= CHANNEL_STATUS.CH3_TC
                    if self.channels[0].requested: status |= CHANNEL_STATUS.CH0_REQ
                    if self.channels[1].requested: status |= CHANNEL_STATUS.CH1_REQ
                    if self.channels[2].requested: status |= CHANNEL_STATUS.CH2_REQ
                    if self.channels[3].requested: status |= CHANNEL_STATUS.CH3_REQ
                    return status
                case 0x81:
                    return self.channels[2].page
                case 0x82:
                    return self.channels[3].page
                case 0x83:
                    return self.channels[1].page
                case _:
                    print(f"Read DMA: {port}")
                    return 0
                
