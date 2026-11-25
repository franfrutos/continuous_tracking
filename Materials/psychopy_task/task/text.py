"""
Texts of the task in Spanish, as the participants read them.
"""

# =============================================================================
# Start of the session
# =============================================================================

WELCOME = (
    "Vas a realizar una tarea en la que nos interesa cómo percibes la visibilidad de un estímulo que aparecerá en "
    "pantalla.\n"
    "En algunas condiciones, la visibilidad de ese estímulo puede fluctuar a lo largo del tiempo.\n"
    "Durante toda la tarea debes mantener la mirada en el punto de fijación central.\n"
    "A lo largo del experimento te pediremos que informes de la visibilidad del estímulo de distintas maneras, según "
    "se te indique en cada parte.\n\n"
    "Pulsa ESPACIO para continuar.")

# Static example of the display
EXAMPLE_TITLE = (
    "A continuación verás un ejemplo estático de la pantalla.\n"
    "Tu tarea consistirá en informar de la visibilidad del estímulo blanco.\n"
    "Aunque ese estímulo aparezca en la periferia, debes mantener la mirada en todo momento en el punto de fijación "
    "central.")
EXAMPLE_TARGET = "Estímulo blanco"
EXAMPLE_FIXATION = "Punto de fijación"
EXAMPLE_FOOTER = "Pulsa ESPACIO para continuar."

# Demonstration
DEMO_INTRO = (
    "A continuación verás un ensayo breve de demostración.\n"
    "Mantén la mirada en el punto central.\n"
    "Durante esta parte no tienes que responder.\n\n"
    "Pulsa ESPACIO para empezar.")
DEMO_END = "Has terminado la demostración.\n\nPulsa Y para continuar."

# =============================================================================
# Between trials and blocks
# =============================================================================

TRIAL_END = "Has terminado este ensayo.\n\nPulsa Y para continuar."
TRIAL_END_REMINDER = "Has terminado este ensayo.\n\n{}\n\nPulsa Y para continuar."
PRACTICE_START = "{}\n\nPulsa ESPACIO para empezar la práctica."
PRACTICE_END = "Has terminado la práctica.\n\nA continuación empezará el bloque experimental.\n\n{}"
READY_FIRST_TRIAL = "Pulsa Y cuando estés listo/a para comenzar el primer ensayo."
BLOCK_END = ("Has terminado esta parte de la tarea.\n\n"
             "Por favor, avisa al experimentador.\n\n"
             "Pulsa Y cuando te indiquen que puedes continuar.")
GOODBYE = "La tarea ha terminado. Puedes llamar al experimentador.\n\nGracias por participar.\n\nPulsa ESPACIO para salir."

# =============================================================================
# Button
# =============================================================================

BUTTON_TITLE = ("En esta parte de la tarea, debes indicar si percibes o no el punto blanco.\n"
                "Mantén la mirada en el punto central durante todos los ensayos.")
BUTTON_EMPHASIS = "Pulsa y mantén ESPACIO mientras NO PERCIBAS EL PUNTO BLANCO."
BUTTON_FOOTER = "Suelta ESPACIO cuando vuelva a ser visible.\nPulsa ESPACIO para continuar."

BUTTON_PRACTICE_TITLE = ("Primero vamos a realizar unos ensayos de práctica.\n"
                         "Mantén la mirada en el punto central en todo momento.")
BUTTON_PRACTICE_EMPHASIS = ("Recuerda: mantén pulsada la tecla ESPACIO\n"
                            "mientras no percibas el estímulo blanco.")
BUTTON_PRACTICE_FOOTER = ("Suelta ESPACIO cuando el estímulo vuelva a ser visible.\n\n"
                          "Pulsa ESPACIO para empezar la práctica.")
BUTTON_PRACTICE_NEXT = "Has terminado este ensayo.\n\nPulsa Y para continuar el próximo ensayo de práctica."

# =============================================================================
# Slider (the participants read "potenciómetro")
# =============================================================================

