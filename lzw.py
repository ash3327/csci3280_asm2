import os
import sys
import argparse
import random
from os.path import join, isabs, isfile, exists, isdir, basename, dirname

CODE_SIZE = 12
DICT_LIMIT = EOF = 4095 # 2**12-1

'''
    Parse command line arguments
'''
def parse_args():
    parser = argparse.ArgumentParser(description='Compress or decompress files using LZW algorithm')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-c', dest='c', type=str, help='Output file of compressed data')
    parser.add_argument('-o', type=str, default=join('.', 'output'), help='Output directory')
    parser.add_argument('input_files', type=str, nargs='*', help='Input files to be compressed')
    group.add_argument('-d', dest='d', type=str, help='Input file to be decompressed')
    return parser.parse_args(), parser.print_help

'''
    *Custom class for LZW_enhancement to override.
    Supposed to be an abstract class or interface, but the library 'abc' is not usable according to guidelines
'''
class BaseLZWWriter:
    '''
        IMPORTANT: MUST CALL initialize() AT START WITHIN ANY FUNCTIONALITY IMPLEMENTATION TO RESET SEED.\n
        ELSE ENCRYPTION AND DECRYPTION MAY GO WRONG.
    '''
    def set_code_size(self, code_size: int):
        self.code_size = code_size

    def initialize(self):'''Reset internal state\n\nIMPORTANT: MUST CALL THIS FUNCTION AT START WITHIN ANY FUNCTIONALITY IMPLEMENTATION TO RESET SEED\nELSE ENCRYPTION AND DECRYPTION MAY GO WRONG.'''

    def read_code(self)->int|None:'''Read a code of size CODE_SIZE from the input file\nReturn None if the end of file is reached'''

    def write_code(self, code):'''Write a code of size CODE_SIZE to the output file\nRemember to write extra bits to flush the buffer after you have written all the codes'''

    def read_file_header(self)->list:'''Read the file header and return the list of file stored in the compressed file'''

    def write_file_header(self, input_file_names):'''Write the file header to the compressed file containing names of the files'''
    
class LZWWriter(BaseLZWWriter):
    def __init__(self, file, code_size=CODE_SIZE):
        self.file = file
        self.name = file.name
        self.code_size = code_size

    '''
        Reset internal state
    '''
    def initialize(self):
        pass

    '''
        Read a code of size CODE_SIZE from the input file
        Return None if the end of file is reached
    '''
    def read_code(self):
        read_code = self
        input_file = self.file

        # skeleton code:
        if not hasattr(read_code, 'buffer'):
            read_code.buffer = 0
            read_code.buffer_bit_count = 0
        while read_code.buffer_bit_count < self.code_size:
            input_byte = input_file.read(1)
            if input_byte == b'':
                return None
            read_code.buffer <<= 8
            read_code.buffer |= int.from_bytes(input_byte, 'big')
            read_code.buffer_bit_count += 8
        read_code.buffer_bit_count -= self.code_size
        code = read_code.buffer >> read_code.buffer_bit_count
        read_code.buffer &= (1 << read_code.buffer_bit_count) - 1

        return code

    '''
        Write a code of size CODE_SIZE to the output file
        Remember to write extra bits to flush the buffer after you have written all the codes
    '''
    def write_code(self, code):
        write_code = self
        output_file = self.file

        # skeleton code:
        if not hasattr(write_code, 'buffer'):
            write_code.buffer = 0
            write_code.buffer_bit_count = 0
        write_code.buffer <<= self.code_size
        write_code.buffer |= code
        write_code.buffer_bit_count += self.code_size
        while write_code.buffer_bit_count >= 8:
            write_code.buffer_bit_count -= 8
            output_byte = (write_code.buffer >> write_code.buffer_bit_count)
            output_byte &= 0xFF
            output_file.write(output_byte.to_bytes(1, 'big'))
            write_code.buffer &= (1 << write_code.buffer_bit_count) - 1
        return

    '''
        Read the file header and return the list of file stored in the compressed file
    '''
    def read_file_header(self):
        input_file = self.file

        # skeleton code:
        output_file_names = []
        while True:
            line = input_file.readline()
            if line == b'' or line == b'\n':
                break
            output_file_names.append(line.decode('utf-8').strip())
        return output_file_names

    '''
        Write the file header to the compressed file containing names of the files
    '''
    def write_file_header(self, input_file_names):
        output_file = self.file

        # skeleton code:
        for input_file_name in input_file_names:
            output_file.write(input_file_name.encode('utf-8') + b'\n')
        output_file.write(b'\n')
        return
    
