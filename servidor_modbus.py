from pyModbusTCP.server import ModbusServer
from time import sleep

# Crea una instancia del servidor Modbus que escucha solo en localhost
# localhost significa "este mismo ordenador"
server = ModbusServer(host="localhost", port=502, no_block=True)

try:
    print("Iniciando servidor Modbus local en localhost:502...")
    server.start()
    print("¡Servidor local en marcha!")

    # Ponemos un valor inicial en el registro 0 para que el cliente pueda leerlo
    server.data_bank.set_holding_registers(0, [123])

    # Mantenemos el servidor corriendo
    while True:
        # Imprimimos el valor del registro 0 cada 5 segundos para ver si el cliente lo cambia
        result = server.data_bank.get_holding_registers(0, 1)
        if result is not None:
            current_value = result[0]
            print(f"Valor actual en el registro 0 del servidor: {current_value}")
        else:
            print("No se pudo leer el registro 0.")
        sleep(5)

except KeyboardInterrupt:
    print("Cerrando el servidor.")
    server.stop()
