import random
from time import sleep
from pyModbusTCP.server import ModbusServer
from modbus_utils import float_to_words, words_to_float

NUM_INGREDIENTS = 5

# --------------------------------------------------------------------------- #
# 1. EL MAPA DE REGISTROS (Constantes)
# --------------------------------------------------------------------------- #
ADDR_TARGET_WEIGHTS_START = 200
ADDR_ORDER_START = 0
ADDR_ORDER_RESET = 1
ADDR_LINE_STATE = 100
ADDR_PROCESS_STAGE = 101
ADDR_ACTIVE_ALARM_CODE = 102
ADDR_REAL_WEIGHTS_START = 300
ADDR_TOTAL_WEIGHT = 400


# --------------------------------------------------------------------------- #
# 2. DEFINICIONES DE ALARMAS Y ESTADOS (Constantes)
# --------------------------------------------------------------------------- #
ALARM_CODE_NONE = 0
ALARM_CODE_DOSING_BASE = 100

STATE_IDLE = 0
STATE_RUNNING = 1
STATE_ALARM = 99

STAGE_IDLE = 0
STAGE_DOSING = 1
STAGE_MIXING = 10
STAGE_BAGGING = 11

# --------------------------------------------------------------------------- #
# 3. PARÁMETROS DE SIMULACIÓN (Constantes)
# --------------------------------------------------------------------------- #
TOLERANCE = 0.5
CHANCE_OF_FAILURE = 0.05

# --------------------------------------------------------------------------- #
# 4. FUNCIONES DE LÓGICA DE PROCESO
# --------------------------------------------------------------------------- #


def initialize_registers(server: ModbusServer):
    """Inicializa todos los registros del servidor a sus valores por defecto."""
    print("Inicializando registros del servidor a valores por defecto...")
    server.data_bank.set_input_registers(ADDR_LINE_STATE, [STATE_IDLE])
    server.data_bank.set_input_registers(ADDR_PROCESS_STAGE, [STAGE_IDLE])
    server.data_bank.set_input_registers(ADDR_ACTIVE_ALARM_CODE, [ALARM_CODE_NONE])
    server.data_bank.set_input_registers(ADDR_TOTAL_WEIGHT, float_to_words(0.0))
    # Limpia los pesos reales
    zeros = [0] * (NUM_INGREDIENTS * 2)
    server.data_bank.set_input_registers(ADDR_REAL_WEIGHTS_START, zeros)


def read_target_weights(server: ModbusServer) -> list[float]:
    """Lee los pesos objetivo desde los registros holding y los convierte a float."""
    target_weights = [0.0] * NUM_INGREDIENTS
    target_weights_words: list[int] = server.data_bank.get_holding_registers(
        ADDR_TARGET_WEIGHTS_START, NUM_INGREDIENTS * 2)  # type: ignore
    if target_weights_words:
        for i in range(NUM_INGREDIENTS):
            w1, w2 = target_weights_words[i*2], target_weights_words[i*2+1]
            target_weights[i] = words_to_float(w1, w2)
    return target_weights


def dose_ingredients(server: ModbusServer, target_weights: list[float]) -> bool:
    """
    Simula el proceso de dosificación de todos los ingredientes.
    Devuelve True si la dosificación fue exitosa, False si ocurrió un fallo.
    """
    for i in range(NUM_INGREDIENTS):
        current_target = target_weights[i]
        if current_target <= 0:
            continue  # Salta ingredientes con peso objetivo cero

        stage = STAGE_DOSING + i
        server.data_bank.set_input_registers(ADDR_PROCESS_STAGE, [stage])
        print(f"[PROCESO] Dosificando ingrediente #{i + 1} (Objetivo: {current_target:.2f} kg)...")
        sleep(1)

        # Simulación de fallo
        if random.random() < CHANCE_OF_FAILURE:
            print(f"[FALLO] ¡Fallo de dosificación en ingrediente #{i + 1}!")
            real_weight = current_target + random.uniform(1.0, 3.0)  # Fallo fuera de tolerancia
        else:
            real_weight = current_target + random.uniform(-0.2, 0.2)  # Funcionamiento normal

        addr = ADDR_REAL_WEIGHTS_START + i * 2
        server.data_bank.set_input_registers(addr, float_to_words(real_weight))

        # Comprobar tolerancia
        if abs(real_weight - current_target) > TOLERANCE:
            print("[ALARMA] Lote fuera de especificación. Producción detenida.")
            alarm_code = ALARM_CODE_DOSING_BASE + (i + 1)
            server.data_bank.set_input_registers(ADDR_ACTIVE_ALARM_CODE, [alarm_code])
            return False  # Indica que la dosificación falló

    print("[PROCESO] Dosificación de todos los ingredientes completada correctamente.")
    return True  # Indica que la dosificación fue exitosa


def perform_mixing(server: ModbusServer):
    """Simula la etapa de mezclado."""
    print("[PROCESO] Dosificación OK. Mezclando...")
    server.data_bank.set_input_registers(ADDR_PROCESS_STAGE, [STAGE_MIXING])
    sleep(2)


