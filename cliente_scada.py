import struct
import time
import os
from pyModbusTCP.client import ModbusClient

# --------------------------------------------------------------------------- #
# 1. EL MAPA DE REGISTROS
# --------------------------------------------------------------------------- #
ADDR_TARGET_WEIGHTS_START = 200
NUM_INGREDIENTS = 5
ADDR_ORDER_START = 0
ADDR_ORDER_RESET = 1
ADDR_LINE_STATE = 100
ADDR_PROCESS_STAGE = 101
ADDR_ACTIVE_ALARM_CODE = 102
ADDR_REAL_WEIGHTS_START = 300
ADDR_TOTAL_WEIGHT = 400
ADDR_OK_SACKS_COUNTER = 500
ADDR_BAD_SACKS_COUNTER = 502

# --------------------------------------------------------------------------- #
# 2. FUNCIONES DE AYUDA
# --------------------------------------------------------------------------- #


def float_to_words(f: float) -> list[int]:
    packed_data = struct.pack('>f', f)
    return list(struct.unpack('>HH', packed_data))


def words_to_float(word1: int, word2: int) -> float:
    packed_data = struct.pack('>HH', word1, word2)
    return struct.unpack('>f', packed_data)[0]


def words_to_int32(word1: int, word2: int) -> int:
    # Esta es la línea que toqué y rompí. La restauro a tu versión.
    packed_data = struct.pack('>HH', word1, word2)
    return struct.unpack('>I', packed_data)[0]


def int32_to_words(i: int) -> list[int]:
    packed_data = struct.pack('>I', i)
    return list(struct.unpack('>HH', packed_data))


# --------------------------------------------------------------------------- #
# 3. DEFINICIÓN DE RECETAS Y MAPAS
# --------------------------------------------------------------------------- #
RECIPES = {
    "1": {"name": "Pollo y Arroz (Básico)", "weights": [25.0, 25.0, 0.0, 0.0, 0.0]},
    "2": {"name": "Salmón y Patata (Premium)", "weights": [20.5, 15.0, 5.5, 0.0, 0.0]},
    "3": {"name": "Cachorro (Completo)", "weights": [15.0, 10.0, 10.0, 8.5, 2.0]}
}
STATE_MAP = {0: "PARADO", 1: "EN PRODUCCIÓN", 99: "ALARMA"}
STAGE_MAP = {
    0: "En espera", 1: "Dosificando Ing. #1", 2: "Dosificando Ing. #2",
    3: "Dosificando Ing. #3", 4: "Dosificando Ing. #4", 5: "Dosificando Ing. #5",
    10: "Mezclando", 11: "Ensacando"
}
ALARM_MAP = {
    0: "Sin alarmas",
    101: "Fallo de dosificación: Ingrediente #1 fuera de tolerancia",
    102: "Fallo de dosificación: Ingrediente #2 fuera de tolerancia",
    103: "Fallo de dosificación: Ingrediente #3 fuera de tolerancia",
    104: "Fallo de dosificación: Ingrediente #4 fuera de tolerancia",
    105: "Fallo de dosificación: Ingrediente #5 fuera de tolerancia",
}

# --------------------------------------------------------------------------- #
# 4. LÓGICA PRINCIPAL DEL CLIENTE
# --------------------------------------------------------------------------- #
SERVER_HOST = "localhost"
SERVER_PORT = 502
client = ModbusClient(host=SERVER_HOST, port=SERVER_PORT)

