# Simulación de Proceso Industrial con Modbus TCP

Este proyecto simula un proceso industrial simplificado de mezclado y ensacado de ingredientes para fabricar pienso. La comunicación entre la maquinaria (el "PLC") y el panel de control del operador (el "SCADA/HMI") se realiza utilizando el protocolo estándar industrial **Modbus TCP**.

El objetivo de esta práctica es entender los fundamentos de la comunicación industrial, la arquitectura cliente-servidor y la programación de máquinas de estado, que son la base de la automatización.

¡Hecho! Es una excelente adición, ya que resalta una de las habilidades clave de desarrollo de software que se practican aquí.

Aquí está la sección de objetivos actualizada con el nuevo punto añadido:

---

## Objetivos de la Práctica
-   Comprender la diferencia entre un cliente y un servidor en un entorno industrial.
-   Familiarizarse con el concepto de registros Modbus como método de intercambio de datos.
-   Implementar y entender el funcionamiento de una máquina de estados para controlar un proceso.
-   Apreciar la importancia de separar la lógica de control (servidor) de la interfaz de usuario (cliente).
-   Utilizar **YAML** para externalizar la configuración de una aplicación, mejorando su mantenibilidad y legibilidad.

## Componentes del Proyecto

El proyecto se divide en tres scripts principales que deben ejecutarse simultáneamente:

1.  `servidor_plc.py` (El PLC / Autómata)
2.  `cliente_scada.py` (El SCADA / HMI)
3.  `modbus_utils.py` (Funciones de utilidad compartidas)

### 1. `servidor_plc.py`: El Cerebro de la Máquina (PLC)

Piensa en el `servidor_plc.py` como el **Controlador Lógico Programable (PLC)** que está conectado directamente a los motores, sensores y actuadores de la fábrica. Su rol es ejecutar la lógica de control y exponer sus datos a través de Modbus.

### 2. `cliente_scada.py`: El Panel de Control (SCADA/HMI)

Piensa en el `cliente_scada.py` como la **Interfaz Humano-Máquina (HMI)** o el panel de control que un operario usaría en la planta para manejar la máquina. Su rol es conectarse al PLC para leer datos y enviar comandos.

## El Protocolo de Comunicación: Mapa de Registros Modbus

La comunicación se basa en un "contrato" predefinido: el **mapa de registros Modbus**.

| Dirección | Nombre del Registro         | Tipo        | Acceso desde Cliente (SCADA) | Descripción                                                     |
| :-------- | :-------------------------- | :---------- | :--------------------------- | :-------------------------------------------------------------- |
| **Coils** |                             |             |                              |                                                                 |
| `0`       | `ADDR_ORDER_START`          | Booleano    | Escritura                    | El SCADA pone a `True` para iniciar la producción.              |
| `1`       | `ADDR_ORDER_RESET`          | Booleano    | Escritura                    | El SCADA pone a `True` para resetear una alarma.                |
| **Input Registers (Solo Lectura)** |    |             |                              |                                                                 |
| `100`     | `ADDR_LINE_STATE`           | Entero 16b  | Lectura                      | Estado de la máquina (0: IDLE, 1: RUN, 99: ALARM).               |
| `101`     | `ADDR_PROCESS_STAGE`        | Entero 16b  | Lectura                      | Etapa del proceso (Dosificando, Mezclando...).                  |
| `102`     | `ADDR_ACTIVE_ALARM_CODE`    | Entero 16b  | Lectura                      | Código de la alarma activa.                                     |
| `300-309` | `ADDR_REAL_WEIGHTS_START`   | Floats (32b)| Lectura                      | Pesos reales de los 5 ingredientes (valor simulado por el PLC). |
| `400-401` | `ADDR_TOTAL_WEIGHT`         | Float (32b) | Lectura                      | Peso total del último saco producido.                           |
| **Holding Registers (Lectura/Escritura)** | |           |                              |                                                                 |
| `200-209` | `ADDR_TARGET_WEIGHTS_START` | Floats (32b)| Escritura                    | Pesos objetivo de la receta enviados por el SCADA.              |

## Cómo Ejecutar la Simulación

### Prerrequisitos

Necesitas tener Python 3 instalado. Luego, instala las librerías `pyModbusTCP` y `pyyaml` (necesaria para la Fase 1):

```bash
pip install pyModbusTCP pyyaml
```

### Instrucciones

1.  **Abre dos terminales o consolas.**
2.  **En la Terminal 1, inicia el servidor (el PLC):**
    ```bash
    python servidor_plc.py
    ```
3.  **En la Terminal 2, inicia el cliente (el SCADA):**
    ```bash
    python cliente_scada.py
    ```

---

## Fases de la Práctica

### Fase 1: Centralización de la Configuración con YAML

**Objetivo:** Refactorizar el código para externalizar todas las constantes (direcciones Modbus, parámetros de simulación, estados, etc.) a un único archivo de configuración `config.yaml`.

#### Una Breve Introducción a YAML

