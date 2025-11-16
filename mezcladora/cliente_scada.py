import time
import os
from typing import Any, Optional
from pyModbusTCP.client import ModbusClient
from modbus_utils import float_to_words, words_to_float

# --------------------------------------------------------------------------- #
# 1. EL MAPA DE REGISTROS Y CONSTANTES
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

SERVER_HOST = "localhost"
SERVER_PORT = 502

# --------------------------------------------------------------------------- #
# 2. DEFINICIONES DE ESTADOS, RECETAS Y MAPAS
# --------------------------------------------------------------------------- #
# --- Constantes de Estado (Protocolo) ---
STATE_IDLE = 0
STATE_RUNNING = 1
STATE_ALARM = 99

# --- Mapas de Visualización (UI) ---
RECIPES: dict[str, dict[str, Any]] = {
    "1": {"name": "Pollo y Arroz (Básico)", "weights": [25.0, 25.0, 0.0, 0.0, 0.0]},
    "2": {"name": "Salmón y Patata (Premium)", "weights": [20.5, 15.0, 5.5, 0.0, 0.0]},
    "3": {"name": "Cachorro (Completo)", "weights": [15.0, 10.0, 10.0, 8.5, 2.0]}
}
STATE_MAP = {STATE_IDLE: "PARADO", STATE_RUNNING: "EN PRODUCCIÓN", STATE_ALARM: "ALARMA"}
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
# 3. FUNCIONES DE INTERFAZ DE USUARIO (UI)
# --------------------------------------------------------------------------- #


def ui_display_main_menu() -> str:
    """Muestra el menú principal y devuelve la opción elegida por el usuario."""
    print("\n" + "="*50)
    print("--- MENÚ PRINCIPAL ---")
    print("1. Producir un saco")
    print("2. Salir")
    return input("Selecciona una opción: ")


def ui_select_recipe() -> Optional[dict[str, Any]]:
    """Muestra el menú de recetas y devuelve la receta seleccionada o None si es inválida."""
    print("\n--- SELECCIÓN DE RECETA ---")
    for key, recipe in RECIPES.items():
        print(f"  [{key}] {recipe['name']}")
    choice = input("Por favor, selecciona el número de la receta a producir: ")
    selected_recipe = RECIPES.get(choice)
    if not selected_recipe:
        print("Selección no válida.")
        return None
    print(f"Has seleccionado: {selected_recipe['name']}")
    return selected_recipe


def ui_display_scada_panel(data: dict[str, Any], recipe: dict[str, Any]):
    """Limpia la pantalla y muestra el panel de control con datos en tiempo real."""
    os.system('cls' if os.name == 'nt' else 'clear')
    print("--- PANEL DE CONTROL ---")
    print(f"ESTADO GENERAL: {STATE_MAP.get(data['line_state'], 'Desconocido')}")
    print(f"ETAPA ACTUAL:   {STAGE_MAP.get(data['process_stage'], 'Desconocida')}")
    print("---------------------------------------------")
    print("PESOS EN TIEMPO REAL (Real / Objetivo):")
    recipe_weights: list[float] = recipe['weights']
    for i in range(NUM_INGREDIENTS):
        indicator = " <-- Proceso" if data['process_stage'] == (1 + i) else ""
        print(f"  - Ingrediente #{i+1}: {data['real_weights'][i]:.2f} / {recipe_weights[i]:.2f} kg {indicator}")
    print("---------------------------------------------")

# --------------------------------------------------------------------------- #
# 4. FUNCIONES DE COMUNICACIÓN CON EL PLC
# --------------------------------------------------------------------------- #


def plc_connect(host: str, port: int) -> Optional[ModbusClient]:
    """Intenta conectar con el servidor Modbus y devuelve el objeto cliente si tiene éxito."""
    print(f"Conectando a la planta en {host}:{port}...")
    client = ModbusClient(host=host, port=port)
    if not client.open():
        print(f"Error: No se pudo conectar. ¿Está el servidor en marcha?")
        return None
    print("¡Conexión exitosa!")
    return client


