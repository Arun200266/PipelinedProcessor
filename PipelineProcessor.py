# ---------------------------------------------------------------------------------------
"""                                  CS2610 ASSIGNMENT 8                              """

# Authors : A R Arun (CS19B002), Manishnantha M (CS19B031), Alan Joel J (CS19B077)
# Version : 1
# Created On : 25/4/21
# About File:
#       Python Script to simulate Pipelined Processor with iCache and dCache of size 256
#       bytes and 16 Registers. Statistics after executing program are stored in
#       "Output.txt" and "DCache.txt" reflects final state of dCache after the processor completes
#       execution.
# Note: We have assumed "ICache.txt", "DCache.txt", and "RF.txt"
#       files are present in an folder named "input"
# ---------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------
# Function Name : FourBitTwosComplement
# Args : x
# Returns : val
# Description : returns the 2s complement of x
# ---------------------------------------------------------------------------------------

def FourBitTwosComplement(x):
    val = x
    if x > 8:
        val = x - 16
    return val

# ---------------------------------------------------------------------------------------
# Function Name : GetHexVal
# Args : x
# Returns : val
# Description : converts hex char to the corresponding int
# ---------------------------------------------------------------------------------------

def GetHexVal(x):
    val = ord(x)
    if x.isdigit():
        val = val - ord('0')
    else:
        val = val - ord('a') + 10
    return val

# ---------------------------------------------------------------------------------------
# Function Name : GetHexChar
# Args : x
# Returns : ch
# Description : returns a corresponding hex character for x
# ---------------------------------------------------------------------------------------

def GetHexChar(x):
    if x < 10:
        ch = chr(x + ord('0'))
    else:
        ch = chr(x + ord('a') - 10)
    return ch

# ---------------------------------------------------------------------------------------
# Function Name : IntToHexStr
# Args : x
# Returns : <a hex string>
# Description : converts an integer to a Hex value represented in a string
# ---------------------------------------------------------------------------------------

