'''
IBM PC Emulator Project - MorganPG

board.pc:

IBM PC 5150 Mainboard Emulation
'''
#Imports
from cpu.cpu_8088 import CPU_8088
from board.pit import PIT_8253, SIGNAL
from board.dma import DMA_8237
from board.pic import PIC_8259
from board.ppi import PPI_8255
from floppy.fdc import UPD765_FDC
from video.mda import MDA

from io_base.isa import ISABus
class PC():
    def __init__(self, romfile = "./cpu/pc_bios.bin") -> None:
        '''
        IBM PC Mainboard
        
        :param self: The PC Object
        :param romfile: The location of the 8KB BIOS file.
        '''
        
        self.pit = PIT_8253()
        self.pic = PIC_8259()
        self.ppi = PPI_8255()
        self.dma = DMA_8237()
        self.fdc = UPD765_FDC(self.dma.channels[2])
        self.cycles = 0
        '''Number of CPU Cycles executed (technically this is wrong, its the number of full instructions processed)'''

        self.isa =  ISABus()

        self.mda = MDA(self.ppi.keyboard)
        self.isa.addDevice(self.mda)

        self.cpu = CPU_8088(self.isa, romfile)
        self.cpu.addIODevices([
            self.pit,
            self.pic,
            self.ppi,
            self.dma,
            self.mda,
            self.fdc
        ])
    
    def run(self):
        '''
        The mainloop
        
        :param self: The PC Object
        '''
        #Force the Channel 0 gate to be always high
        self.pit.channels[0].setGate(True)

        #Mainloop
        while self.mda.running:
            #Update the PIT timers (definitely not accurate, but 4 times per mainloop seems to work best)
            for i in range(4):
                self.pit.update()   

            #Handle interrupts
            if self.pit.channels[0].irq:
                self.pic.raise_irq(0)
            
            self.pit.channels[0].irq = False
                
            if self.ppi.keyboard.irq:
                self.pic.raise_irq(1)
                self.ppi.keyboard.irq = False

            if self.cpu.interrupts_enabled():
                irq = self.pic.getActiveIRQ()
                if irq:    
                    self.cpu.call_int(irq)
            
            if self.cycles % 50000 == 0:
                self.mda.update()
            
            #Update the CPU and PPI
            self.cpu.step(1)
            self.ppi.update()
            self.cycles += 1
            
