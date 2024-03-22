from lzw import *

'''
    Parse command line arguments
'''
def parse_args():

    parser = argparse.ArgumentParser(description='Compress or decompress files using LZW algorithm (Enhancements Part)')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-c', dest='c', type=str, help='Output file of compressed data')
    parser.add_argument('-o', type=str, default=join('.', 'output'), help='Output directory')
    parser.add_argument('input_files', type=str, nargs='*', help='Input files to be compressed')
    group.add_argument('-d', dest='d', type=str, help='Input file to be decompressed')

    parser.add_argument('-e', '--encrypt', type=int, default=None, help='Integer encryption key (Default: no encryption)')
    parser.add_argument('-t', '--text', type=str, default='none', choices=['none', 'hex', 'base64'], help='Binary-to-text encoding scheme used (Default: no binary-to-text)')
    parser.add_argument('-v', '--variable', default=argparse.SUPPRESS, action='store_true', help='Whether variable-width code is used (Default: no)')

    return parser.parse_args(), parser.print_help

def dict_limit(N_BITS):
    return 2**N_BITS-1
'''
    Encryption
'''
class EncryptedLZWWriter(BaseLZWWriter):

    def __init__(self, parent_writer:LZWWriter, encrypt_key=None):

        self.parent_writer = parent_writer
        self.encrypt_key = encrypt_key
        self.name = self.parent_writer.name
        self.dict_limit = dict_limit(parent_writer.code_size)

    def set_code_size(self, code_size: int):
        super().set_code_size(code_size)
        self.dict_limit = dict_limit(code_size)
        self.parent_writer.set_code_size(code_size)

    '''
        Reset internal state
    '''
    def initialize(self):
        if self.encrypt_key:
            random.seed(self.encrypt_key)

    '''
        Read a code of size CODE_SIZE from the input file
        Return None if the end of file is reached
    '''
    def read_code(self):
        code = self.parent_writer.read_code()
        # process code
        if self.encrypt_key and code is not None:
            code += random.randint(0, self.dict_limit+1)
            code %= self.dict_limit+1
            pass
        return code
    
    '''
        Write a code of size CODE_SIZE to the output file
        Remember to write extra bits to flush the buffer after you have written all the codes
    '''
    def write_code(self, code):
        # process code
        if self.encrypt_key:
            code += self.dict_limit+1
            code -= random.randint(0, self.dict_limit+1)
            code %= self.dict_limit+1
            pass
        self.parent_writer.write_code(code)

    '''
        *Offset function that performs encryption on the file names.
        TODO: prevent encoding to value b'' and b'\n'
    '''
    def _offset(self, char, sign=+1):
        MIN_VALID_CODE = ord('\n')+1 # to prevent anything to be encoded to b'' or b'\n'.
        MAX_VALID_CODE = sys.maxunicode-MIN_VALID_CODE

        char = ord(char)
        char += MAX_VALID_CODE
        char += sign*(MIN_VALID_CODE+random.randint(0, MAX_VALID_CODE))
        char %= MAX_VALID_CODE
        char = chr(char)

        return char

    '''
        Read the file header and return the list of file stored in the compressed file
    '''
    def read_file_header(self):
        self.initialize()
        output_file_names = self.parent_writer.read_file_header()
        # process strings
        if self.encrypt_key:
            output_file_names = output_file_names[0]
            output_file_names = ''.join([self._offset(c, -1) for c in output_file_names])
            output_file_names = output_file_names.split('\n')
        return output_file_names

    '''
        Write the file header to the compressed file containing names of the files
    '''
    def write_file_header(self, input_file_names):
        self.initialize()
        # process strings
        if self.encrypt_key:
            input_file_names = '\n'.join(input_file_names)
            input_file_names = [''.join([self._offset(c, +1) for c in input_file_names])]
        self.parent_writer.write_file_header(input_file_names)

