# Aula térmica · Python + Streamlit

Prototipo interactivo para simular la temperatura media de un aula ocupada y
comparar qué ocurre con y sin aire acondicionado. La interfaz está en español.

## Inicio rápido en Windows

1. Instalá **Python 3.12** y descomprimí el proyecto.
2. Abrí la carpeta `aula_termica`.
3. Hacé doble clic en `iniciar_windows.bat`.

El iniciador crea un entorno virtual, instala las dependencias y abre Streamlit.
La primera instalación necesita conexión a Internet. Para detenerlo, usá Ctrl+C
en la consola. También podés ejecutarlo manualmente desde esa carpeta:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

Si no se abre automáticamente, visitá `http://localhost:8501`.

## macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

O ejecutá `bash iniciar_macos_linux.sh` desde la carpeta del proyecto.

## Subir a Streamlit Community Cloud

1. Creá un repositorio de GitHub y subí **el contenido descomprimido**, incluyendo
   `app.py`, `modelo.py`, `graficos.py`, `datos.py`, `requirements.txt` y `.streamlit/config.toml`.
   El ZIP es para transportar el proyecto; no es el archivo que ejecuta Streamlit.
2. Entrá en [Streamlit Community Cloud](https://share.streamlit.io/).
3. Elegí **Create app**, seleccioná el repositorio, la rama y el archivo `app.py`.
4. En **Advanced settings**, elegí **Python 3.12**.
5. Pulsá **Deploy**.

Si subís la carpeta entera en lugar de su contenido, el archivo de entrada será
`aula_termica/app.py`. Es más simple colocar los archivos en la raíz del repositorio.
No hace falta configurar claves, servicios externos ni una base de datos.

La app queda preparada para ese despliegue. Este proyecto no crea ni publica un
repositorio automáticamente.

## Qué se puede cambiar

- Temperatura inicial del aula y temperatura exterior constante o con rampa lineal.
- Largo, ancho, altura, superficie de ventanas y fracción de paredes exteriores.
- Transmitancias U y techo expuesto al exterior.
- Alumnos, docentes, calor por persona y horario de ocupación.
- Sol, vidrio, sombra, iluminación y equipos.
- Renovación de aire y horario de apertura de ventanas.
- Número de aires y capacidad por equipo en frigorías/h, BTU/h o kW frigoríficos.
- Consigna, banda de termostato, horario y modo de potencia fija.
- Fracción sensible, COP, inercia térmica, paso de cálculo y tarifa de electricidad.

Los cambios recalculan la simulación. Para comparar distintas aulas, guardá su
escenario JSON y luego cargalo en la sección correspondiente.

## Qué muestra

**Simulación:** curvas de temperatura con la configuración elegida, sin aire y
exterior; un control para recorrer el tiempo; plano con alumnos y estado del aire;
balance de entradas y salidas de calor; energía y costo del aire.

**Comparar equipos:** escenarios de distintas capacidades bajo las mismas
condiciones. El modo de control y el horario también se conservan.

**Modelo y datos:** ecuaciones, parámetros derivados, comparación con mediciones,
descarga CSV y guardado/carga de escenario JSON.

El plano está teñido por **la temperatura media del aula**. Los alumnos y la flecha
del aire son esquemáticos. No representan diferencias de temperatura por posición
ni una solución de dinámica de fluidos.

## Modelo físico

Es un modelo de una zona, con una temperatura interior uniforme T y una capacidad
térmica efectiva C. El balance de energía sensible es:

```text
C · dT/dt = (UA + Hvent) · (Text - T)
            + Qpersonas + Qluces + Qequipos + Qsolar - Qaire
```

| Variable | Unidad | Definición |
|---|---|---|
| T, Text | °C | Temperatura media interior y temperatura exterior. |
| C | J/K | Capacidad térmica de aire más masa equivalente. |
| UA | W/K | Transmisión por paredes opacas, ventanas y techo exterior. |
| Hvent | W/K | Intercambio por ventilación e infiltraciones. |
| Qpersonas, Qluces, Qequipos, Qsolar | W | Ganancias de calor sensible. |
| Qaire | W | Refrigeración sensible del equipo. |

```text
Área de piso = largo · ancho
Volumen = área de piso · altura
Área de paredes exteriores = 2 · (largo + ancho) · altura · fracción exterior
UA = Upared · (área exterior - área ventanas)
     + Uventana · área ventanas + Utecho · área piso [si techo exterior]
Hvent = densidad del aire · calor específico · volumen · ACH / 3600
C = densidad del aire · calor específico · volumen
    + área piso · masa térmica equivalente [convertida de kJ a J]
Qsolar = área ventanas · irradiancia · factor solar vidrio · (1 - sombra)
Qpersonas = personas presentes · calor sensible por persona
Qaire = capacidad total en kW · 1000 · fracción sensible · u
Potencia eléctrica [kW] = capacidad total en kW / COP · u
Energía [kWh] = integral de potencia eléctrica sobre el tiempo en horas
```

`u` es 1 si el aire está enfriando y 0 si no. La densidad del aire es 1,2 kg/m³ y
su calor específico es 1006 J/(kg·K), constantes del modelo.

El aire exterior **calienta si Text > T y enfría si Text < T**. Las U expresan
transmisión, por lo que un mayor aislamiento se representa con una U menor.
El modelo no incluye paredes interiores ni piso intercambiando con otros ambientes.

La iluminación y otros equipos se activan durante el horario de clase. El sol se
mantiene constante durante toda la simulación. La ocupación es una ventana de
tiempo única. Los extremos iniciales son inclusivos y los finales exclusivos:
al terminar la clase, la última fila puede mostrar cero personas aunque el calor
de la clase siga presente en la temperatura.

### Aire acondicionado y unidades

- **1 BTU/h = 0,00029307107 kW** frigoríficos.
- **1 frigoría/h ≈ 0,001163 kW** frigoríficos.
- La capacidad frigorífica y la potencia eléctrica son magnitudes distintas.
  A igual capacidad, cambiar el COP modifica el consumo eléctrico, no el calor
  que extrae el modelo.
- La fracción sensible convierte la capacidad nominal total en la parte que
  modifica la temperatura. Se considera constante. La carga latente no se resuelve.

**Termostato:** enciende al alcanzar consigna + media banda y apaga al alcanzar
consigna - media banda. Con consigna 24 °C y banda 1 °C, enciende a 24,5 °C y apaga
a 23,5 °C. Arranca apagado si la temperatura inicial está dentro de la banda.

**Potencia fija:** enfría continuamente durante el intervalo habilitado. En ese
modo puede enfriar por debajo de la consigna porque no actúa el termostato.

**Tiempo hasta la banda:** tiempo desde habilitar el aire hasta el primer instante
con T ≤ consigna + media banda. Si ya cumple al habilitarlo, vale cero. No garantiza
permanencia en la banda ni es una evaluación de confort.

### Método numérico

`modelo.py` utiliza la solución exponencial del balance para cada intervalo de
coeficientes constantes. La temperatura exterior se aproxima en el punto medio.
Si no hay intercambio exterior, aplica directamente el balance lineal de energía.
Agrega los horarios de entrada, salida, apertura y encendido a la grilla.

El termostato se evalúa cada paso (10 s por defecto). Puede sobrepasar ligeramente
los límites de la banda, sobre todo con poca inercia o equipos muy potentes.
Reducí el paso para mejorar la resolución del control.

## Aula de ejemplo

Los parámetros iniciales son ilustrativos, no mediciones de un aula real:

| Parámetro | Valor |
|---|---:|
| Dimensiones | 8 × 6 × 3 m |
| Ocupación | 25 alumnos + 1 docente |
| Temperatura inicial / exterior | 30 / 34 °C |
| Equipo | 6000 frigorías/h (6,978 kW totales) |
| Fracción sensible / COP | 0,85 / 3,2 |
| Inicio del aire | minuto 15 |
| Consigna / banda | 24 / 1 °C |
| Duración | 240 min |
| Calor sensible por persona | 75 W |
| Masa equivalente | 40 kJ/(m²·K) |
| Tarifa ilustrativa editable | 300 ARS/kWh |

Para una primera exploración, alterná los ejemplos de 45 alumnos, equipo de
3000 frigorías/h y ventanas abiertas. Observá cuánto calor agregan y si el equipo
puede compensarlo.

## Mediciones y camino al gemelo digital

Un gemelo digital de un aula real requiere sincronizar datos y validar el modelo.
Esta versión deja preparada la comparación con mediciones, pero usa condiciones
de entrada configuradas por el usuario.

Formato de mediciones CSV:

```csv
minuto,temperatura_c
0,30.0
10,30.7
20,30.5
```

Los valores del ejemplo anterior solo ilustran el formato. La columna `minuto`
se cuenta desde el inicio del ensayo. Debe estar dentro de la duración configurada.
La app interpola su predicción en esos tiempos y muestra MAE y RMSE. Cargar el CSV
no calibra automáticamente el modelo.

En `ejemplos/mediciones_sinteticas.csv` hay temperaturas generadas por este mismo
modelo para probar el cargador. **No son mediciones ni evidencia de validación.**
También se incluye `ejemplos/escenario_base.json`.

Para calibrar y validar con un aula:

1. Medí temperatura interior y exterior, ocupación, ventanas, estado del aire y,
   si es posible, potencia eléctrica, con una referencia de tiempo común.
2. Relevá geometría y capacidad de placa del equipo.
3. Ajustá UA, ACH e inercia con registros que incluyan períodos con y sin aire.
   Esos parámetros pueden compensarse entre sí; una sola curva no suele bastar.
4. Verificá el error en una jornada distinta de la usada para el ajuste.
5. Conectá el modelo a CSV periódicos o sensores/API conservando registro histórico.

La versión actual no calcula humedad, CO₂, temperatura de paredes por separado,
estratificación, corrientes locales ni confort térmico completo. No incluye curvas
de capacidad/COP según condiciones, modulación inverter, ventilador independiente
ni consumo en espera. Por eso la capacidad y el gasto son estimaciones de este
modelo, no resultados certificados de selección de equipos.

## Estructura y modificación del código

```text
aula_termica/
    app.py                      interfaz y exportaciones
    modelo.py                   parámetros, balance y simulación
    graficos.py                 curvas, plano y balance
    datos.py                    carga y validación de JSON / CSV
    requirements.txt            dependencias probadas
    README.md                   estas instrucciones
    iniciar_windows.bat         inicio con doble clic
    iniciar_macos_linux.sh       inicio en macOS/Linux
    .streamlit/config.toml       tema visual
    ejemplos/                   escenario y datos sintéticos
    tests/                      pruebas físicas y de interfaz
```

Desde un script dentro del proyecto podés usar el motor sin Streamlit:

```python
from dataclasses import replace
from modelo import Parametros, comparar

p = replace(Parametros(), alumnos=35, capacidad_total_kw=8.0)
con_aire, sin_aire = comparar(p)
con_aire.to_csv("resultado.csv", index=False)
```

Para sumar un nuevo aporte de calor, modificá `cargas` en `modelo.py`; para cambiar
el controlador, modificá `_control`. El motor se puede sustituir por un modelo de
dos temperaturas o uno espacial sin reemplazar toda la interfaz.

## Verificación

Desde la carpeta del proyecto:

```bash
python -m unittest discover -s tests -v
```

Las pruebas verifican conservación de energía, soluciones analíticas, efecto de
ocupación, ventilación e inercia, integración de eventos, consumo/COP, ciclos del
termostato y los controles de Streamlit. Se usan `unittest` y `AppTest`; no hace
falta instalar pytest. No sustituyen la calibración con datos reales.

Probado con Python 3.12 y las versiones fijadas en `requirements.txt`.

## Referencias

- [Balance de calor en zonas, Engineering Reference de EnergyPlus](https://bigladdersoftware.com/epx/docs/24-2/engineering-reference/air-heat-balance-manager-processes.html).
  Referencia conceptual; este proyecto usa un modelo de capacidad concentrada
  mucho más simple, no implementa EnergyPlus.
- [Documentación de Streamlit](https://docs.streamlit.io/).
- [Despliegue en Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).
- [AppTest oficial](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest).
- [Integración de Plotly en Streamlit](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart).

Las U, ganancias por persona, radiación, ACH, inercia, COP y tarifa iniciales son
hipótesis de demostración modificables; las referencias no avalan esos valores
para un edificio concreto.
