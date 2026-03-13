'''
IBM PC Emulator Project - MorganPG

video.mda

IBM MDA Video Emulation.
'''
#Imports
from io_base.isa import ISADevice
from io_base.io import IODevice
from board.ppi import Keyboard
from video.chrset import CharsetDecoder
import pygame

class MDA(ISADevice, IODevice):
    def __init__(self, keyboard:Keyboard, chrRom:str="./video/chrset.bin") -> None:
        '''
        IBM MDA Video Emulation

        :param self: The MDA Object
        :param keyboard: The keyboard for sending keypresses to the machine
        :type keyboard: Keyboard
        :param chrRom: The path to the character ROM
        :type chrRom: str
        '''
        #Initialise basic variables
        self.keyboard:Keyboard = keyboard
        self.io_range = range(0x3b0,0x3c0)
        self.mem_range = (0xB0000, 0xB1000)
        self.vram = bytearray(4096)
        self.chrset = CharsetDecoder(chrRom)
        self.updateNeeded = False
        self.running = True

        #Initialise pygame
        pygame.init()

        self.screen = pygame.display.set_mode((720,350))


    def readMem(self, addr: int) -> int:
        '''
        Returns the value stored at the memory address in VRAM

        :param self: The MDA object
        :param addr: The offset from the start of the memory range.
        :type addr: int
        :return: The data stored in the memory address
        :rtype: int
        '''
        
        return self.vram[addr]
    
    def writeMem(self, addr: int, value: int) -> None:
        '''
        Writes data to a memory address in VRAM

        :param self: The MDA object
        :param addr: The offset from the start of the memory range.
        :param value: The value to store in the memory address.
        :type addr: int
        :type value: int
        '''
        #print(f"WRITE TO VRAM! ADDR: {hex(addr)} VALUE: {hex(value)}")
        self.updateNeeded = True
        self.vram[addr] = value
    
    def update(self) -> None:
        '''
        Update the window used to display the framebuffer

        :param self: The MDA object
        '''
        if self.updateNeeded:
            tmp_surface = pygame.Surface((80*9, 25*14))
            for i in range(0, len(self.vram), 2): 
                char_code = self.vram[i]
                attr = self.vram[i+1]  # Attribute byte (currently unused)
                
                row = i // 160
                col = (i % 160) // 2
                isInverted = attr in [0x70, 0x78]
                img = self.chrset.getPygameImage(char_code, isInverted)
                
                #Should the image be rendered, or should it be ignored?
                if attr not in [0x00, 0x08, 0x80, 0x88] and (char_code not in [0x0,0x20] or isInverted):
                    tmp_surface.blit(img, (col * 9, row * 14))
                tmp_surface = pygame.transform.scale(tmp_surface, (self.screen.get_width(), self.screen.get_height()))
            self.screen.blit(tmp_surface, (0,0))
            pygame.display.flip()

        #Event logic
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key in self.keyboard.keymap:
                    key = self.keyboard.keymap[event.key]
                    self.keyboard.pressKey(key)
            if event.type == pygame.KEYUP:
                if event.key in self.keyboard.keymap:
                    key = self.keyboard.keymap[event.key]
                    self.keyboard.releaseKey(key)
