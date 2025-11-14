import struct
from typing import cast
import random
from time import sleep
from pyModbusTCP.server import ModbusServer

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
# 2. DEFINICIONES DE ALARMAS
# --------------------------------------------------------------------------- #
ALARM_CODE_NONE = 0
ALARM_CODE_DOSING_BASE = 100

# --------------------------------------------------------------------------- #
# 3. FUNCIONES DE AYUDA
# --------------------------------------------------------------------------- #


def words_to_float(word1: int, word2: int) -> float:
    packed_data = struct.pack('>HH', word1, word2)
    return struct.unpack('>f', packed_data)[0]


def float_to_words(f: float) -> list[int]:
    packed_data = struct.pack('>f', f)
    return list(struct.unpack('>HH', packed_data))


def words_to_int32(word1: int, word2: int) -> int:
    packed_data = struct.pack('>HH', word1, word2)
    return struct.unpack('>I', packed_data)[0]


def int32_to_words(i: int) -> list[int]:
    packed_data = struct.pack('>I', i)
    return list(struct.unpack('>HH', packed_data))


# --------------------------------------------------------------------------- #
# 4. EL SERVIDOR Y LA LÓGICA DE SIMULACIÓN
# --------------------------------------------------------------------------- #
TOLERANCE = 0.5
CHANCE_OF_FAILURE = 0.15  # Volvemos a una probabilidad normal
STATE_IDLE = 0
STATE_RUNNING = 1
STATE_ALARM = 99
STAGE_IDLE = 0
STAGE_DOSING = 1
STAGE_MIXING = 10
STAGE_BAGGING = 11

server = ModbusServer(host="localhost", port=502, no_block=True)

