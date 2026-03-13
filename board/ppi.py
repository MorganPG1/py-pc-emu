'''
IBM PC Emulator Project - MorganPG

board.ppi:

Intel 8255 PPI (Programmable Peripheral Interface) Emulation
Should be mapped into IO Ports 0x60-0x63
'''

from io_base.io import IODevice
import pygame


class Keyboard():

    keymap = {
        pygame.K_F1: 0x3B,
        pygame.K_F2: 0x3C,
        pygame.K_F3: 0x3D,
        pygame.K_F4: 0x3E,
        pygame.K_F5: 0x3F,
        pygame.K_F6: 0x40,
        pygame.K_F7: 0x41,
        pygame.K_F8: 0x42,
        pygame.K_F9: 0x43,
        pygame.K_F10: 0x44,
        pygame.K_ESCAPE: 0x01,
        pygame.K_1: 0x02,
        pygame.K_2: 0x03,
        pygame.K_3: 0x04,
        pygame.K_4: 0x05,
        pygame.K_5: 0x06,
        pygame.K_6: 0x07,
        pygame.K_7: 0x08,
        pygame.K_8: 0x09,
        pygame.K_9: 0x0A,
        pygame.K_0: 0x0B,
        pygame.K_MINUS:0x0C,
        pygame.K_EQUALS:0x0D,
        pygame.K_BACKSPACE:0x0E,
        pygame.K_TAB:0x0F,
        pygame.K_q:0x10,
        pygame.K_w:0x11,
        pygame.K_e:0x12,
        pygame.K_r:0x13,
        pygame.K_t:0x14,
        pygame.K_y:0x15,
        pygame.K_u:0x16,
        pygame.K_i:0x17,
        pygame.K_o:0x18,
        pygame.K_p:0x19,
        pygame.K_LEFTBRACKET:0x1A,
        pygame.K_RIGHTBRACKET:0x1B,
        pygame.K_RETURN:0x1C,
        pygame.K_LCTRL:0x1D,
        pygame.K_a:0x1E,
        pygame.K_s:0x1F,
        pygame.K_d:0x20,
        pygame.K_f:0x21,
        pygame.K_g:0x22,
        pygame.K_h:0x23,
        pygame.K_j:0x24,
        pygame.K_k:0x25,
        pygame.K_l:0x26,
        pygame.K_SEMICOLON:0x27,
        pygame.K_QUOTE:0x28,
        pygame.K_HASH:0x29,
        pygame.K_LSHIFT:0x2A,
        pygame.K_BACKSLASH:0x2B,
        pygame.K_z:0x2C,
        pygame.K_x:0x2D,
        pygame.K_c:0x2E,
        pygame.K_v:0x2F,
        pygame.K_b:0x30,
        pygame.K_n:0x31,
        pygame.K_m:0x32,
        pygame.K_COMMA:0x33,
        pygame.K_PERIOD:0x34,
        pygame.K_SLASH:0X35,
        pygame.K_RSHIFT:0x36,
        pygame.K_SPACE:0x39
        
    }
    def __init__(self):
        self.irq = False
        self.enabled = False
        self.clock = 0
        self.clockTicking = True
        self.clockInhibitTicks = 0
        self.delay = 0
        self.latch = 0x00
    def pressKey(self, keyCode:int):
        self.latch = keyCode | 0x80
        self.irq = True
    def releaseKey(self, keyCode:int):
        self.latch = keyCode
        self.irq = True

class PPI_8255(IODevice):
    '''
    PPI Emulation
    '''
    def __init__(self) -> None:
        '''
        PPI Emulation (for now this is pretty much just a stub)
        
        :param self: The PPI_8255 object
        '''
        self.port_a = 0
        self.port_b = 0
        self.port_c = 0
        self.keyboard = Keyboard()
        self.io_range = range(0x60,0x64)
        self.tick = 0
    def write(self, port: int, value: int):
        '''
        I/O Write handler for the PPI

        :param self: The PPI_8255 object
        :param port: The I/O port being written to
        :type port: int
        :param value: The data to store in the I/O port
        :type value: int
        '''
        if port != 0x63:
            print(f"WRITE {hex(value)} TO PORT {port-0x5F}")
        match port:
            case 0x60:
                self.port_a = value
            case 0x61:
                if (value & 0x40) != 0:
                    self.keyboard.clockTicking = True
                else:
                    self.keyboard.clockTicking = False
                
                if (value & 0x80) != 0:
                    self.keyboard.enabled = False
                else:
                    self.keyboard.enabled = True
                self.port_b = value
            case 0x62:
                self.port_c = value
    
    def read(self, port: int) -> int:
        '''
        I/O Read handler for the PPI

        :param self: The PPI_8255 object
        :param port: The I/O port being read
        :type port: int
        :return: The data from the I/O port
        :rtype: int
        '''
        match port:
            case 0x60:
                if self.port_b & 0x80:
                    #return 0b0
                    #return 0b10111100
                    return 0b00111101
                else:
                    data = self.keyboard.latch
                    self.keyboard.latch = 0
                    self.keyboard.irq = False
                    return data
            case 0x61:
                return 0 | (self.keyboard.clock << 6)
            
            case 0x62:
                if (self.port_b & 0b100) >> 2:
                    return 0b0000
                else:
                    return 0b0
            case _:
                return 0
    def update(self) -> None:
        if self.tick == 50 and self.keyboard.enabled:
            print("KEYBOARD INIT")
            self.keyboard.latch = 0xAA
            self.keyboard.irq = True
        if self.keyboard.clockTicking:
            self.keyboard.clock = 0 if self.keyboard.clock else 1
            self.tick += 1
            self.keyboard.clockInhibitTicks = 0
        else:
            self.keyboard.clock = 0
            self.tick = 0
            self.keyboard.clockInhibitTicks += 1
        