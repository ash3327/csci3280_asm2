import os
import sys
import argparse
import random
from os.path import join, isabs, isfile, exists, isdir, basename

CODE_SIZE = 12

'''
    Parse command line arguments
'''
def parse_args():
    parser = argparse.ArgumentParser(description='Compress or decompress files using LZW algorithm')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-c', type=str, help='Output file of compressed data')
    parser.add_argument('-o', type=str, default=join('.', 'output'), help='Output directory')
    parser.add_argument('input_files', type=str, nargs='*', help='Input files to be compressed')
    group.add_argument('-d', type=str, help='Input file to be decompressed')
    return parser.parse_args(), parser.print_help

'''
    Read a code of size CODE_SIZE from the input file
    Return None if the end of file is reached
'''
def read_code(input_file, code_size):
    if not hasattr(read_code, 'buffer'):
        read_code.buffer = 0
        read_code.buffer_bit_count = 0
    while read_code.buffer_bit_count < code_size:
        input_byte = input_file.read(1)
        if input_byte == b'':
            return None
        read_code.buffer <<= 8
        read_code.buffer |= int.from_bytes(input_byte, 'big')
        read_code.buffer_bit_count += 8
    read_code.buffer_bit_count -= code_size
    code = read_code.buffer >> read_code.buffer_bit_count
    read_code.buffer &= (1 << read_code.buffer_bit_count) - 1
    return code

'''
    Write a code of size CODE_SIZE to the output file
    Remember to write extra bits to flush the buffer after you have written all the codes
'''
def write_code(output_file, code, code_size):
    if not hasattr(write_code, 'buffer'):
        write_code.buffer = 0
        write_code.buffer_bit_count = 0
    write_code.buffer <<= code_size
    write_code.buffer |= code
    write_code.buffer_bit_count += code_size
    while write_code.buffer_bit_count >= 8:
        write_code.buffer_bit_count -= 8
        output_byte = (write_code.buffer >> write_code.buffer_bit_count)
        output_file.write(output_byte.to_bytes(1, 'big'))
        write_code.buffer &= (1 << write_code.buffer_bit_count) - 1
    return

'''
    Read the file header and return the list of file stored in the compressed file
'''
def read_file_header(input_file):
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
def write_file_header(output_file, input_file_names):
    for input_file_name in input_file_names:
        output_file.write(input_file_name.encode('utf-8') + b'\n')
    output_file.write(b'\n')
    return

'''
    Implement your LZW compression
    You can choose to process one file in one function call or all files together
'''
def compress():
    pass

'''
    Implement your LZW decompression
    You can choose to process one file in one function call or all files together
'''
def decompress():
    pass


def main():
    opt, print_usage = parse_args()

    if opt.c is not None and opt.input_files != []:
        input_file_names = opt.input_files
        output_file_name = opt.c
        output_file = open(output_file_name, 'wb')
        for input_file_name in input_file_names:
            if not isfile(input_file_name):
                raise ValueError(f'Error: file {input_file_name} does not exist')
        write_file_header(output_file, input_file_names)

        '''
            Add code to compress files
        '''

    elif opt.d is not None and opt.input_files == []:
        input_file_name = opt.d
        input_file = open(input_file_name, 'rb')
        output_file_names = read_file_header(input_file)
        
        output_dir = opt.o
        if not isdir(output_dir):
            os.mkdir(output_dir)
        for i, output_file_name in enumerate(output_file_names):
            output_file_name = basename(output_file_name)
            output_file_names[i] = join(output_dir, output_file_name)

        '''
            Add code to decompress files
        '''

    else:
        print_usage()

if __name__ == '__main__':
    main()