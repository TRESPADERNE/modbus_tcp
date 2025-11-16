import struct

# El manual del fabricante (la fuente de la verdad) nos dice que el
# formato es "Big-Endian, High Word First" y que el valor es 230.5.
# Vamos a ver qué pasa si lo interpretamos de las cuatro formas posibles.

# Suponemos que la lectura de los registros 100 y 101 nos da:
reg1 = 17254  # En hexadecimal: 0x4366
reg2 = 32768  # En hexadecimal: 0x8000


# --- Escenario 1: Interpretación CORRECTA ---
# Manual: "High Word First" -> El primer registro (reg1) es la parte alta.
# Manual: "Big Endian" -> El byte alto de cada registro va primero.
# Bytes en el cable: [0x43, 0x66] [0x80, 0x00] -> b'\x43\x66\x80\x00'
# Se dice a unpack que interprete esos bytes como un float big-endian ('>f').
payload_bytes = reg1.to_bytes(2, 'big') + reg2.to_bytes(2, 'big')
valor = struct.unpack('>f', payload_bytes)[0]
print(f"1. High Word First, Big Endian (CORRECTO): {valor}")


# --- Escenario 2: Interpretación INCORRECTA (Error de Endianness) ---
# Leemos los registros en el orden correcto (High Word First), pero
# creemos que el sistema es Little Endian.
# Se dice a unpack que interprete b'\x43\x66\x80\x00' como little-endian ('<f').
valor = struct.unpack('<f', payload_bytes)[0]
print(f"2. High Word First, Little Endian (ERROR): {valor}")


# --- Escenario 3: Interpretación INCORRECTA (Error de orden de registros) ---
# Creemos que es "Low Word First", así que invertimos los registros.
# Bytes en el cable: [0x80, 0x00] [0x43, 0x66] -> b'\x80\x00\x43\x66'
# Y lo interpretamos como Big Endian.
payload_bytes_invertido = reg2.to_bytes(2, 'big') + reg1.to_bytes(2, 'big')
valor = struct.unpack('>f', payload_bytes_invertido)[0]
print(f"3. Low Word First, Big Endian (ERROR): {valor}")


# --- Escenario 4: Interpretación INCORRECTA (Doble error) ---
# Invertimos los registros (Low Word First) Y TAMBIÉN nos equivocamos
# en el endianness (creemos que es Little Endian).
valor = struct.unpack('<f', payload_bytes_invertido)[0]
print(f"4. Low Word First, Little Endian (ERROR): {valor}")
