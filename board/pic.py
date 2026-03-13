'''
IBM PC Emulator Project - MorganPG

board.pic:

Intel 8259 PIC (Programmable Interrupt Controller) Emulation
Should be mapped into IO Ports 0x20 and 0x21

Main source: https://osdev.wiki/wiki/8259_PIC
Other sources:
https://davmac.org/osdev/pchwpe/i8259.html
https://github.com/86Box/86Box/blob/master/src/pic.c
'''
#Imports
from io_base.io import IODevice

class PIC_8259(IODevice):
    '''
    Intel 8259 PIC (Programmable Interrupt Controller) Emulation
    '''
    def __init__(self) -> None:
        '''
        Intel 8259 PIC (Programmable Interrupt Controller) Emulation

        :param self: The PIC_8259 object
        '''
        self.io_range = [0x20, 0x21]
        
        self.irr = 0 
        '''Interrupt Request Register'''

        self.isr = 0
        '''In-Service Register'''

        self.imr = 0xff #Interrupt Mask Register
        '''Interrupt Mask Register'''

        self.vector_base = 0
        '''The base value used to calculate the CPU Interrupt value (IRQ + vector_base = CPU Interrupt Value)'''

        self.icw4 = False
        '''Is initialisation stage 4 expected'''

        self.icw3 = False
        '''Is initialisation stage 3 expected'''

        self.init_step = -1
        '''The current initialisation stage'''

        self.isr_read = False
        '''Should a read to 0x20 return the ISR?'''
    def mask_lowest_active(self, val:int) -> tuple[int,int]:
        '''
        Provides the bitmask and IRQ number of the highest priority interrupt

        :param self: Description
        :param val: Any interrupt register (should be masked with IMR first though if it is the IRR)
        :type val: int
        :return: Bitmask, IRQ Number
        :rtype: tuple[int, int]
        '''
        for i in range(8):
            mask = 1 << i
            if val & mask != 0:
                return ~mask, i
        return 0b11111111, -1
    
    def write(self, port: int, value: int):
        '''
        I/O Write handler for the PIC

        :param self: The PIC_8259 object
        :param port: The I/O port being written to
        :type port: int
        :param value: The data to store in the I/O port
        :type value: int
        '''
        if port == 0x20:
            if value & 0b00010000:
                self.irr = 0
                self.isr = 0
                self.init_step = 1
                self.icw3 = not bool(value & 2)
                self.icw4 = bool(value & 1)
            elif value == 0x20:
                mask, irq = self.mask_lowest_active(self.isr)
                if irq != -1:
                    self.isr &= ~(1 << irq)
                return
            elif (value & 0x18) == 0x8:
                if value & 0x2:
                    self.isr_read = True
                else:
                    self.isr_read = False
        elif port == 0x21:
            match self.init_step:
                case 0:
                    self.imr = value
                case 1:
                    value &= 0b11111000
                    self.vector_base = value
                    if self.icw3:
                        self.init_step += 1
                    else:
                        self.init_step = 3 if self.icw4 else 0
                    return
                case 2:
                    self.init_step += 1
                    return
                case 3:
                    self.init_step = 0
                    self.isr = 0
                    self.irr = 0
                    return
    
    def read(self, port: int) -> int:
        '''
        I/O Read handler for the PIC

        :param self: The PIC_8259 object
        :param port: The I/O port being read
        :type port: int
        :return: The data from the I/O port
        :rtype: int
        '''
        if port == 0x20:
            if self.isr_read:
                return self.isr
            else:
                return self.irr
        else:
            return self.imr
        
    def raise_irq(self,irq:int):
        '''
        Raise an IRQ (add it to the IRR to be processed)

        :param self: The PIC_8259 object
        :param irq: Description
        :type irq: int
        '''
        if self.init_step == 0 and ((1 << irq) & self.imr == 0):
            self.irr |= (0b00000001 << irq) 
    
    def getActiveIRQ(self) -> int|None:
        '''
        Returns the active interrupt and converts it to a CPU Interrupt number (eg: INT 10h)

        :param self: The PIC_8259 object
        :return: Either the active IRQ, or None if there is no IRQs unmasked and active
        :rtype: int | None
        '''
        
        waiting = self.irr & ~self.imr
        if not bool(waiting):
            return
        else:
            mask, irq = self.mask_lowest_active(waiting)
            _, irq2 = self.mask_lowest_active(self.isr)
            if irq2 != -1 and irq2 >= irq:
                return
            self.irr &= mask
            self.isr |= (1 << irq)

            return irq + self.vector_base