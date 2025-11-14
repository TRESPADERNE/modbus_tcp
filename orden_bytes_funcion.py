import struct
from typing import Literal


ByteOrder = Literal['>', '<']
WordOrder32 = Literal['>', '<']
WordOrder64 = Literal['ABCD', 'DCBA', 'BADC', 'CDAB']


class Endian:
    Big: ByteOrder = '>'
    Little: ByteOrder = '<'


# Mapeo declarativo para el orden de palabras de 64 bits

WORD_ORDER_MAP: dict[WordOrder64, tuple[int, int, int, int]] = {
    'ABCD': (0, 1, 2, 3),  # Orden original
    'DCBA': (3, 2, 1, 0),  # Inversión completa de registros
    'BADC': (1, 0, 3, 2),  # Swap de registros dentro de cada par de 32 bits
    'CDAB': (2, 3, 0, 1)   # Swap de los dos bloques de 32 bits
}


def decode_32bit_float(
    registers: list[int],
    byteorder: ByteOrder = Endian.Big,
    wordorder: WordOrder32 = Endian.Big
) -> float:
    # (Tu función de 32 bits, que ya era perfecta)
    if len(registers) != 2:
        raise ValueError("Se requieren exactamente 2 registros para un float de 32 bits.")
    if wordorder == Endian.Little:
        registers = registers[::-1]
    packed_data = struct.pack(f'{byteorder}HH', *registers)
    return struct.unpack(f'{byteorder}f', packed_data)[0]


def decode_64bit_double(
    registers: list[int],
    byteorder: ByteOrder = Endian.Big,
    wordorder: WordOrder64 = 'ABCD'
) -> float:
    """
    Decodifica una lista de cuatro registros de 16 bits en un double de 64 bits.
    """
    if len(registers) != 4:
        raise ValueError("Se requieren exactamente 4 registros para un double de 64 bits.")

    # 1. Obtener el orden correcto de los índices desde el diccionario
    try:
        indices = WORD_ORDER_MAP[wordorder]
    except KeyError:
        raise ValueError(f"wordorder desconocido: {wordorder}")

    # 2. Reordenar los registros usando una list comprehension
    ordered_regs = [registers[i] for i in indices]

    # 3. Empaquetar y decodificar
    packed_data = struct.pack(f'{byteorder}HHHH', *ordered_regs)
    return struct.unpack(f'{byteorder}d', packed_data)[0]


# --- EJEMPLO DE USO ---

# 230.5 en float de 32 bits
# Hexadecimal: 0x43668000
# Enteros de 16 bits: 17254, 32768
registers_float: list[int] = [17254, 32768]
temperatura: float = decode_32bit_float(registers_float)
print(f"Float decodificado (32 bits): {temperatura}")

# Ejemplo para un double: el número PI
# (Big Endian, Word Order 'BADC')
# pi = 3.141592653589793
# Hexadecimal: 0x400921FB54442D18
# enteros de 16 bits: 16393, 8699, 21572, 11544,
registers_double: list[int] = [8699, 16393, 11544, 21572]
pi_aprox: float = decode_64bit_double(registers_double, byteorder=Endian.Big, wordorder='BADC')
print(f"Double decodificado (64 bits): {pi_aprox}")
