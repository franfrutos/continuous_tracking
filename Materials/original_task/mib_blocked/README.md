# Blocked MIB Task

Implementacion principal de la tarea MIB.

## Configuracion

La forma mas sencilla de cambiar parametros frecuentes es editar:

- [mib_config.py](/C:/Users/User/OneDrive/Escritorio/Task%20programming/PsychoPy/MIB_experiment/mib_config.py)

Para especificar el puerto del potenciómetro, por ejemplo:

```python
MIB_DEVICE_SERIAL_PORT = "COM7"
```

Si tambien defines variables de entorno, estas tienen prioridad sobre el archivo de configuracion.

## Bloques experimentales

La sesion incluye tres bloques comparables:
- `button`
- `potentiometer`
- `tet`

Los tres bloques se contrabalancean con las 6 permutaciones posibles. El orden se asigna a partir de `participant_id modulo 6` y se guarda como `assigned_order`.

## Flujo por bloque

- `button`: instrucciones -> 5 practicas -> pausa -> 20 ensayos experimentales
- `potentiometer`: instrucciones -> calibracion -> 5 practicas -> pausa -> 20 ensayos experimentales
- `tet`: instrucciones -> 5 practicas -> pausa -> 20 ensayos experimentales

En test mode se mantiene el mismo flujo y la misma duracion de ensayo, pero con `BLOCK_SIZE = 2`, `PRACTICE_TRIALS_PER_BLOCK = 1` y una calibracion por tipo (`up`, `down`, `sinusoidal`).

## Parametros principales

Full mode:
- `TRIAL_DURATION = 30 s`
- `TET_EXPERIMENTAL_DISPLAY_DURATION = 30 s`
- `BLOCK_SIZE = 12`
- `PRACTICE_TRIALS_PER_BLOCK = 5`
- composicion experimental por defecto actual: `8 peripheral`, `0 no_target`, `4 control`

Test mode:
- `TRIAL_DURATION = 30 s`
- `BLOCK_SIZE = 2`
- `PRACTICE_TRIALS_PER_BLOCK = 1`
- composicion experimental por defecto actual: `1 peripheral`, `0 no_target`, `1 control`
- calibracion continua: `1 calibration_up`, `1 calibration_down`, `1 calibration_sinusoidal`

## Ensayos de control

Los controles se configuran con `MIB_CONTROL_TRIAL_MODE`:
- `static_mask`: target periferico normal, misma posicion periferica, pero mascara estatica (`mask_motion = static`)
- `near_fixation`: target cercano a fijacion, en el mismo angulo que el target periferico

La excentricidad del control `near_fixation` se configura con `MIB_CONTROL_TARGET_ECC_CM` y por defecto es `1.0 cm`.
El modo de control por defecto es `near_fixation`.

La composicion experimental tambien se puede fijar por separado desde `mib_config.py`:
- Full mode: `MIB_PERIPHERAL_TRIALS_PER_BLOCK`, `MIB_NO_TARGET_TRIALS_PER_BLOCK`, `MIB_CONTROL_TRIALS_PER_BLOCK`
- Test mode: `MIB_TEST_PERIPHERAL_TRIALS_PER_BLOCK`, `MIB_TEST_NO_TARGET_TRIALS_PER_BLOCK`, `MIB_TEST_CONTROL_TRIALS_PER_BLOCK`

Si `MIB_NO_TARGET_TRIALS_PER_BLOCK = 0`, no se muestran ensayos `no_target`.

## Pausa tras cada ensayo

Despues de cada ensayo aparece:

`Has terminado este ensayo. Pulsa Y para continuar.`

## TET

Cada ensayo TET:
1. Presenta el estimulo durante `30 s` en full mode.
2. Abre la pantalla de trazado.

Reglas del trazado:
- `normalized_time` y `normalized_visibility` quedan en `0..1`
- dibujar por encima o por debajo de la grafica se recorta al maximo o minimo permitido
- no se acepta terminar si el trazado no llega suficientemente al borde derecho
- la tolerancia se controla con `TET_COMPLETION_TOLERANCE`

## Datos

La carpeta raiz sigue siendo `MIB_DATA_DIR` (por defecto `data/`).

Cada participante se guarda en:

```text
data/participant_<participant_id>/
```

Dentro de esa carpeta:
- `session_summary_p<participant_id>.csv`
- `trial_summary_p<participant_id>.csv`
- `continuous_responses_p<participant_id>.csv`
- `button_events_p<participant_id>.csv`
- `tet_traces_p<participant_id>.csv`

El archivo acumulativo `counterbalance_assignments.csv` queda en la raiz de `data/` o `MIB_DATA_DIR`.

Nota: si se vuelve a ejecutar la tarea con el mismo `participant_id`, estos archivos se sobrescriben porque ya no incluyen `SESSION_ID` en el nombre.

Comparabilidad temporal:
- `button` y `potentiometer` se guardan en `continuous_responses` con la misma rejilla temporal fija.
- `tet_traces` se remuestrea a esa misma frecuencia (`MIB_RESPONSE_LOG_HZ`) para que el numero de filas por ensayo sea comparable entre metodos de igual duracion.

## Potenciometro

Por defecto `MIB_DEVICE_RATING` esta activado.

Ejemplo:

```powershell
$env:MIB_DEVICE_RATING = "1"
$env:MIB_DEVICE_SERIAL_PORT = "COM5"
$env:MIB_DEVICE_SERIAL_BAUD = "115200"
$env:MIB_DEVICE_QUERY_CHAR = "R"
$env:MIB_DEVICE_LEVEL_MIN = "0"
$env:MIB_DEVICE_LEVEL_MAX = "4095"
python .\run_mib_blocked.py --mode full
```