try:
    print("Iniciando servidor (VERSIÓN ESTABLE)...")
    server.start()
    print("¡Servidor en marcha!")

    server.data_bank.set_input_registers(ADDR_LINE_STATE, [STATE_IDLE])
    server.data_bank.set_input_registers(ADDR_PROCESS_STAGE, [STAGE_IDLE])
    server.data_bank.set_input_registers(ADDR_ACTIVE_ALARM_CODE, [ALARM_CODE_NONE])
    server.data_bank.set_input_registers(ADDR_OK_SACKS_COUNTER, int32_to_words(0))
    server.data_bank.set_input_registers(ADDR_BAD_SACKS_COUNTER, int32_to_words(0))
    server.data_bank.set_input_registers(ADDR_TOTAL_WEIGHT, float_to_words(0.0))
    for i in range(NUM_INGREDIENTS):
        addr = ADDR_REAL_WEIGHTS_START + i * 2
        server.data_bank.set_input_registers(addr, float_to_words(0.0))

    line_state = STATE_IDLE
    current_ingredient_index = 0
    target_weights = [0.0] * NUM_INGREDIENTS

    while True:
        if line_state == STATE_IDLE:
            server.data_bank.set_input_registers(ADDR_LINE_STATE, [STATE_IDLE])
            server.data_bank.set_input_registers(ADDR_PROCESS_STAGE, [STAGE_IDLE])
            server.data_bank.set_input_registers(ADDR_ACTIVE_ALARM_CODE, [ALARM_CODE_NONE])

            is_start_order = server.data_bank.get_coils(ADDR_ORDER_START, 1)
            if is_start_order and is_start_order[0] is True:
                print("\n[INFO] Orden de marcha recibida. Iniciando producción...")
                server.data_bank.set_coils(ADDR_ORDER_START, [False])

                zeros = [0] * (NUM_INGREDIENTS * 2)
                server.data_bank.set_input_registers(ADDR_REAL_WEIGHTS_START, zeros)
                server.data_bank.set_input_registers(ADDR_TOTAL_WEIGHT, float_to_words(0.0))

                target_weights_words = cast(list[int] | None, server.data_bank.get_holding_registers(
                    ADDR_TARGET_WEIGHTS_START, NUM_INGREDIENTS * 2))
                if target_weights_words:
                    for i in range(NUM_INGREDIENTS):
                        w1, w2 = target_weights_words[i*2], target_weights_words[i*2+1]
                        target_weights[i] = words_to_float(w1, w2)

                current_ingredient_index = 0
                line_state = STATE_RUNNING

        elif line_state == STATE_RUNNING:
            server.data_bank.set_input_registers(ADDR_LINE_STATE, [STATE_RUNNING])

            if current_ingredient_index >= NUM_INGREDIENTS:
                print("[PROCESO] Dosificación OK. Mezclando...")
                server.data_bank.set_input_registers(ADDR_PROCESS_STAGE, [STAGE_MIXING])
                sleep(2)
                print("[PROCESO] Ensacando...")
                server.data_bank.set_input_registers(ADDR_PROCESS_STAGE, [STAGE_BAGGING])

                real_weights_words = cast(list[int], server.data_bank.get_input_registers(
                    ADDR_REAL_WEIGHTS_START, NUM_INGREDIENTS * 2))
                total_weight = sum(words_to_float(
                    real_weights_words[i*2], real_weights_words[i*2+1]) for i in range(NUM_INGREDIENTS))
                server.data_bank.set_input_registers(ADDR_TOTAL_WEIGHT, float_to_words(total_weight))

                ok_sacks_words = cast(list[int] | None, server.data_bank.get_input_registers(ADDR_OK_SACKS_COUNTER, 2))
                ok_sacks_count = words_to_int32(ok_sacks_words[0], ok_sacks_words[1]) if ok_sacks_words else 0
                server.data_bank.set_input_registers(ADDR_OK_SACKS_COUNTER, int32_to_words(ok_sacks_count + 1))

                print(f"[INFO] Saco producido correctamente. Peso total: {total_weight:.2f} kg.")
                current_ingredient_index = 0
                line_state = STATE_IDLE
            else:
                current_target = target_weights[current_ingredient_index]
                if current_target <= 0:
                    current_ingredient_index += 1
                else:
                    stage = STAGE_DOSING + current_ingredient_index
                    server.data_bank.set_input_registers(ADDR_PROCESS_STAGE, [stage])
                    print(f"[PROCESO] Dosificando ingrediente #{current_ingredient_index + 1}...")
                    sleep(1)

                    real_weight = current_target + random.uniform(-0.2, 0.2)
                    if random.random() < CHANCE_OF_FAILURE:
                        print(f"[FALLO] ¡Fallo de dosificación en ingrediente #{current_ingredient_index + 1}!")
                        real_weight = current_target + random.uniform(1.0, 3.0)

                    addr = ADDR_REAL_WEIGHTS_START + current_ingredient_index * 2
                    server.data_bank.set_input_registers(addr, float_to_words(real_weight))

                    if abs(real_weight - current_target) > TOLERANCE:
                        print("[ALARMA] Lote fuera de especificación. Producción detenida.")
                        alarm_code = ALARM_CODE_DOSING_BASE + (current_ingredient_index + 1)
                        server.data_bank.set_input_registers(ADDR_ACTIVE_ALARM_CODE, [alarm_code])

                        bad_sacks_words = cast(
                            list[int] | None, server.data_bank.get_input_registers(ADDR_BAD_SACKS_COUNTER, 2))
                        bad_sacks_count = words_to_int32(
                            bad_sacks_words[0], bad_sacks_words[1]) if bad_sacks_words else 0
                        server.data_bank.set_input_registers(
                            ADDR_BAD_SACKS_COUNTER, int32_to_words(bad_sacks_count + 1))

                        line_state = STATE_ALARM
                    else:
                        current_ingredient_index += 1

        elif line_state == STATE_ALARM:
            server.data_bank.set_input_registers(ADDR_LINE_STATE, [STATE_ALARM])

            is_reset_order = server.data_bank.get_coils(ADDR_ORDER_RESET, 1)
            if is_reset_order and is_reset_order[0] is True:
                print("[INFO] Reset de alarma detectado. Volviendo a estado IDLE.")
                server.data_bank.set_coils(ADDR_ORDER_RESET, [False])

                current_ingredient_index = 0
                line_state = STATE_IDLE

        sleep(0.5)

except Exception as e:
    print(f"Error fatal: {e}")
finally:
    print("Cerrando el servidor.")
    server.stop()