SLIDER_INTRO = ("En esta parte de la tarea, debes ajustar la respuesta de forma continua para reflejar cómo cambia la "
                "visibilidad del estímulo.\n"
                "Mantén la mirada en el punto central durante todos los ensayos.\n"
                "{}\n"
                "La parte alta de la escala corresponde a más visibilidad y la parte baja a menos visibilidad.\n"
                "{}"
                "Primero realizarás una breve calibración y, después, harás varios ensayos de práctica.\n\n"
                "Pulsa ESPACIO para continuar.")
SLIDER_HOW = {"device": "Usa el potenciómetro para indicar cuánta visibilidad percibes.",
              "keyboard": "Usa las teclas UP y DOWN para indicar cuánta visibilidad percibes."}
SLIDER_KEYS = {"device": "",
               "keyboard": "Si usas el teclado, la tecla UP indica más visibilidad y la tecla DOWN menos visibilidad.\n"}

SLIDER_DEMO = {"device": ("Antes de empezar, prueba a mover el potenciómetro para ver cómo funciona.\n\n"
                          "A medida que lo muevas, verás cambiar el indicador de la derecha.\n\n"
                          "Pulsa ESPACIO para continuar."),
               "keyboard": ("Antes de empezar, prueba a mover la respuesta para ver cómo funciona.\n\n"
                            "Usa las teclas UP y DOWN para cambiar el indicador de la derecha.\n\n"
                            "Pulsa ESPACIO para continuar.")}

# Response bar (shown in the demo and in the calibration)
BAR_LABEL = "Visibilidad"
BAR_TOP = "Veo el estímulo\ncon total claridad"
BAR_BOTTOM = "No veo\nel estímulo"

# Calibration
CALIBRATION_INTRO = ("Ahora vamos a realizar unos ensayos de calibración para que aprendas a usar el potenciómetro.\n"
                     "Durante estos ensayos tendrás que ajustar la respuesta para seguir los cambios de visibilidad "
                     "del punto.\n"
                     "Mantén la mirada en el centro en todo momento.\n\n"
                     "Pulsa ESPACIO para continuar.")
_FOLLOW = "\nMantén la mirada en el centro y ajusta la respuesta para seguir la visibilidad del punto."
CALIBRATION_TRIAL = {
    "calibration_up": "En este ensayo, la intensidad del punto blanco irá subiendo desde la mínima intensidad hasta la máxima intensidad." + _FOLLOW,
    "calibration_down": "En este ensayo, la intensidad del punto blanco irá bajando desde la máxima intensidad hasta la mínima intensidad." + _FOLLOW,
    "calibration_sinusoidal": "En este ensayo, la intensidad del punto blanco irá bajando y subiendo de intensidad." + _FOLLOW}
CALIBRATION_END = "Has terminado la calibración.\n\nPulsa ESPACIO para continuar."

# Position of the slider before a trial
PLACE_SLIDER = {"low": ("Antes de empezar, coloca el potenciómetro en la posición más baja.\n"
                        "Cuando lo tengas abajo del todo, pulsa ESPACIO para empezar."),
                "high": ("Antes de empezar, coloca el potenciómetro en la posición más alta.\n"
                         "Cuando lo tengas arriba del todo, pulsa ESPACIO para empezar.")}
PLACE_NEXT = {"low": "Antes del siguiente ensayo, vuelve a colocar el potenciómetro en la posición más baja.",
              "high": "Antes del siguiente ensayo, vuelve a colocar el potenciómetro en la posición más alta."}
START_TRIAL = "Pulsa ESPACIO para empezar."
SLIDER_READY = "Antes de empezar, coloca el potenciómetro en la posición más alta.\n\nPulsa Y para continuar."

