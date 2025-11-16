from pyModbusTCP.server import ModbusServer
from time import sleep

# Crea una instancia del servidor Modbus que escucha solo en localhost
# localhost significa "este mismo ordenador"
server = ModbusServer(host="localhost", port=502, no_block=True)
# Usamos no_block=True para que el servidor no bloquee la ejecución del programa
# De esta forma podemos hacer otras cosas en el mismo programa, como imprimir el valor del registro 0
# cambiar el valor del registro 0, etc.
try:
    print("Iniciando servidor Modbus local en localhost:502...")
    server.start()
    print("¡Servidor local en marcha!")

    # Ponemos un valor inicial 123 en el registro 0 para que el cliente pueda leerlo
    # Como la lista tiene un único elemento, significa que solo escribimos en el registro 0
    server.data_bank.set_holding_registers(0, [123])

    # Mantenemos el servidor corriendo
    while True:
        # Imprimimos el valor del registro 0 cada 5 segundos para ver si el cliente lo cambia
        # El 1 indica que queremos leer 1 registro a partir del registro 0
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
