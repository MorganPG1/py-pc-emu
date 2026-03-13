'''
IBM PC Emulator Project - MorganPG

board.pit:

Intel 8253 PIT (Programmable Interval Timer) Emulation
Should be mapped into IO Ports 0x40-0x5F

Main source:https://osdev.wiki/wiki/Programmable_Interval_Timer
'''
#Imports
from io_base.io import IODevice
from typing import Annotated
from datetime import datetime 
#Flags
class MODE():

    ITC = 0 #Interrupt On Terminal Count
    HW_RT_OS = 1 #Hardware Re-triggerable One-shot
    RATE_GEN = 2 #Rate Generator
    SQR_WAVE = 3 #Square Wave
    SW_STROBE = 4 #Software Strobe
    HW_STROBE = 5 #Hardware Strobe

class ACCESS():
    LSB = 1 #Least Significant Byte
    MSB = 2 #Most Significant Byte
    BOTH = 3 #LSB/MSB

class CMD():
    NONE = 0
    LATCH = 1
    MODES = 2
    RELOAD = 3

class SIGNAL():
    LOW = 0
    HIGH = 1
    FALLING = 2
    RISING = 3

class PITChannel():
    def __init__(self) -> None:
        '''
        PIT Channel Implementation
        
        :param self: The PITChannel object
        '''
        #Booleans

        self.latched = False 
        '''The latch state of the PIT Channel'''

        self.flipFlop = False
        '''The internal state of the flipflop (for the ACCESS.BOTH mode)'''

        self.counting = False
        '''Used to determine if the value should be counting or not'''

        self.fired = False
        '''Used in Interrupt on Terminal Count to check if an IRQ has already been fired'''
        self.irq = False
        '''Is an IRQ active for this channel (only checked for channel one)'''

        #Digital I/O signals

        self.output:int = SIGNAL.LOW
        '''The output of the PIT Channel'''

        self.gate:int = SIGNAL.LOW
        '''The gate (input) of the PIT Channel'''

        #Integers

        self.tick:int = 0
        '''The tick (clock cycle) of the PIT from the start of execution'''

        self.latchVal:int = 0
        '''The current latched value'''

        self.current:int = 0
        '''The current value of the PIT Channel'''

        self.lastCMD:int = CMD.NONE
        '''The last command that was processed by the PIT Channel'''

        self.mode:int = 0
        '''The operating mode of the PIT Channel'''

        self.accessMode:int = 0
        '''The access mode of the PIT Channel'''

        self.tmp_LSB:int = 0
        '''A temporary value used to store the LSB in the ACCESS.BOTH mode'''

        self.reload:int = 0
        '''The value stored in the reload register'''

        self.ticksSinceGateChange:int = 0
        self.ticksSinceOutputChange:int = 0
    def getValue(self) -> int:
        '''
        Returns the current value in the PIT Channel, accounting for access mode logic 

        :param self: The PITChannel object
        :return: The value in the PIT Channel
        :rtype: int
        '''
        #Latch logic
        if self.latched:
            val = self.latchVal    
        else:
            val = self.current

        #Access mode logic
        match self.accessMode:
            case ACCESS.LSB: #Least Significant Byte only
                self.latched = False
                return (val & 0b0000000011111111) #LSB
            case ACCESS.MSB: #Most Significant Byte only
                self.latched = False
                return (val & 0b1111111100000000) >> 8 #MSB
            case _: #Default (both)
                self.flipFlop = not self.flipFlop

                #Handle switching between MSB and LSB
                if not self.flipFlop:
                    self.latched = False
                    return (val & 0b1111111100000000) >> 8 #MSB
                else:
                    return (val & 0b0000000011111111) #LSB
                
    def latch(self) -> None:
        '''
        Latches the current value

        :param self: The PITChannel object
        '''
        self.latched = True
        self.lastCMD = CMD.LATCH
        self.latchVal = self.current

    def modeSpecific(self, isZero:bool) -> None:
        '''
        Handles the mode specific logic.

        :param self: The PITChannel object
        :param isZero: If the value is 0
        :type isZero: bool
        '''
        #Handle mode specific update logic.

        match self.mode:
            case MODE.ITC:
                if self.gate in [SIGNAL.HIGH, SIGNAL.RISING] and self.current != 0:
                    self.counting = True 
                else:
                    self.counting = False
                #If zero, reset counter to 0xFFFF and set output to HIGH
                if self.current == 0 and not self.fired:
                    self.irq = True
                    self.setOutput(True)
                    self.fired = True
                if self.current == 0:
                    self.current = 0xFFFF
                    

                #If reload register set, clear the output
                if self.lastCMD == CMD.RELOAD:
                    self.setOutput(False)

            case MODE.HW_RT_OS:
                if self.gate == SIGNAL.RISING:
                    self.setOutput(False)
                    self.counting = True
                if isZero:
                    self.current = 0xFFFF
                    self.irq = True
                    self.setOutput(True)

            case MODE.RATE_GEN:
                if self.lastCMD == CMD.RELOAD:
                    self.counting = True
                if self.current-1 == 1:
                    
                    self.output = SIGNAL.LOW
                elif self.output == SIGNAL.LOW:
                    self.irq = True
                    self.output = SIGNAL.HIGH

                
                if isZero:
                    self.current = self.reload
            case MODE.SQR_WAVE:
                
                if (self.reload % 2) == 0:
                    halfway = self.reload // 2
                else:
                    halfway = (self.reload + 1) // 2

                
                if self.current-2 > (self.reload - halfway):
                    if self.output == SIGNAL.LOW:
                        self.irq = True
                        self.setOutput(True)
                    

                elif self.output in [SIGNAL.HIGH, SIGNAL.RISING]:
                    
                    self.setOutput(False)
                
                if isZero:
                    
                    self.current = self.reload

                if self.lastCMD == CMD.RELOAD:
                    self.output = SIGNAL.HIGH
                    self.counting = True

    def setReload(self, value:int) -> None:
        '''
        Changes the value in the reload register, accounting for access mode logic.

        :param self: The PITChannel object
        :param value: The value to set the reload register to
        :type value: int
        '''
        self.lastCMD = CMD.RELOAD

        #Access mode logic
        match self.accessMode:

            case ACCESS.LSB:
                #Only store Least Significant Byte
                self.current = value
                self.reload = value
                #print(f"[{datetime.now()}, PIT Clock: {self.tick}] (LSB ONLY) RELOAD SET TO {self.reload}, MODE SET TO: {self.mode}")
                self.counting = True
                self.irq = False
                self.output = SIGNAL.LOW
                self.fired = False
                if self.mode in [MODE.HW_RT_OS, MODE.RATE_GEN, MODE.SQR_WAVE]:
                    self.output = SIGNAL.HIGH
                    self.counting = False
                else:
                    self.output = SIGNAL.LOW
            case ACCESS.MSB:
                #Only store Most Significant Byte
                value <<= 8
                self.current = value
                self.reload = value
                #print(f"[{datetime.now()}, PIT Clock: {self.tick}] (MSB ONLY) RELOAD SET TO {self.reload}, MODE SET TO: {self.mode}")
                self.counting = True
                self.irq = False
                self.fired = False
                self.output = SIGNAL.LOW
                if self.mode in [MODE.HW_RT_OS, MODE.RATE_GEN, MODE.SQR_WAVE]:
                    self.output = SIGNAL.HIGH
                    self.counting = False
                else:
                    self.output = SIGNAL.LOW
            case _:
                #Flip the flipflop
                self.flipFlop = not self.flipFlop

                #Handle switching between MSB and LSB
                if not self.flipFlop: 
                    val = (value << 8) | self.tmp_LSB #MSB
                    if val != 0:
                        self.reload = val
                        self.current = val
                        
                    else:
                        self.reload = 0x10000
                        self.current = 0x10000
                    self.irq = False
                    self.fired = False
                    if self.mode in [MODE.HW_RT_OS, MODE.RATE_GEN, MODE.SQR_WAVE]:
                        self.output = SIGNAL.HIGH
                        self.counting = False
                    else:
                        self.output = SIGNAL.LOW


                    #print(f"[{datetime.now()}, PIT Clock: {self.tick}] (MSB/LSB) RELOAD SET TO {self.reload}, MODE SET TO: {self.mode}")
                else:
                    self.counting = False
                    self.tmp_LSB = value #LSB
            
    def setGate(self, gate:bool) -> None:
        '''
        Sets the gate signal

        :param self: The PITChannel object
        :param gate: The state to set the gate to
        :type gate: bool
        '''
        self.ticksSinceOutputChange = 0
        match self.gate:
            case SIGNAL.LOW:
                self.gate = SIGNAL.RISING if gate else SIGNAL.LOW
            case SIGNAL.HIGH:
                self.gate = SIGNAL.HIGH if gate else SIGNAL.FALLING
            case SIGNAL.RISING:
                self.gate = SIGNAL.HIGH if gate else SIGNAL.LOW
            case SIGNAL.FALLING:
                self.gate = SIGNAL.RISING if gate else SIGNAL.LOW

    def setOutput(self, output:bool) -> None:
        '''
        Sets the output signal

        :param self: The PITChannel object
        :param output: The state to set the output to
        :type output: bool
        '''
        self.ticksSinceOutputChange = 0
        match self.output:
            case SIGNAL.LOW:
                self.output = SIGNAL.RISING if output else SIGNAL.LOW
            case SIGNAL.HIGH:
                self.output = SIGNAL.HIGH if output else SIGNAL.FALLING
            case SIGNAL.RISING:
                self.output = SIGNAL.HIGH if output else SIGNAL.LOW
            case SIGNAL.FALLING:
                self.output = SIGNAL.RISING if output else SIGNAL.LOW
        
        
    def setMode(self, mode:int) -> None:
        '''
        Changes the operating mode for the channel

        :param self: The PITChannel object
        :param mode: The operating mode to set it to
        :type mode: int
        '''
        self.mode = mode
        match mode:
            case MODE.ITC:
                self.setOutput(False)
            
        self.flipFlop = False

    def setAccess(self, access:int) -> None:
        '''
        Changes the access mode for the channel.

        :param self: The PITChannel object
        :param access: The access mode to set it to
        :type access: int
        '''
        self.accessMode = access
        self.flipFlop = False

    def update(self) -> None:
        '''
        Updates the PITChannel.

        :param self: The PITChannel object
        '''
        #Update logic
        prev = self.current
        self.modeSpecific(self.current <= 0)
        if prev == self.current:
            if self.counting:
                match self.mode:
                    case MODE.SQR_WAVE:
                        self.current -= 2
                    case _:
                        self.current -= 1
                
        if self.current < 0:
            self.current = self.reload

        
        
        #Update digital signals
        if self.ticksSinceGateChange == 1:
            match self.gate:
                case SIGNAL.RISING:
                    self.gate = SIGNAL.HIGH
                case SIGNAL.FALLING:
                    self.gate = SIGNAL.LOW
        if self.ticksSinceOutputChange == 1:
            match self.output:
                case SIGNAL.RISING:
                    self.output = SIGNAL.HIGH
                case SIGNAL.FALLING:
                    self.output = SIGNAL.LOW

        #Clear command
        self.lastCMD = CMD.NONE
        self.lastIrq = self.irq
        self.tick += 1
        self.ticksSinceGateChange += 1
        self.ticksSinceOutputChange += 1