'''
    Binary-to-text Encoding
'''
class HexLZWWriter(LZWWriter):

    def __init__(self, file, code_size=CODE_SIZE):
        super(HexLZWWriter, self).__init__(file, code_size)

    def read_code(self):
        read_code = self
        input_file = self.file

        if not hasattr(read_code, 'buffer'):
            read_code.buffer = 0
            read_code.buffer_bit_count = 0
        while read_code.buffer_bit_count < self.code_size:
            input_byte = input_file.read(2) # read 2 bytes together
            if input_byte == b'':
                return None
            read_code.buffer <<= 8
            read_code.buffer |= int.from_bytes(bytes.fromhex(input_byte.decode('ascii')), 'big') # from hex
            read_code.buffer_bit_count += 8
        read_code.buffer_bit_count -= self.code_size
        code = read_code.buffer >> read_code.buffer_bit_count
        read_code.buffer &= (1 << read_code.buffer_bit_count) - 1
        return code

    def write_code(self, code):
        write_code = self
        output_file = self.file

        if not hasattr(write_code, 'buffer'):
            write_code.buffer = 0
            write_code.buffer_bit_count = 0
        write_code.buffer <<= self.code_size
        write_code.buffer |= code
        write_code.buffer_bit_count += self.code_size # the remaining number of bits in the buffer
        while write_code.buffer_bit_count >= 8:
            write_code.buffer_bit_count -= 8
            output_byte = (write_code.buffer >> write_code.buffer_bit_count)
            output_byte &= 0xFF
            output_file.write(output_byte.to_bytes(1, 'big').hex().encode()) # to hex
            write_code.buffer &= (1 << write_code.buffer_bit_count) - 1
        return

    def read_file_header(self):
        input_file = self.file

        NUL, NL = b'', b'\n'
        NUL, NL = NUL.hex().encode('ascii'), NL.hex().encode('ascii')
        output_file_names = []

        line = b''
        while True:
            char = input_file.read(2)
            line += char
            if line == NUL or line == NL or line == b'':
                break
            if char == NL:
                output_file_names.append(bytes.fromhex(line.decode('ascii')).decode('utf-8').strip())
                line = b''
        return output_file_names

    def write_file_header(self, input_file_names:list[str]):
        output_file = self.file

        NUL, NL = b'', b'\n'
        NUL, NL = NUL.hex().encode('ascii'), NL.hex().encode('ascii')
        for input_file_name in input_file_names:
            output_file.write(input_file_name.encode('utf-8').hex().encode('ascii') + NL)
        output_file.write(NL)
        return

class Base64LZWWriter(LZWWriter):
    
    std_base64chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

    def __init__(self, file, code_size=CODE_SIZE):
        self.file = file
        self.name = file.name
        self.code_size = code_size

    def read_code(self):
        read_code = self
        input_file = self.file

        if not hasattr(read_code, 'buffer'):
            read_code.buffer = 0
            read_code.buffer_bit_count = 0
        while read_code.buffer_bit_count < self.code_size:
            input_byte = input_file.read(1)
            if input_byte == b'':
                return None
            input_byte = self.std_base64chars.find(input_byte.decode('ascii')) # base64 inverse mapping
            read_code.buffer <<= 6
            read_code.buffer |= input_byte
            read_code.buffer_bit_count += 6
        read_code.buffer_bit_count -= self.code_size
        code = read_code.buffer >> read_code.buffer_bit_count
        read_code.buffer &= (1 << read_code.buffer_bit_count) - 1
        return code

    def write_code(self, code):
        write_code = self
        output_file = self.file

        if not hasattr(write_code, 'buffer'):
            write_code.buffer = 0
            write_code.buffer_bit_count = 0
        write_code.buffer <<= self.code_size
        write_code.buffer |= code
        write_code.buffer_bit_count += self.code_size
        while write_code.buffer_bit_count >= 6:
            write_code.buffer_bit_count -= 6
            output_byte = (write_code.buffer >> write_code.buffer_bit_count)
            output_byte &= 0x3F # 6 bits
            output_byte = self.std_base64chars[output_byte].encode('ascii') # base64 mapping
            output_file.write(output_byte)
            write_code.buffer &= (1 << write_code.buffer_bit_count) - 1
        return

    def read_file_header(self):
        code_size = self.code_size
        self.code_size = 8

        NUL, NL = b'', b'\n'

        output_file_names = []
        
        line = b''
        while True:
            char = bytes([self.read_code()])
            line += char
            if line == NUL or line == NL:
                break
            if char == NL:
                output_file_names.append(line.decode('utf-8').strip())
                line = b''

        self.code_size = code_size

        return output_file_names

    def write_file_header(self, input_file_names):
        code_size = self.code_size
        self.code_size = 8

        for input_file_name in input_file_names:
            for c in input_file_name.encode('utf-8') + b'\n':
                self.write_code(c)
        self.write_code(ord(b'\n'.decode('utf-8')))

        self.code_size = code_size
        return