def perform_bagging(server: ModbusServer):
    """Simula la etapa de ensacado y actualiza contadores."""
    print("[PROCESO] Ensacando...")
    server.data_bank.set_input_registers(ADDR_PROCESS_STAGE, [STAGE_BAGGING])

    real_weights_words = server.data_bank.get_input_registers(ADDR_REAL_WEIGHTS_START, NUM_INGREDIENTS * 2)

    total_weight = sum(words_to_float(
        real_weights_words[i*2], real_weights_words[i*2+1]) for i in range(NUM_INGREDIENTS))  # type: ignore

    server.data_bank.set_input_registers(ADDR_TOTAL_WEIGHT, float_to_words(total_weight))

    print(f"[INFO] Saco producido correctamente. Peso total: {total_weight:.2f} kg.")

# --------------------------------------------------------------------------- #
# 5. FUNCIONES DE MANEJO DE ESTADOS Y TRANSICIONES
# --------------------------------------------------------------------------- #


def on_enter_idle(server: ModbusServer):
    """Configura el sistema para el estado IDLE."""
    print("[INFO] Entrando en estado IDLE. Sistema listo.")
    server.data_bank.set_input_registers(ADDR_LINE_STATE, [STATE_IDLE])
    server.data_bank.set_input_registers(ADDR_PROCESS_STAGE, [STAGE_IDLE])
    server.data_bank.set_input_registers(ADDR_ACTIVE_ALARM_CODE, [ALARM_CODE_NONE])


def on_enter_running(server: ModbusServer):
    """Prepara el sistema para un nuevo ciclo de producción."""
    print("\n[INFO] Orden de marcha recibida. Iniciando producción...")
    server.data_bank.set_input_registers(ADDR_LINE_STATE, [STATE_RUNNING])
    # Limpiar registros para el nuevo ciclo
    zeros = [0] * (NUM_INGREDIENTS * 2)
    server.data_bank.set_input_registers(ADDR_REAL_WEIGHTS_START, zeros)
    server.data_bank.set_input_registers(ADDR_TOTAL_WEIGHT, float_to_words(0.0))


def on_enter_alarm(server: ModbusServer):
    """Configura el sistema para el estado de ALARMA."""
    print("[INFO] Entrando en estado de ALARMA. Producción detenida.")
    server.data_bank.set_input_registers(ADDR_LINE_STATE, [STATE_ALARM])


def handle_idle_state(server: ModbusServer) -> int:
    """En IDLE, solo espera la orden de arranque para solicitar un cambio de estado."""
    is_start_order = server.data_bank.get_coils(ADDR_ORDER_START, 1)
    if is_start_order and is_start_order[0] is True:
        server.data_bank.set_coils(ADDR_ORDER_START, [False])
        return STATE_RUNNING
    return STATE_IDLE


def handle_running_state(server: ModbusServer) -> int:
    """Ejecuta el ciclo de producción y solicita cambiar de estado al finalizar o fallar."""
    # Opcional pero recomendado (robustez PLC): reafirmar el estado en cada ciclo.
    server.data_bank.set_input_registers(ADDR_LINE_STATE, [STATE_RUNNING])

    target_weights = read_target_weights(server)
    dosing_success = dose_ingredients(server, target_weights)
    if not dosing_success:
        return STATE_ALARM  # Petición de transición a ALARM

    perform_mixing(server)
    perform_bagging(server)
    return STATE_IDLE  # Petición de transición a IDLE


def handle_alarm_state(server: ModbusServer) -> int:
    """En ALARMA, solo espera la orden de reset para solicitar un cambio de estado."""
    is_reset_order = server.data_bank.get_coils(ADDR_ORDER_RESET, 1)
    if is_reset_order and is_reset_order[0] is True:
        server.data_bank.set_coils(ADDR_ORDER_RESET, [False])
        return STATE_IDLE
    return STATE_ALARM

# --------------------------------------------------------------------------- #
# 6. FUNCIÓN PRINCIPAL Y BUCLE DE SIMULACIÓN (CON GESTOR DE TRANSICIONES)
# --------------------------------------------------------------------------- #


def main():
    server = ModbusServer(host="localhost", port=502, no_block=True)
    try:
        print("Iniciando servidor (VERSIÓN CON TRANSICIONES)...")
        server.start()
        print("¡Servidor en marcha!")

        line_state = STATE_IDLE
        on_enter_idle(server)  # Inicializar el primer estado

        while True:
            previous_state = line_state

            if line_state == STATE_IDLE:
                line_state = handle_idle_state(server)
            elif line_state == STATE_RUNNING:
                line_state = handle_running_state(server)
            elif line_state == STATE_ALARM:
                line_state = handle_alarm_state(server)

            # --- Gestor de Transiciones ---
            # Si el estado ha cambiado, ejecutar la lógica de entrada correspondiente.
            if previous_state != line_state:
                if line_state == STATE_IDLE:
                    on_enter_idle(server)
                elif line_state == STATE_RUNNING:
                    on_enter_running(server)
                elif line_state == STATE_ALARM:
                    on_enter_alarm(server)

            sleep(0.5)

    except Exception as e:
        print(f"Error fatal: {e}")
    finally:
        print("Cerrando el servidor.")
        server.stop()


if __name__ == "__main__":
    main()