class PIT_8253(IODevice):
    '''
    Intel 8253 PIT (Programmable Interval Timer) Emulation
    '''
    def __init__(self) -> None:
        '''
        Intel 8253 PIT (Programmable Interval Timer) Emulation

        :param self: The PIT_8253 object
        '''
        #Define the IO Ports needed to be binded
        self.io_range = range(0x40, 0x60)

        self.channels:list[PITChannel] = [
            PITChannel(),
            PITChannel(),
            PITChannel(),
        ]
        '''A list containing all 3 PIT Channels'''
    
    def read(self, port: int) -> int:
        '''
        The I/O Device read handler for the PIT

        :param self: The PIT_8253 object
        :param port: The I/O port being read from
        :type port: int
        :return: The data from the I/O port
        :rtype: int
        '''
        channelNum = port - 0x40
        if channelNum < 3:
            channel = self.channels[channelNum]
            return channel.getValue()
        else:
            return 0
        
    def write(self, port: int, value: int):
        '''
        The I/O Device write handler for the PIT

        :param self: The PIT_8253 object
        :param port: The I/O port being written to
        :type port: int
        :param value: The data to store in the I/O port
        :type value: int
        '''
        channelNum = port - 0x40
        if channelNum < 3:
            # print(f"RELOAD FOR CHANNEL {channelNum} SET TO {hex(value)}")
            channel = self.channels[channelNum]
            channel.setReload(value)
        else:
            
            channelNum = (value & 0b11000000) >> 6 #Use bitmask to get the channel
            accessMode = (value & 0b00110000) >> 4 #Use bitmask to get the access mode
            operatingMode = (value & 0b00001110) >> 1 #Use bitmask to get the operating mode
            #print(f"CONFIG FOR CHANNEL {channelNum} CHANGED!")
            if channelNum < 3:
                channel = self.channels[channelNum]
                if accessMode == 0:
                    channel.latch()
                else:
                    channel.setAccess(accessMode)
                    channel.setMode(operatingMode)
    
    def update(self):
        '''
        Updates the PIT Channels

        :param self: The PIT_8253 object
        '''
        for channel in self.channels:
            channel.update()
        self.channels[1].irq = False
        self.channels[2].irq = False
        # if self.channels[0].irq:
            #print(f"[{datetime.now()}, PIT Clock: {self.channels[0].tick}] IRQ CALLED")