'''
    Variable-width Code
'''
class VariableWidthLZWProcessor(LZWProcessor):
    N_BITS = 8
    MIN_BITS = 9
    MAX_BITS = 16
    CUR_DICT_LIMIT = 2**8-1
    EOF = CUR_DICT_LIMIT
    
    @classmethod
    def update_code_size(cls, writer:BaseLZWWriter, code_size:int):
        print("update code size", code_size)
        cls.N_BITS = code_size
        cls.EOF = cls.CUR_DICT_LIMIT = dict_limit(code_size)
        writer.set_code_size(cls.N_BITS)

    '''
        Implement your LZW compression
        You can choose to process one file in one function call or all files together
    '''
    @classmethod
    def compress(cls, writer:LZWWriter, input_file_names):
        print(f"\nCompressing {', '.join(input_file_names)} into {writer.name}")

        lzw_dict = LZWDict()
        DICT = lzw_dict.init_dict_comp(dict())
        writer.initialize()

        cls.update_code_size(writer, cls.MIN_BITS)

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
                        if len(DICT) >= cls.CUR_DICT_LIMIT: # To cater for variable-width code
                            if cls.N_BITS < cls.MAX_BITS:
                                cls.update_code_size(writer, cls.N_BITS+1)
                                lzw_dict.update_dict_comp(DICT, len(DICT), STRING+CHAR)
                            else:
                                lzw_dict.init_dict_comp(DICT) 
                                cls.update_code_size(writer, cls.MIN_BITS)
                        else:
                            lzw_dict.update_dict_comp(DICT, len(DICT), STRING+CHAR)
                        STRING = CHAR
                writer.write_code(DICT[STRING])
                writer.write_code(cls.EOF)
            
        writer.write_code(0)

        print("\tDone.")

    '''
        Implement your LZW decompression
        You can choose to process one file in one function call or all files together
    '''
    @classmethod
    def decompress(cls, reader:BaseLZWWriter, output_file_names):
        print(f"\nDeompressing {reader.name} into {', '.join(output_file_names)}")

        lzw_dict = LZWDict()
        DICT = lzw_dict.init_dict_decomp(dict())
        reader.initialize()

        cls.update_code_size(reader, cls.MIN_BITS)

        STRING, CHAR = None, None

        CURRENT = reader.read_code()
        writer = FilesWriter(output_file_names)
        i = 0
        while True:
            NEXT = reader.read_code()
            if NEXT == cls.EOF: 
                writer.write(i, DICT[CURRENT])
                i += 1

                CURRENT = reader.read_code()
                STRING, CHAR = None, None
                if CURRENT is None: break
                continue

            STRING = DICT[CURRENT]
            writer.write(i, STRING)
            if NEXT is None: break
            if NEXT in DICT:
                CHAR = bytes([DICT[NEXT][0]])
            else:
                CHAR = bytes([STRING[0]])
            if len(DICT) >= cls.CUR_DICT_LIMIT-1: # To cater for variable-width code
                if cls.N_BITS < cls.MAX_BITS:
                    cls.update_code_size(reader, cls.N_BITS+1)
                    lzw_dict.update_dict_decomp(DICT, len(DICT), STRING+CHAR)
                else:
                    lzw_dict.init_dict_decomp(DICT)
                    cls.update_code_size(reader, cls.MIN_BITS)
            else:
                lzw_dict.update_dict_decomp(DICT, len(DICT), STRING+CHAR)
            CURRENT = NEXT
        writer.close()
                
        print("\tDone.")

LZW_PROCESSORS = {False:LZWProcessor, True:VariableWidthLZWProcessor}
BASE_WRITERS = {'none':LZWWriter, 'hex':HexLZWWriter, 'base64':Base64LZWWriter}

def main():
    opt, print_usage = parse_args()

    has_bin_to_text = opt.text != 'none'
    has_variable_code = 'variable' in opt

    print(f'Received encryption key: {opt.encrypt}.' if opt.encrypt else 'Received no encryption.')
    if has_bin_to_text:     print(f'Binary-to-text encoding {opt.text} is enabled.')
    if has_variable_code:   print('Variable-width code is enabled.')
    
    lzw_processor   = LZW_PROCESSORS[has_variable_code]
    base_writer     = BASE_WRITERS[opt.text]
    encryptor       = EncryptedLZWWriter

    if opt.c is not None and opt.input_files != []:
        input_file_names = opt.input_files
        output_file_name = opt.c

        # added line:
        os.makedirs(dirname(output_file_name), exist_ok=True)

        output_file = open(output_file_name, 'wb')
        # added lines:
        writer = base_writer(output_file, code_size=CODE_SIZE) 
        writer = encryptor(writer, encrypt_key=opt.encrypt)

        for input_file_name in input_file_names:
            if not isfile(input_file_name):
                raise ValueError(f'Error: file {input_file_name} does not exist')
        writer.write_file_header(input_file_names)

        '''
            Add code to compress files
        '''
        lzw_processor.compress(writer, input_file_names)

    elif opt.d is not None and opt.input_files == []:
        input_file_name = opt.d
        input_file = open(input_file_name, 'rb')
        # added lines:
        reader = base_writer(input_file, code_size=CODE_SIZE) 
        reader = encryptor(reader, encrypt_key=opt.encrypt)
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
        #try:
        lzw_processor.decompress(reader, output_file_names)
        #except Exception:
        #    print(f'Incorrect encryption key provided. If you are certain that you used the correct key, \nplease also make sure that you are using the same python version, as the behavior of random.randint() may differ.')

    else:
        print_usage()

if __name__ == '__main__':
    main()