Ya conoces JSON, que usa llaves `{}` y comillas para definir objetos y sus valores. **YAML** es otro formato para estructurar datos, muy popular para archivos de configuración por ser más fácil de leer para los humanos.

El acrónimo **YAML** esconde una curiosidad: originalmente significaba *"Yet Another Markup Language"* (Otro Lenguaje de Marcado Más). Sin embargo, para destacar que su verdadero propósito es la **serialización de datos** (como JSON) y no el marcado de documentos (como HTML), su significado se redefinió oficialmente a un acrónimo recursivo: **"YAML Ain't Markup Language"** (YAML No Es un Lenguaje de Marcado).

La principal diferencia con JSON es que YAML usa la **indentación** (espacios) para definir la estructura, en lugar de llaves y comas. Compara el mismo objeto en ambos formatos:

**JSON:**
```json
{
  "modbus": {
    "host": "localhost",
    "port": 502
  }
}
```

**YAML:**
```yaml
# Este es un comentario que explica la sección
modbus:
  host: "localhost"
  port: 502
```

Fíjate en las diferencias clave:
-   **No hay llaves `{}` ni comas**: La estructura de anidamiento se define por los espacios al inicio de la línea.
-   **Más legible**: Al eliminar la "basura" sintáctica, el resultado es más limpio.
-   **Permite comentarios**: Las líneas que empiezan con `#` son comentarios, algo que JSON no permite y que es extremadamente útil en archivos de configuración para documentar cada parámetro.

Lo usamos aquí para introducirte a este formato tan común y porque, gracias a su legibilidad y a los comentarios, nuestro `config.yaml` será más fácil de entender y mantener.


#### Pasos a seguir:

1.  **Crear `config.yaml`**: Crea un archivo `config.yaml` que contenga todas las constantes. Organízalas de forma lógica (ej. secciones para `modbus`, `registers`, `states`, etc.).

2.  **Modificar los Scripts**: Al inicio de `servidor_plc.py` y `cliente_scada.py`, importa `yaml`, lee el archivo de configuración y reemplaza las constantes "hard-codeadas" por los valores del diccionario de configuración (ej. `config['registers']['order_start']` en lugar de `ADDR_ORDER_START`).

#### ⚠️ Importante: Simulación vs. Realidad

En un entorno industrial real, **NO** se compartiría un archivo `.yaml`. Esta refactorización es una buena práctica de desarrollo de software para esta simulación, pero es crucial entender cómo difiere del mundo real:
-   **PLC**: Su mapa de registros está programado con software específico del fabricante (ej. Siemens TIA Portal) y se compila en un formato propietario.
-   **SCADA**: Su "base de datos de tags" se configura dentro del propio software SCADA, apuntando manualmente a las direcciones del PLC.
-   **Dispositivos de Campo (ej. una báscula)**: Su mapa de registros es **fijo e inalterable**, definido por el fabricante en su firmware.

Usamos YAML aquí por conveniencia didáctica y para asegurar que nuestro PLC y SCADA simulados estén siempre sincronizados durante el desarrollo.

---

### Fase 2: Producción por Lotes y Contadores

**Objetivo:** Añadir la funcionalidad de producir un número determinado de sacos (un lote) y mostrar los contadores de producción. Esta fase se construye sobre el código refactorizado de la Fase 1.

#### Pasos a seguir:

1.  **Ampliar `config.yaml`**: Define las nuevas direcciones Modbus que necesitarás para los contadores y el objetivo del lote. Por ejemplo:
    ```yaml
    # En la sección de 'registers' del config.yaml
    target_sacks_goal: 500  # Objetivo de sacos a producir
    ok_sacks_counter: 502   # Contador de sacos buenos
    bad_sacks_counter: 504  # Contador de sacos malos
    ```

2.  **Modificaciones en `servidor_plc.py` (PLC)**:
    -   **Lógica de Lote**: El PLC debe leer el objetivo de sacos a producir del nuevo registro.
    -   **Bucle de Producción**: La máquina de estados debe ser modificada. En lugar de volver a `STATE_IDLE` después de un saco, debe iniciar otro ciclo si aún no ha alcanzado el objetivo. Solo volverá a `IDLE` al completar el lote.
    -   **Implementar Contadores**: El PLC debe llevar la cuenta interna de sacos OK y sacos NOK. Después de cada ciclo, debe actualizar los registros `ok_sacks_counter` y `bad_sacks_counter`.

3.  **Modificaciones en `cliente_scada.py` (SCADA)**:
    -   **Entrada de Usuario**: Antes de enviar la orden de marcha, pregunta al usuario: `"¿Cuántos sacos desea producir? (1-10)"`.
    -   **Enviar Objetivo del Lote**: Escribe el número introducido por el usuario en el registro `target_sacks_goal` del PLC.
    -   **Visualización Mejorada**: Modifica el panel SCADA para que lea y muestre los nuevos contadores. Debería verse algo así:
        ```
        PROGRESO DEL LOTE: 3 / 10
          - Sacos Buenos: 2
          - Sacos Malos:  1
        ```
