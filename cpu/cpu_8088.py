'''
IBM PC Emulator Project - MorganPG

cpu.cpu_8088:

Intel 8088 CPU Emulation
Handles I/O Ports and Memory mapping
'''

#Ignore the pyright comments, VS Code keeps saying that I can't use wildcards in imports and adding that shuts it up.
from unicorn import * # pyright: ignore[reportWildcardImportFromLibrary]
from unicorn.x86_const import * # pyright: ignore[reportWildcardImportFromLibrary]

#Try to import capstone to decompile the code in case of errors, it is not needed though
try:
    from capstone import * # pyright: ignore[reportWildcardImportFromLibrary]
    capstone_imported = True
except ImportError:
    capstone_imported = False

from cpu.cpu import CPU
from io_base.io import IODevice
from io_base.isa import ISABus
from datetime import datetime

if capstone_imported:
    md = Cs(CS_ARCH_X86, CS_MODE_16)

class CPU_8088(CPU):
    '''
    Intel 8088 CPU Emulation
    '''

    #Hooks:
    def int_hook(self, uc, intno, user_data):
        
        self.call_int(intno)
    def io_hook(self, uc, port, size, value, user_data=None):
        if port in self.io_mappings:
            ioDev = self.io_mappings[port]
        else:
            ioDev = None

        if value == None: #Read request

            if ioDev:
                return ioDev.read(port)
            else:
                #print(f"READ FROM UNKNOWN I/O PORT {hex(port)}")
                return 0xFF
            
        else: #Write request

            if ioDev:
                return ioDev.write(port, value)
            else:
                #print(f"WRITE {hex(value)} TO UNKNOWN I/O PORT {hex(port)}")
                return 0
    def rom_hook(self, uc, access, addr, size, value:int, user_data):
        return True
    def isa_hook(self, uc, access, addr, size, value:int, user_data):
        if value != None:
            if value > 255:
                val = value.to_bytes(2, "little")
                self.isa.write(addr, val[0])
                self.isa.write(addr+1, val[1])
            else:
                self.isa.write(addr, value)

    
    #Main class functions
    def __init__(self, isa:ISABus=ISABus(), bios_file:str="./cpu/pc_bios.bin") -> None:
        '''
        Intel 8088 CPU Emulation

        :param self: The CPU Object
        :param bios_file: The location of the BIOS File
        :type bios_file: str
        '''
        self.isa = isa
        self.vram = bytearray(4096)

        #Initialise IO Port Mappings
        self.io_mappings:dict[int, IODevice] = {}

        #Initialise the Unicorn Engine
        self.mu = Uc(UC_ARCH_X86, UC_MODE_16)

        #Map RAM
        self.mu.mem_map(0,0x10000) 

        #Map unused ram as read only
        self.mu.mem_map(0x10000,0x90000, UC_PROT_READ)
        
        #Map Video RAM
        self.mu.mem_map(0xA0000,0x20000) 

        #Map IO
        self.mu.mem_map(0xC0000,0x30000) 

        #Map ROM
        self.mu.mem_map(0xF0000, 0x10000, UC_PROT_READ | UC_PROT_EXEC)
        #self.mu.mem_map(0xFE000, 0x10000)
        

        #Initialise Registers
        self.mu.reg_write(UC_X86_REG_CS, 0xFFFF)
        self.mu.reg_write(UC_X86_REG_IP, 0x0000)
        self.mu.reg_write(UC_X86_REG_SS, 0x0000) 
        self.mu.reg_write(UC_X86_REG_SP, 0x7FF0)
        self.mu.reg_write(UC_X86_REG_DS, 0x0000)
        
        #Load BIOS Rom into memory
        f = open(bios_file, "rb")
        data = f.read()
        self.mu.mem_write(0xFE000, data)
        self.mu.mem_write(0x10000, bytes([0xFF]*0x90000))

        #Set up IO Hooks
        self.mu.hook_add(UC_HOOK_INSN, self.io_hook, None, 1, 0, UC_X86_INS_IN)
        self.mu.hook_add(UC_HOOK_INSN, self.io_hook, None, 1, 0, UC_X86_INS_OUT)
        self.mu.hook_add(UC_HOOK_INTR, self.int_hook)
        self.mu.hook_add(UC_HOOK_MEM_WRITE, self.isa_hook, begin=0xA0000, end=0xEFFF)
        self.mu.hook_add(UC_HOOK_MEM_WRITE_PROT, self.rom_hook)
        print("CPU INITIALISED")

    def step(self, count: int=1):
        '''
        Steps the CPU Forward

        :param self: The CPU Object
        :param count: The number of instructions to execute.
        :type count: int
        '''
        
        
        #Get IP and CS for debugging
        ip = self.mu.reg_read(UC_X86_REG_IP)
        cs = self.mu.reg_read(UC_X86_REG_CS)
        if isinstance(ip, int) and isinstance(cs, int): #Type checking
            
            pc = (cs * 16) + ip #Calculate physical address

            #print(hex(pc)) #Log for debugging

            try:
                self.mu.emu_start(pc, -1, count=count)
            except UcError as e:
                #Disassemble the code relating to the error
                code = self.mu.mem_read(pc-10, 50)

                ss = self.mu.reg_read(UC_X86_REG_SS)
                sp = self.mu.reg_read(UC_X86_REG_SP)
                ds = self.mu.reg_read(UC_X86_REG_DS)
                cs = self.mu.reg_read(UC_X86_REG_CS)
                bx = self.mu.reg_read(UC_X86_REG_BX)
                es = self.mu.reg_read(UC_X86_REG_ES)
                
                print(f"SS: {hex(ss)} SP: {hex(sp)} CS: {hex(cs)} DS: {hex(ds)} ES:{hex(es)} BX:{hex(bx)} PC: {hex(pc)}")
                
                #data = self.mu.mem_read(0, 1024*1024)
                #f = open("memory.bin", "wb")
                #f.write(data)
                #f.close()
                
                #If capstone is available, disassemble the last couple instructions to assist with debugging.
                if capstone_imported:
                    for insn in md.disasm(code, pc-10):
                        print(f"0x{insn.address:x}:\t{insn.mnemonic}\t{insn.op_str}")
                        if insn.address == pc:
                            break

                raise e
    
    def bindIOPorts(self, ports: list[int], ioDevice:IODevice):
        '''
        Binds a list of I/O Ports to the I/O device (note: you should probably be using addIODevice)
        
        :param self: CPU Object
        :param ports: A list of the I/O Ports to bind to the I/O device
        :type ports: list[int]
        :param ioDevice: The I/O Device to bind to the ports
        :type ioDevice: IODevice
        '''
        for port in ports:
            self.io_mappings[port] = ioDevice

    def addIODevice(self, ioDevice:IODevice):
        '''
        Adds an I/O device to the CPU's I/O.

        :param self: The CPU Object
        :param ioDevice: The I/O Device to add.
        :type ioDevice: IODevice
        '''
        self.bindIOPorts(list(ioDevice.io_range), ioDevice)
    
    def addIODevices(self, ioDevices:list[IODevice]):
        '''
        The same as addIODevice except it adds a list of IODevices

        :param self: The CPU Object
        :param ioDevices: A list of I/O Devices to add.
        :type ioDevices: list[IODevice]
        '''
        for dev in ioDevices:
            self.addIODevice(dev)
    def call_int(self, interrupt: int):
        '''
        Calls an interrupt
        
        :param self: The CPU Object
        :param interrupt: The interrupt to call
        :type interrupt: int
        '''
        
        # Get contents of registers
        sp = self.mu.reg_read(UC_X86_REG_SP)
        ss  = self.mu.reg_read(UC_X86_REG_SS)
        cs  = self.mu.reg_read(UC_X86_REG_CS)
        ip  = self.mu.reg_read(UC_X86_REG_IP)
        flags = self.mu.reg_read(UC_X86_REG_EFLAGS)
        
        # Calculate the stack offsets
        sp_flags = (sp - 2) & 0xFFFF
        sp_cs    = (sp_flags - 2) & 0xFFFF
        sp_ip    = (sp_cs - 2) & 0xFFFF

        # Push FLAGS to stack
        self.mu.mem_write((ss << 4) + sp_flags, flags.to_bytes(2, 'little'))
        # Push CS (code segment) to stack
        self.mu.mem_write((ss << 4) + sp_cs, cs.to_bytes(2, 'little'))
        # Push IP (instruction pointer) to stack
        self.mu.mem_write((ss << 4) + sp_ip, ip.to_bytes(2, 'little'))

        # Update the stack pointer
        self.mu.reg_write(UC_X86_REG_SP, sp_ip)

        # Get the interrupt handler from the IVT (interrupt vector table)
        int_addr = interrupt * 4
        ip_bytes = self.mu.mem_read(int_addr, 2)
        cs_bytes = self.mu.mem_read(int_addr + 2, 2)
        
        # Convert to int
        handler_ip = int.from_bytes(ip_bytes, 'little')
        handler_cs = int.from_bytes(cs_bytes, 'little')

        # Jump to the interrupt handler
        self.mu.reg_write(UC_X86_REG_CS, handler_cs)
        self.mu.reg_write(UC_X86_REG_IP, handler_ip)

        #Clear the interrupt flag
        new_flags = flags & ~0x0200
        self.mu.reg_write(UC_X86_REG_EFLAGS, new_flags)

    def interrupts_enabled(self) -> bool:
        '''
        Checks if the Interrupt Flag (IF) is set in EFLAGS.
        '''
        eflags = self.mu.reg_read(UC_X86_REG_EFLAGS)
        return (eflags & 0x200) != 0