def IntToHexStr(x):
    return GetHexChar(x // 16) + GetHexChar(x % 16)

# ---------------------------------------------------------------------------------------
# Function Name : TwosComplement
# Args : line
# Returns : val
# Description : Returns twos complement of the int corr. to the hex line
# ---------------------------------------------------------------------------------------

def TwosComplement(line):
    x = GetHexVal(line[0]) * 16 + GetHexVal(line[1])
    if x > 127:
        return x - 256
    else:
        return x

# ---------------------------------------------------------------------------------------
# Function Name : extract
# Args : instr
# Returns : [opcode, addr1, addr2, addr3]
# Description : from an instruction opcode destination address and source address are extracted and returned
# ---------------------------------------------------------------------------------------

def extract(instr):
    opcode = GetHexVal(instr[0])
    addr1 = GetHexVal(instr[1])
    addr2 = GetHexVal(instr[2])
    addr3 = GetHexVal(instr[3])
    return [opcode, addr1, addr2, addr3]

# ---------------------------------------------------------------------------------------
# Class Name : Processor
#
# Description : Models a processor which implements pipelining
# ---------------------------------------------------------------------------------------
class Processor:
    def __init__(self):
        # -----------------------------------------------------------------------------
        self.iCache = []
        self.dCache = []
        self.Register = []
        self.FILE_HANDLE()

        # REGISTERS -------------------------------------------------------------------
        self.PC = 0
        self.IR = None
        self.A = None
        self.B = None
        self.ALUOutput = None
        self.LMD = None
        self.tempReg = None
        self.L1 = None

        self.offset = None
        self.Cycle = 0
        self.preCycle = 0

        # FLAGS -----------------------------------------------------------------------
        self.halt = False
        self.RegFlag = [False] * 16
        self.StageFlags = [False] * 5
        self.StageFlags[0] = True
        self.stallFlag = False
        self.ctrlFlag = False

        # BUFFERS ---------------------------------------------------------------------
        self.StageID = []
        self.StageEX = []
        self.StageMEM = []
        self.StageWB = []

        # -----------------------------------------------------------------------------
        self.Code = {
            "ADD": 0, "SUB": 1, "MUL": 2, "INC": 3,
            "AND": 4, "OR": 5, "NOT": 6, "XOR": 7,
            "LOAD": 8, "STORE": 9, "JMP": 10, "BEQZ": 11,
            "HLT": 15
        }

        self.InstructionCount = {
            "ARIT": 0,
            "LOGC": 0,
            "DATA": 0,
            "CTRL": 0,
            "HALT": 0,
        }

        self.StallCount = {
            "RAW": 0,
            "CTRL": 0,
        }

    # -----------------------------------------------------------------------------
    # Function Name : FILE_HANDLE
    # Args : self
    # Returns : <none>
    # Description : To read from the given input files and extracting info
    # -----------------------------------------------------------------------------
    def FILE_HANDLE(self):
        # opening "ICache.txt" file
        f_inst = open("input/ICache.txt", "r+")
        while True:
            line = f_inst.readline()
            if not line:
                break
            # to remove the '\n' at the last
            line = line.strip()
            # store the contents of the file in iCache attribute of class
            self.iCache.append(line)
        f_inst.close()

        # opening "DCache.txt" file
        f_data = open("input/DCache.txt", "r+")
        while True:
            line = f_data.readline()
            if not line:
                break
            # to remove the '\n' at the last
            line = line.strip()
            x = TwosComplement(line)
            # store the contents of the file in dCache attribute of class
            self.dCache.append(x)
        f_data.close()

        # opening "RF.txt" file
        f_reg = open("input/RF.txt", "r+")
        while True:
            line = f_reg.readline()
            if not line:
                break
            # to remove the '\n' at the last
            line = line.strip()
            x = TwosComplement(line)
            # load the contents of the register file into the Register class attribute
            self.Register.append(x)
        f_reg.close()

    # -----------------------------------------------------------------------------
    # Function Name : instr_fetch
    # Args : self
    # Returns : <none>
    # Description : Function which performs instruction fetch
    # -----------------------------------------------------------------------------

    def instr_fetch(self):
        # Getting instruction using PC
        self.IR = self.iCache[self.PC][0:2] + self.iCache[self.PC + 1][0:2]
        self.PC += 2
        self.StageFlags[1] = True
        self.StageID = [self.IR]  # buffer update
        self.StageFlags[0] = not (self.IR[0] == 'f')  # HLT?
        return

    # -----------------------------------------------------------------------------
    # Function Name : instr_decode
    # Args : self
    # Returns : <none>
    # Description : Function which performs instruction decode
    # -----------------------------------------------------------------------------

    def instr_decode(self):
        self.StageFlags[1] = False
        self.IR = self.StageID[0]

        # retrieve from buffer
        [opcode, addr1, addr2, addr3] = extract(self.IR)

        TwoSrc = [self.Code["ADD"], self.Code["SUB"], self.Code["MUL"],
                  self.Code["XOR"], self.Code["OR"], self.Code["AND"]]
        # Decoding instruction based on opcode and checking register availability
        # i.e. RAW dependency
        if opcode in TwoSrc:
            self.tempReg = addr1
            if self.RegFlag[addr2] or self.RegFlag[addr3]:
                self.stallFlag = True
                self.StageFlags[1] = True
                self.StallCount["RAW"] += 1
            else:
                self.stallFlag = False
                self.A = self.Register[addr2]
                self.B = self.Register[addr3]
        elif opcode == self.Code["INC"]:
            self.tempReg = addr1
            if self.RegFlag[addr1]:
                self.stallFlag = True
                self.StageFlags[1] = True
                self.StallCount["RAW"] += 1
            else:
                self.stallFlag = False
                self.A = self.Register[addr1]
        elif opcode == self.Code["NOT"]:
            self.tempReg = addr1
            if self.RegFlag[addr2]:
                self.stallFlag = True
                self.StageFlags[1] = True
                self.StallCount["RAW"] += 1
            else:
                self.stallFlag = False
                self.A = self.Register[addr2]
        elif opcode == self.Code["LOAD"]:
            if self.RegFlag[addr2]:
                self.stallFlag = True
                self.StageFlags[1] = True
                self.StallCount["RAW"] += 1
            else:
                self.stallFlag = False
                self.tempReg = addr1
                self.A = self.Register[addr2]
                self.offset = addr3
        elif opcode == self.Code["STORE"]:
            if self.RegFlag[addr1] or self.RegFlag[addr2]:
                self.stallFlag = True
                self.StageFlags[1] = True
                self.StallCount["RAW"] += 1
            else:
                self.stallFlag = False
                self.tempReg = self.Register[addr1]
                self.A = self.Register[addr2]
                self.offset = addr3
        elif opcode == self.Code["JMP"]:
            self.L1 = TwosComplement(self.IR[1:3])
            self.stallFlag = True
            self.ctrlFlag = True
            # Stalling if there is a CTRL hazard
            self.StallCount["CTRL"] += 2
            self.preCycle = self.Cycle
        elif opcode == self.Code["BEQZ"]:
            if self.RegFlag[addr1]:
                self.stallFlag = True
                self.StageFlags[1] = True
                self.StallCount["RAW"] += 1
            else:
                self.tempReg = self.Register[addr1]
                self.L1 = TwosComplement(self.IR[2:4])
                self.stallFlag = True
                self.ctrlFlag = True
                self.StallCount["CTRL"] += 2
                self.preCycle = self.Cycle

        if not self.stallFlag or self.ctrlFlag:
            self.StageFlags[2] = True
            # buffer update
            self.StageEX = [opcode, self.tempReg, self.A, self.B, self.offset, self.L1]
        return

    # -----------------------------------------------------------------------------
    # Function Name : execute
    # Args : self
    # Returns : <none>
    # Description : To perform execute operation
    # -----------------------------------------------------------------------------

    def execute(self):
        self.StageFlags[2] = False
        [opcode, self.tempReg, self.A, self.B, self.offset, self.L1] = self.StageEX

        # Executing instruction based on opcode
        if opcode == self.Code["ADD"]:
            self.ALUOutput = self.A + self.B
            self.InstructionCount["ARIT"] += 1
            self.RegFlag[self.tempReg] = True

        if opcode == self.Code["SUB"]:
            self.ALUOutput = self.A - self.B
            self.InstructionCount["ARIT"] += 1
            self.RegFlag[self.tempReg] = True

        if opcode == self.Code["MUL"]:
            self.ALUOutput = self.A * self.B
            self.InstructionCount["ARIT"] += 1
            self.RegFlag[self.tempReg] = True

        if opcode == self.Code["INC"]:
            self.ALUOutput = self.A + 1
            self.InstructionCount["ARIT"] += 1
            self.RegFlag[self.tempReg] = True

        if opcode == self.Code["AND"]:
            self.ALUOutput = self.A & self.B
            self.InstructionCount["LOGC"] += 1
            self.RegFlag[self.tempReg] = True

        if opcode == self.Code["OR"]:
            self.ALUOutput = self.A | self.B
            self.InstructionCount["LOGC"] += 1
            self.RegFlag[self.tempReg] = True

        if opcode == self.Code["NOT"]:
            self.ALUOutput = 15 - self.A
            self.InstructionCount["LOGC"] += 1
            self.RegFlag[self.tempReg] = True

        if opcode == self.Code["XOR"]:
            self.ALUOutput = self.A ^ self.B
            self.InstructionCount["LOGC"] += 1
            self.RegFlag[self.tempReg] = True

        # Getting Offset for LOAD and STORE
        if opcode == self.Code["LOAD"] or opcode == self.Code["STORE"]:
            self.ALUOutput = self.A + FourBitTwosComplement(self.offset)
            self.InstructionCount["DATA"] += 1

        # Getting L1 for JMP and BEQZ
        if opcode == self.Code["JMP"]:
            self.ALUOutput = self.PC + (self.L1 << 1)
            self.PC = self.ALUOutput
            self.InstructionCount["CTRL"] += 1

        if opcode == self.Code["BEQZ"]:
            self.ALUOutput = self.PC + (self.L1 << 1)
            self.InstructionCount["CTRL"] += 1
            if self.tempReg == 0:
                self.PC = self.ALUOutput

        self.StageFlags[3] = True
        self.StageMEM = [opcode, self.tempReg, self.ALUOutput]
        return

    # -----------------------------------------------------------------------------
    # Function Name : mem_access
    # Args : self
    # Returns : <none>
    # Description : implements the memory access stage
    # -----------------------------------------------------------------------------

    def mem_access(self):
        self.StageFlags[3] = False
        # retrieve from buffer
        [opcode, self.tempReg, self.ALUOutput] = self.StageMEM

        # Gets value from DCache to LMD
        if opcode == self.Code["LOAD"]:
            self.LMD = self.dCache[self.ALUOutput]
        # Gets value from LMD and storing in DCache
        elif opcode == self.Code["STORE"]:
            self.dCache[self.ALUOutput] = self.tempReg

        self.StageFlags[4] = True
        # buffer update
        self.StageWB = [opcode, self.tempReg, self.ALUOutput, self.LMD]
        return

    # -----------------------------------------------------------------------------
    # Function Name : write_back
    # Args : self
    # Returns : <none>
    # Description : implements the write back stage
    # -----------------------------------------------------------------------------

    def write_back(self):
        self.StageFlags[4] = False
        # retrieve from buffer
        [opcode, self.tempReg, self.ALUOutput, self.LMD] = self.StageWB

        if opcode < 8:  # ALU
            self.Register[self.tempReg] = self.ALUOutput
            self.RegFlag[self.tempReg] = False
            # Setting Register free - RAW Dependency removed
        elif opcode == self.Code["LOAD"]:  # LOAD
            self.Register[self.tempReg] = self.LMD
            self.RegFlag[self.tempReg] = False
            # Setting Register free - RAW Dependency removed
        elif opcode == self.Code["HLT"]:  # HLT
            self.halt = True

        return

    # -----------------------------------------------------------------------------
    # Function Name : RestoreDCache
    # Args : self
    # Returns : <none>
    # Description : writing back into DCache.txt file from dCache attribute
    # -----------------------------------------------------------------------------

    def RestoreDCache(self):
        f_data = open("input/DCache.txt", "w+")
        for x in self.dCache:
            line = IntToHexStr(x % 256) + '\n'
            f_data.write(line)
        f_data.close()

    # -----------------------------------------------------------------------------
    # Function Name : Run
    # Args : self
    # Returns : <none>
    # Description : A simulation of Running the pipelined processor
    # -----------------------------------------------------------------------------

    def Run(self):
        # One loop iteration corresponds to one clock cycle
        while True:
            # We perform the steps in reverse order for convenience
            # (in reality all these processes will be done in parallel)
            if self.StageFlags[4]:
                self.write_back()
            if self.StageFlags[3]:
                self.mem_access()
            if self.StageFlags[2]:
                self.execute()
            if self.StageFlags[1]:
                self.instr_decode()
            if self.StageFlags[0] and not self.stallFlag:
                self.instr_fetch()

            # incrementing cycle count
            self.Cycle += 1


            if self.ctrlFlag and self.Cycle == self.preCycle + 2:
                self.stallFlag = self.ctrlFlag = False

            # Terminate if halt
            if self.halt:
                self.InstructionCount["HALT"] += 1
                break
        self.RestoreDCache()
        return

    # -----------------------------------------------------------------------------
    # Function Name : WriteStats
    # Args : self
    # Returns : <none>
    # Description : Functions to Write stats in Output.txt
    # -----------------------------------------------------------------------------

    def WriteStats(self):

        TotalInstructionCount = 0
        for key in self.InstructionCount:
            TotalInstructionCount += self.InstructionCount[key]

        TotalStallCount = self.StallCount["RAW"] + self.StallCount["CTRL"]

        CPI = self.Cycle / TotalInstructionCount

        f_out = open("Output.txt", "w")
        f_out.write("Total number of instructions executed      : " + str(TotalInstructionCount) + "\n")
        f_out.write("\nNumber of instructions in each class\n\n")
        f_out.write("Arithmetic instructions                    : " + str(self.InstructionCount["ARIT"]) + "\n")
        f_out.write("Logical instructions                       : " + str(self.InstructionCount["LOGC"]) + "\n")
        f_out.write("Data instructions                          : " + str(self.InstructionCount["DATA"]) + "\n")
        f_out.write("Control instructions                       : " + str(self.InstructionCount["CTRL"]) + "\n")
        f_out.write("Halt instructions                          : " + str(self.InstructionCount["HALT"]) + "\n")
        f_out.write("Cycles Per Instruction                     : %.5f\n" % (CPI))
        f_out.write("Total number of stalls                     : " + str(TotalStallCount) + "\n")
        f_out.write("Data stalls (RAW)                          : " + str(self.StallCount["RAW"]) + "\n")
        f_out.write("Control Stalls                             : " + str(self.StallCount["CTRL"]) + "\n")
        f_out.close()

# ---------------------------------------------------------------------------------------
# Function Name : main
# Args : <none>
# Returns : <none>
# Description : Main Function
# ---------------------------------------------------------------------------------------

def main():
    print("Simulating Processor ...")
    P = Processor()
    P.Run()
    P.WriteStats()


if __name__ == "__main__":
    main()