try:
    print(f"Conectando a la planta en {SERVER_HOST}:{SERVER_PORT}...")
    if not client.open():
        print(f"Error: No se pudo conectar. ¿Está el servidor en marcha?")
        exit()
    print("¡Conexión exitosa!")

    while True:
        print("\n" + "="*50)
        print("--- MENÚ PRINCIPAL ---")
        print("1. Producir un saco")
        print("2. Salir")
        main_choice = input("Selecciona una opción: ")

        if main_choice == '2':
            break

        if main_choice != '1':
            continue

        print("\n--- SELECCIÓN DE RECETA ---")
        for key, recipe in RECIPES.items():
            print(f"  [{key}] {recipe['name']}")
        choice = input("Por favor, selecciona el número de la receta a producir: ")
        selected_recipe = RECIPES.get(choice)
        if not selected_recipe:
            print("Selección no válida.")
            continue
        print(f"Has seleccionado: {selected_recipe['name']}")

        target_weights_words = []
        for weight in selected_recipe['weights']:
            target_weights_words.extend(float_to_words(weight))
        print("Enviando parámetros de la receta al PLC...")
        if not client.write_multiple_registers(ADDR_TARGET_WEIGHTS_START, target_weights_words):
            print("Error: No se pudo escribir la receta en el PLC.")
            continue

        input("\nPresiona Enter para dar la ORDEN DE MARCHA...")
        client.write_single_coil(ADDR_ORDER_START, True)

        has_started_working = False

        while True:
            os.system('cls' if os.name == 'nt' else 'clear')

            state_regs = client.read_input_registers(ADDR_LINE_STATE, 3)
            weight_regs = client.read_input_registers(ADDR_REAL_WEIGHTS_START, NUM_INGREDIENTS * 2)
            counter_regs = client.read_input_registers(ADDR_OK_SACKS_COUNTER, 4)

            if not all([state_regs, weight_regs, counter_regs]):
                print("Error: No se pudo leer el estado completo. Reintentando...")
                time.sleep(2)
                continue

            line_state = state_regs[0]
            process_stage = state_regs[1]
            active_alarm_code = state_regs[2]
            ok_sacks = words_to_int32(counter_regs[0], counter_regs[1])
            bad_sacks = words_to_int32(counter_regs[2], counter_regs[3])
            real_weights = [words_to_float(weight_regs[i*2], weight_regs[i*2+1]) for i in range(NUM_INGREDIENTS)]

            print("--- PANEL DE CONTROL ---")
            print(f"ESTADO GENERAL: {STATE_MAP.get(line_state, 'Desconocido')}")
            print(f"ETAPA ACTUAL:   {STAGE_MAP.get(process_stage, 'Desconocida')}")
            print("---------------------------------------------")
            print(f"PRODUCCIÓN: [{selected_recipe['name']}]")
            print(f"  - Sacos Buenos (Total):    {ok_sacks}")
            print(f"  - Sacos Rechazados (Total): {bad_sacks}")
            print("---------------------------------------------")
            print("PESOS EN TIEMPO REAL (Real / Objetivo):")
            for i in range(NUM_INGREDIENTS):
                indicator = " <-- Proceso" if process_stage == (1 + i) else ""
                print(
                    f"  - Ingrediente #{i+1}: {real_weights[i]:.2f} / {selected_recipe['weights'][i]:.2f} kg {indicator}")
            print("---------------------------------------------")

            if line_state == 1:
                has_started_working = True

            if line_state == 99:
                alarm_message = ALARM_MAP.get(active_alarm_code, f"Alarma desconocida (Código: {active_alarm_code})")
                print(f"\n\n¡¡¡ ALARMA DETECTADA !!!\nMOTIVO: {alarm_message}")
                input("Presiona Enter para RECONOCER y RESETEAR la alarma...")
                client.write_single_coil(ADDR_ORDER_RESET, True)
                print("Enviando orden de reset al PLC...")
                time.sleep(1.5)
                break

            if has_started_working and line_state == 0:
                print("\n\nSaco procesado. Volviendo al menú principal.")
                time.sleep(2)
                break

            print("\n(Presiona Ctrl+C para detener el SCADA)")
            time.sleep(1)

except KeyboardInterrupt:
    print("\nSCADA detenido por el usuario.")
except Exception as e:
    print(f"Error fatal: {e}")
finally:
    if client.is_open:
        print("Cerrando conexión con la planta.")
        client.close()