# Practice
SLIDER_PRACTICE = (
    "Ahora vamos a realizar unos ensayos de práctica con el potenciómetro.\n"
    "Durante estas prácticas, ajusta la respuesta de forma continua para reflejar cuánta visibilidad percibes. "
    "Si percibes la intensidad máxima, lleva el potenciómetro hasta el tope de arriba del todo. "
    "Si percibes la intensidad mínima, lleva el potenciómetro hasta el tope de abajo del todo. "
    "Realiza los movimientos tan bruscamente o tan progresivamente como tu visibilidad cambie.")

# =============================================================================
# TET
# =============================================================================

TET_INTRO = (
    "En este bloque, primero observarás el estímulo durante {:.0f} segundos y, después, dibujarás cómo cambió su "
    "visibilidad a lo largo del tiempo.\n"
    "Antes de empezar el bloque experimental harás varios ensayos de práctica.\n\n"
    "El dibujo se hará sobre unos ejes.\n"
    "El eje horizontal representa el tiempo y el eje vertical representa la visibilidad.\n"
    "La parte alta indica más visibilidad y la parte baja menos visibilidad.\n"
    "Es importante que lleves la línea hasta el final del eje temporal antes de terminar.\n\n"
    "Pulsa ESPACIO para continuar.")

# Trying the graph before the practice
TET_GRAPH_INTRO = (
    "Antes de empezar las prácticas, vas a ver un ejemplo de la gráfica en la que tendrás que dibujar.\n"
    "Puedes probar cómo se dibuja la línea con el ratón y familiarizarte con los ejes.\n"
    "Puedes borrar tantas veces como desees.\n"
    "Cuando quieras, completa el trazado hasta el final y pulsa ENTER.\n\n"
    "Pulsa ESPACIO para continuar.")
TET_GRAPH_END = "Has terminado esta prueba de la gráfica.\n\nPulsa ESPACIO para continuar."

TET_PRACTICE = (
    "Ahora vamos a realizar unos ensayos de práctica.\n"
    "En cada uno de ellos observarás primero el estímulo durante {:.0f} segundos y, después, tendrás que dibujar de la "
    "manera más fiel posible cómo cambió su visibilidad a lo largo del tiempo.")
TET_PRACTICE_NEXT = "Has terminado este ensayo de práctica.\n\nPulsa Y para continuar."
TET_READY = "Pulsa Y cuando estés listo/a para continuar."

TET_EXPERIMENT = (
    "En cada ensayo, al igual que en la práctica observarás el estímulo durante {:.0f} segundos.\n"
    "Mantén la mirada en el punto central mientras lo observas.\n"
    "Después dibuja, en los ejes, cómo fue cambiando la visibilidad a lo largo del ensayo.\n"
    "No termines el trazado hasta haber llegado al borde derecho de la gráfica.\n\n"
    "Pulsa ESPACIO para continuar.")

# The drawing screen
TET_DRAW = (
    "Haz clic y arrastra para dibujar la visibilidad a lo largo del tiempo.\n"
    "El trazado debe empezar en el borde izquierdo y terminar en el borde derecho.\n"
    "Arriba significa más visible y abajo menos visible.\n"
    "Si percibes el estímulo con máxima intensidad, intenta con tu línea llegar hasta arriba de la gráfica. Si dejas "
    "de ver el estímulo, llega hasta abajo con la línea.\n"
    "Pulsa RETROCESO para reiniciar. Pulsa ENTER para confirmar.")
TET_INCOMPLETE = ("El trazado no llega hasta el final del ensayo.\n"
                  "Continúa la línea hasta el borde derecho de la gráfica antes de terminar.")
TET_TIME_AXIS = "Tiempo"
TET_TOP = "Veo el estímulo\ncon total claridad"
TET_BOTTOM = "No veo\nel estímulo"

# =============================================================================
# Start form
# =============================================================================

DIALOG_TITLE = "Datos de participante"
DIALOG_LABELS = {"participant": "ID participante (ej. 1001)", "age": "Edad", "gender": "Género"}
GENDERS = ["Mujer", "Hombre", "No binario", "Prefiero no decir", "Otro"]
