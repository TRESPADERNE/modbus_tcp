import struct
from typing import Literal, List, Dict

# Tipos para byteorder y wordorder
ByteOrder = Literal['>', '<']
WordOrder32 = Literal['>', '<']
WordOrder64 = Literal['ABCD', 'DCBA', 'BADC', 'CDAB']


class Endian:
    Big: ByteOrder = '>'
    Little: ByteOrder = '<'


WORD_ORDER_MAP: Dict[WordOrder64, tuple[int, int, int, int]] = {
    'ABCD': (0, 1, 2, 3),
    'DCBA': (3, 2, 1, 0),
    'BADC': (1, 0, 3, 2),
    'CDAB': (2, 3, 0, 1)
}


def float_to_words(f: float) -> List[int]:
    packed_data = struct.pack('>f', f)
    return list(struct.unpack('>HH', packed_data))


def words_to_float(word1: int, word2: int) -> float:
    packed_data = struct.pack('>HH', word1, word2)
    return struct.unpack('>f', packed_data)[0]


def int32_to_words(i: int) -> List[int]:
    packed_data = struct.pack('>I', i)
    return list(struct.unpack('>HH', packed_data))


def words_to_int32(word1: int, word2: int) -> int:
    packed_data = struct.pack('>HH', word1, word2)
    return struct.unpack('>I', packed_data)[0]


def decode_32bit_float(
    registers: List[int],
    byteorder: ByteOrder = Endian.Big,
    wordorder: WordOrder32 = Endian.Big
) -> float:
    if len(registers) != 2:
        raise ValueError("Se requieren exactamente 2 registros para un float de 32 bits.")
    if wordorder == Endian.Little:
        registers = registers[::-1]
    packed_data = struct.pack(f'{byteorder}HH', *registers)
    return struct.unpack(f'{byteorder}f', packed_data)[0]


def decode_64bit_double(
    registers: List[int],
    byteorder: ByteOrder = Endian.Big,
    wordorder: WordOrder64 = 'ABCD'
) -> float:
    if len(registers) != 4:
        raise ValueError("Se requieren exactamente 4 registros para un double de 64 bits.")
    try:
        indices = WORD_ORDER_MAP[wordorder]
    except KeyError:
        raise ValueError(f"wordorder desconocido: {wordorder}")
    ordered_regs = [registers[i] for i in indices]
    packed_data = struct.pack(f'{byteorder}HHHH', *ordered_regs)
    return struct.unpack(f'{byteorder}d', packed_data)[0]