def plc_send_recipe(client: ModbusClient, recipe_weights: list[float]) -> bool:
    """Convierte los pesos de la receta y los envía al PLC."""
    target_weights_words = []
    for weight in recipe_weights:
        target_weights_words.extend(float_to_words(weight))
    print("Enviando parámetros de la receta al PLC...")
    if not client.write_multiple_registers(ADDR_TARGET_WEIGHTS_START, target_weights_words):
        print("Error: No se pudo escribir la receta en el PLC.")
        return False
    return True


def plc_read_live_data(client: ModbusClient) -> Optional[dict[str, Any]]:
    """Lee todos los datos relevantes del PLC y los devuelve en un diccionario estructurado."""
    state_regs: list[int] = client.read_input_registers(ADDR_LINE_STATE, 3)  # type: ignore
    weight_regs: list[int] = client.read_input_registers(ADDR_REAL_WEIGHTS_START, NUM_INGREDIENTS * 2)  # type: ignore

    if not all([state_regs, weight_regs]):
        print("Error: No se pudo leer el estado completo. Reintentando...")
        return None

    data = {
        "line_state": state_regs[0],
        "process_stage": state_regs[1],
        "active_alarm_code": state_regs[2],
        "real_weights": [words_to_float(weight_regs[i*2], weight_regs[i*2+1]) for i in range(NUM_INGREDIENTS)]
    }
    return data

# --------------------------------------------------------------------------- #
# 5. LÓGICA DE CONTROL DE PROCESO
# --------------------------------------------------------------------------- #


def monitor_production(client: ModbusClient, selected_recipe: dict[str, Any]):
    """Bucle principal que monitoriza un ciclo de producción hasta que termina o hay una alarma."""
    has_started_working = False
    while True:
        live_data = plc_read_live_data(client)
        if not live_data:
            time.sleep(2)
            continue

        ui_display_scada_panel(live_data, selected_recipe)

        line_state = live_data["line_state"]
        if line_state == STATE_RUNNING:
            has_started_working = True

        if line_state == STATE_ALARM:
            alarm_code = live_data["active_alarm_code"]
            alarm_message = ALARM_MAP.get(alarm_code, f"Alarma desconocida (Código: {alarm_code})")
            print(f"\n\n¡¡¡ ALARMA DETECTADA !!!\nMOTIVO: {alarm_message}")
            input("Presiona Enter para RECONOCER y RESETEAR la alarma...")
            client.write_single_coil(ADDR_ORDER_RESET, True)
            print("Enviando orden de reset al PLC...")
            time.sleep(1.5)
            break

        if has_started_working and line_state == STATE_IDLE:
            print("\n\nSaco procesado. Volviendo al menú principal.")
            time.sleep(2)
            break

        print("\n(Presiona Ctrl+C para detener el SCADA)")
        time.sleep(1)


def run_production_cycle(client: ModbusClient):
    """Orquesta la secuencia completa para producir un saco: seleccionar, enviar y monitorizar."""
    selected_recipe = ui_select_recipe()
    if not selected_recipe:
        return

    recipe_weights: list[float] = selected_recipe['weights']
    if not plc_send_recipe(client, recipe_weights):
        return

    input("\nPresiona Enter para dar la ORDEN DE MARCHA...")
    client.write_single_coil(ADDR_ORDER_START, True)

    monitor_production(client, selected_recipe)

# --------------------------------------------------------------------------- #
# 6. FUNCIÓN PRINCIPAL
# --------------------------------------------------------------------------- #


def main():
    """Punto de entrada principal del programa cliente."""
    client = plc_connect(SERVER_HOST, SERVER_PORT)
    if not client:
        return

    try:
        while True:
            choice = ui_display_main_menu()
            if choice == '1':
                run_production_cycle(client)
            elif choice == '2':
                break
            else:
                print("Opción no válida, por favor intenta de nuevo.")
                time.sleep(1)

    except KeyboardInterrupt:
        print("\nSCADA detenido por el usuario.")
    except Exception as e:
        print(f"Error fatal: {e}")
    finally:
        if client and client.is_open:
            print("Cerrando conexión con la planta.")
            client.close()


if __name__ == "__main__":
    main()