'''
    *Open file for writing
'''
class FilesWriter:
    def __init__(self, file_names):
        self.i = -1
        self.file_names = file_names
        self.file_name = None
        self.buffer_writer = None

    def open(self, i):
        if i >= len(self.file_names):
            return
        self.i = i
        self.file_name = self.file_names[i]
        if self.buffer_writer and not self.buffer_writer.closed:
            self.buffer_writer.close()
        self.buffer_writer = open(self.file_name, 'wb')
        print(f"\tDeompressing {self.file_name} ...")

    def write(self, i, val):
        if self.i != i:
            self.open(i)
        self.buffer_writer.write(val)

    def close(self):
        self.i = -1
        self.file_name = None
        if self.buffer_writer and not self.buffer_writer.closed:
            self.buffer_writer.close()
        self.buffer_writer = None

'''
    *Reinitialize the dictionary.
'''
class LZWDict:
    
    def init_dict_comp(self, DICT:dict)->dict:
        DICT.clear()
        DICT.update({bytes([v]): v for v in range(256)})
        return DICT

    def init_dict_decomp(self, DICT:dict)->dict:
        DICT.clear()
        DICT.update({v: bytes([v]) for v in range(256)})
        return DICT

    def update_dict_comp(self, DICT:dict, code:int, string:bytes):
        DICT.update({string: code})

    def update_dict_decomp(self, DICT:dict, code:int, string:bytes):
        DICT.update({code: string})

'''
    *Encapsulation of compress-decompress functions
'''
class LZWProcessor:
    '''
        Implement your LZW compression
        You can choose to process one file in one function call or all files together
    '''
    @staticmethod
    def compress(writer:BaseLZWWriter, input_file_names):
        print(f"\nCompressing {', '.join(input_file_names)} into {writer.name}")

        lzw_dict = LZWDict()
        DICT = lzw_dict.init_dict_comp(dict())
        writer.initialize()

        for input_file_name in input_file_names:
            STRING, CHAR = None, None
            with open(input_file_name, 'rb') as input_file:
                print(f"\tCompressing {input_file.name} ...")
                if STRING is None:
                    STRING = input_file.read(1)
                while True:
                    CHAR = input_file.read(1)
                    if CHAR == b'': break
                    if STRING+CHAR in DICT:
                        STRING += CHAR
                    else:
                        writer.write_code(DICT[STRING])
                        if len(DICT) >= DICT_LIMIT:
                            lzw_dict.init_dict_comp(DICT)
                        else:
                            lzw_dict.update_dict_comp(DICT, len(DICT), STRING+CHAR)
                        STRING = CHAR
                writer.write_code(DICT[STRING])
                writer.write_code(EOF)
        
        writer.write_code(0)

        print("\tDone.")

    '''
        Implement your LZW decompression
        You can choose to process one file in one function call or all files together
    '''
    @staticmethod
    def decompress(reader:BaseLZWWriter, output_file_names):
        print(f"\nDeompressing {reader.name} into {', '.join(output_file_names)}")

        lzw_dict = LZWDict()
        DICT = lzw_dict.init_dict_decomp(dict())
        reader.initialize()

        STRING, CHAR = None, None

        CURRENT = reader.read_code()
        writer = FilesWriter(output_file_names)
        i = 0
        while True:
            NEXT = reader.read_code()
            if NEXT == EOF: 
                writer.write(i, DICT[CURRENT])
                i += 1

                CURRENT = reader.read_code()
                STRING, CHAR = None, None
                continue
            STRING = DICT[CURRENT]
            writer.write(i, STRING)
            if NEXT is None: break #
            if NEXT in DICT:
                CHAR = bytes([DICT[NEXT][0]])
            else:
                CHAR = bytes([STRING[0]])
            if len(DICT) >= DICT_LIMIT:
                lzw_dict.init_dict_decomp(DICT)
            else:
                lzw_dict.update_dict_decomp(DICT, len(DICT), STRING+CHAR)
            CURRENT = NEXT
        
        writer.close()
                
        print("\tDone.")


def main():
    opt, print_usage = parse_args()

    if opt.c is not None and opt.input_files != []:
        input_file_names = opt.input_files
        output_file_name = opt.c

        # added line:
        os.makedirs(dirname(output_file_name), exist_ok=True)

        output_file = open(output_file_name, 'wb')
        writer = LZWWriter(output_file, code_size=CODE_SIZE) # added line

        for input_file_name in input_file_names:
            if not isfile(input_file_name):
                raise ValueError(f'Error: file {input_file_name} does not exist')
        writer.write_file_header(input_file_names)

        '''
            Add code to compress files
        '''
        LZWProcessor.compress(writer, input_file_names)

    elif opt.d is not None and opt.input_files == []:
        input_file_name = opt.d
        input_file = open(input_file_name, 'rb')
        reader = LZWWriter(input_file, code_size=CODE_SIZE) # added line
        output_file_names = reader.read_file_header()
        
        output_dir = opt.o
        if not isdir(output_dir):
            os.mkdir(output_dir)
        for i, output_file_name in enumerate(output_file_names):
            output_file_name = basename(output_file_name)
            output_file_names[i] = join(output_dir, output_file_name)

        '''
            Add code to decompress files
        '''
        LZWProcessor.decompress(reader, output_file_names)

    else:
        print_usage()

if __name__ == '__main__':
    main()