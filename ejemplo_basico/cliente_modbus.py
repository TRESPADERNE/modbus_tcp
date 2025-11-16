from pyModbusTCP.client import ModbusClient
from time import sleep

SERVER_HOST = "localhost"
SERVER_PORT = 502

print(f"Intentando conectar al servidor local en {SERVER_HOST}:{SERVER_PORT}")
client = ModbusClient(host=SERVER_HOST, port=SERVER_PORT)

# Conectar
client.open()

if client.is_open:
    print("¡Conexión exitosa con el servidor local!")

    # 1. Leer el valor inicial del registro 0
    print("\n--- LECTURA ---")
    valor_leido = client.read_holding_registers(0, 1)
    if valor_leido:
        print(f"Valor leído del servidor: {valor_leido[0]}")
    else:
        print("Error al leer.")

    sleep(2)

    # 2. Escribir un nuevo valor en el registro 0
    print("\n--- ESCRITURA ---")
    nuevo_valor = 999
    print(f"Escribiendo el nuevo valor {nuevo_valor} en el servidor...")
    escribir_ok = client.write_single_register(0, nuevo_valor)

    if escribir_ok:
        print("¡Escritura correcta! Ahora el servidor debería mostrar el nuevo valor.")
    else:
        print("Error al escribir.")

    client.close()
    print("\nConexión cerrada.")

else:
    print("Error: No se pudo conectar. ¿Te acordaste de arrancar primero el 'servidor_modbus.py'?")
