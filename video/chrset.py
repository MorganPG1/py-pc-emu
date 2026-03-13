'''
IBM PC Emulator Project - MorganPG

video.chrset

IBM Character Set Decoder
'''
#Imports
from PIL import Image, ImageOps
import pygame

class CharsetDecoder():
    def __init__(self, charset:str) -> None:
        '''
        IBM Character Set Decoder

        :param self: CharsetDecoder object
        :param charset: Path to character set binary
        :type charset: str
        '''
        file = open(charset, "rb")
        self.charset = file.read()
        file.close()

        self.charList:list[Image.Image] = []
        self.pygameList:list[pygame.Surface] = []
        self.invCharList:list[Image.Image] = []
        self.invPygameList:list[pygame.Surface] = []
        
        for char in range(256):
            self.charList.append(self.getUncachedPILImage(char))
            self.pygameList.append(self.getUncachedPygameImage(char))

            self.invCharList.append(self.getUncachedPILImage(char, True))
            self.invPygameList.append(self.getUncachedPygameImage(char, True))
            
    def getUncachedPILImage(self, chr:int, inv:bool=False) -> Image.Image:
        '''
        Returns a PIL Image for the character index (DO NOT USE, USE getPILImage or getPygameImage, this is used internally during initialisation)

        :param self: CharsetDecoder object
        :param chr: The index of the character
        :param inv: Return an inverted copy of the image
        :type chr: int
        :type inv: bool
        :return: The PIL image of the character
        :rtype: Image
        '''

        #Initialise the image
        chrImg = Image.new("L", (9,14))
        
        #Iterate through scanlines
        for scanline in range(14):

            #Check if first or second bank should be used
            if scanline <= 7:
                addr = (chr*8) + scanline
            else:
                addr = 0x800 + (chr*8) + scanline-8

            #Iterate through bits
            for i in range(8):
                #Shift the line
                line = self.charset[addr] >> (7 - i)

                #Check the bit state
                bit = line & 1

                #Add the bit to the image
                chrImg.putpixel((i, scanline), bit*0xFF)

                #If last bit AND the character in the box drawing range, duplicate the last bit
                if i == 7 and chr >= 0xB0 and chr <= 0xDF:
                    chrImg.putpixel((8, scanline), bit*0xFF)
        
        if inv:
            return ImageOps.invert(chrImg)
        return chrImg
    
    def getPILImage(self, chr:int, inv:bool) -> Image.Image:
        '''
        Returns a PIL Image for the character index 

        :param self: CharsetDecoder object
        :param chr: The index of the character
        :param inv: Return an inverted copy of the image
        :type chr: int
        :type inv: bool
        :return: The PIL image of the character
        :rtype: Image
        '''
        if inv:
            return self.invCharList[chr]
        return self.charList[chr]
    
    
    def getUncachedPygameImage(self, chr:int, inv:bool=False) -> pygame.Surface:
        '''
        Returns a Pygame Image for the character index (DO NOT USE, USE getPILImage or getPygameImage, this is used internally during initialisation)

        :param self: CharsetDecoder object
        :param chr: The index of the character
        :param inv: Return an inverted copy of the image
        :type chr: int
        :type inv: bool
        :return: The Pygame image of the character
        :rtype: Surface
        '''
        pil_img = self.getPILImage(chr, inv).convert("RGB")
        size = pil_img.size
        data = pil_img.tobytes()

        return pygame.image.fromstring(data, size, "RGB")
    
    
    def getPygameImage(self, chr:int, inv:bool=False) -> pygame.Surface:
        '''
        Returns a Pygame Image for the character index

        :param self: CharsetDecoder object
        :param chr: The index of the character
        :param inv: Return an inverted copy of the image
        :type chr: int
        :type inv: bool
        :return: The Pygame image of the character
        :rtype: Surface
        '''
        if inv:
            return self.invPygameList[chr]
        return self.pygameList[chr]
