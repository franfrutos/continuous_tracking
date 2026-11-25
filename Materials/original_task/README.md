# MIB Experiment

Repositorio principal para la tarea bloqueada de Motion-Induced Blindness (MIB) en PsychoPy.

## Ejecucion

Desde la raiz del proyecto:

```powershell
conda env create -f environment.yml
conda activate mib-psychopy
python .\run_mib_blocked.py --mode test
python .\run_mib_blocked.py --mode full
```

Tambien puedes lanzar la tarea con doble clic desde Windows:
- `Lanzar_MIB_Completo.bat`
- `Lanzar_MIB_Test.bat`

Estos lanzadores buscan `conda`, usan el entorno `mib-psychopy` y ejecutan `run_mib_blocked.py` sin necesidad de escribir comandos en terminal.

`psychtoolbox` no es requisito para ejecutar la tarea.

## Configuracion rapida

Para cambiar ajustes frecuentes sin tocar el script principal, edita:

- [mib_config.py](/C:/Users/User/OneDrive/Escritorio/Task%20programming/PsychoPy/MIB_experiment/mib_config.py)

Por ejemplo, para cambiar el puerto serie del potenciómetro:

```python
MIB_DEVICE_SERIAL_PORT = "COM7"
```

Las variables de entorno, si se usan, siguen teniendo prioridad sobre `mib_config.py`.

## Estructura del protocolo

La tarea tiene tres bloques experimentales:
- `button`
- `potentiometer`
- `tet`

Los tres bloques se contrabalancean. Como hay 3 bloques, hay 6 ordenes posibles (`3!`), asignados de forma reproducible con `participant_id modulo 6`.

Ejemplos de `assigned_order`:
- `button__potentiometer__tet`
- `button__tet__potentiometer`
- `potentiometer__button__tet`
- `potentiometer__tet__button`
- `tet__button__potentiometer`
- `tet__potentiometer__button`

El orden asignado se guarda en `session_summary` y, en full mode, tambien en `counterbalance_assignments.csv`.

## Ensayos por bloque

Full mode:
- `BLOCK_SIZE = 12`
- `TRIAL_DURATION = 30 s`
- composicion por bloque: `8 peripheral`, `0 no_target`, `4 control`

Test mode:
- mantiene los tres bloques y el mismo flujo general
- `BLOCK_SIZE = 2`
- composicion por bloque: `1 peripheral`, `0 no_target`, `1 control`
- `PRACTICE_TRIALS_PER_BLOCK = 1`
- calibracion continua: `1 calibration_up`, `1 calibration_down`, `1 calibration_sinusoidal`
- `TRIAL_DURATION = 30 s`

## Practicas y calibracion

Full mode:
- antes de cada bloque hay 5 ensayos de practica (`PRACTICE_TRIALS_PER_BLOCK = 5`)
- el bloque `potentiometer` incluye una calibracion inmediatamente antes del bloque experimental:
  - `2 x calibration_up`
  - `2 x calibration_down`
  - `2 x calibration_sinusoidal`

Test mode:
- antes de cada bloque hay 1 ensayo de practica (`PRACTICE_TRIALS_PER_BLOCK = 1`)
- el bloque `potentiometer` incluye una calibracion inmediatamente antes del bloque experimental:
  - `1 x calibration_up`
  - `1 x calibration_down`
  - `1 x calibration_sinusoidal`

La calibracion se guarda en datos como `phase = calibration`, pero no cuenta como bloque experimental.

## Datos

`MIB_DATA_DIR` sigue siendo la carpeta raiz configurable. Por defecto es `data/`.

Los datos de cada participante se guardan en:

```text
data/
└── participant_<participant_id>/
    ├── session_summary_p<participant_id>.csv
    ├── trial_summary_p<participant_id>.csv
    ├── continuous_responses_p<participant_id>.csv
    ├── button_events_p<participant_id>.csv
    └── tet_traces_p<participant_id>.csv
```

`counterbalance_assignments.csv` se mantiene en la raiz de `data/` (o `MIB_DATA_DIR`).

Importante: como los nombres ya no incluyen `SESSION_ID`, volver a ejecutar la tarea con el mismo `participant_id` sobrescribira los archivos previos de ese participante.

## Notas de respuesta

- En `button`, la persona mantiene `ESPACIO` pulsada mientras no percibe el punto blanco y la suelta cuando vuelve a percibirlo.
- En `potentiometer`, la respuesta continua se registra como serie temporal en `continuous_responses`.
- En `tet`, cada ensayo incluye 30 s de presentacion y despues un trazado de visibilidad.
- `button` y `potentiometer` se guardan a la misma frecuencia fija en `continuous_responses`.
- `tet_traces` se remuestrea a esa misma rejilla temporal fija para que los tres metodos sean comparables por ensayo.

Los ensayos de control se pueden configurar con `MIB_CONTROL_TRIAL_MODE`:
- `static_mask`: target periferico normal con mascara estatica.
- `near_fixation`: target muy cercano al punto de fijacion, en el mismo angulo que el target periferico.

El valor por defecto es `near_fixation`.

La excentricidad del control cercano a fijacion se controla con `MIB_CONTROL_TARGET_ECC_CM` y por defecto es `1.0 cm` (aprox. `1º` a 57.3 cm).

La composicion experimental por bloque se puede fijar desde `mib_config.py` con:
- `MIB_PERIPHERAL_TRIALS_PER_BLOCK`
- `MIB_NO_TARGET_TRIALS_PER_BLOCK`
- `MIB_CONTROL_TRIALS_PER_BLOCK`

Si `MIB_NO_TARGET_TRIALS_PER_BLOCK = 0`, no se muestran ensayos `no_target`.

En `test mode`, si alguna vez hace falta, existen tambien:
- `MIB_TEST_PERIPHERAL_TRIALS_PER_BLOCK`
- `MIB_TEST_NO_TARGET_TRIALS_PER_BLOCK`
- `MIB_TEST_CONTROL_TRIALS_PER_BLOCK`

La configuracion actual por defecto deja:
- Full mode: `8 peripheral`, `0 no_target`, `4 control`
- Test mode: `1 peripheral`, `0 no_target`, `1 control`

## Documentacion adicional

- `mib_blocked/README.md`
- `mib_blocked/INSTRUCTIONS.md`
- `DATA_DICTIONARY.md`
