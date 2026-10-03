"""Ejecutar con: python -m streamlit run app.py"""

from dataclasses import asdict, replace
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from graficos import balance, curva_temperatura, plano_aula, estilo
from datos import leer_escenario, leer_mediciones
from modelo import (BTUH_TO_KW, FRIGORIAS_H_TO_KW, Parametros,
                    cargas, comparar, resumir, simular)

st.set_page_config(page_title="Aula térmica", page_icon="🌡️", layout="wide")

FACTORES = {"frigorías/h": FRIGORIAS_H_TO_KW, "BTU/h": BTUH_TO_KW, "kW frigoríficos": 1.0}
BASE = asdict(Parametros())


def aplicar(p):
    for nombre, valor in asdict(p).items():
        st.session_state[nombre] = float(valor) if isinstance(BASE[nombre], float) else valor
    st.session_state["duracion_min"] = int(p.duracion_min)
    st.session_state["intervalo_clase"] = (int(p.inicio_clase_min), int(p.fin_clase_min))
    st.session_state["intervalo_aire"] = (int(p.inicio_aire_min), int(p.fin_aire_min))
    st.session_state["intervalo_ventanas"] = (int(p.inicio_ventanas_min), int(p.fin_ventanas_min))
    st.session_state["unidad_aire"] = "kW frigoríficos"
    st.session_state["unidad_anterior"] = "kW frigoríficos"
    cantidad = max(1, int(np.ceil(p.capacidad_total_kw / 25)))
    st.session_state["capacidad_equipo"] = float(p.capacidad_total_kw / cantidad)
    st.session_state["cantidad_equipos"] = cantidad
    st.session_state["exterior_variable"] = p.exterior_inicial_c != p.exterior_final_c
    st.session_state["inspeccionar_min"] = min(60, int(p.duracion_min))


def cambiar_unidad():
    anterior = st.session_state["unidad_anterior"]
    nueva = st.session_state["unidad_aire"]
    kw = st.session_state["capacidad_equipo"] * FACTORES[anterior]
    st.session_state["capacidad_equipo"] = min(25.0, max(0.0, kw)) / FACTORES[nueva]
    st.session_state["unidad_anterior"] = nueva


def cambiar_duracion():
    fin = int(st.session_state["duracion_min"])
    for clave in ["intervalo_clase", "intervalo_aire", "intervalo_ventanas"]:
        a, b = st.session_state[clave]
        st.session_state[clave] = (min(a, fin), min(b, fin))
    st.session_state["inspeccionar_min"] = min(st.session_state["inspeccionar_min"], fin)


def elegir_ejemplo():
    nombre = st.session_state["ejemplo"]
    p = Parametros()
    if nombre == "Clase de 45 alumnos":
        p = replace(p, alumnos=45)
    elif nombre == "Aire de 3000 frigorías/h":
        p = replace(p, capacidad_total_kw=3000 * FRIGORIAS_H_TO_KW)
    elif nombre == "Ventanas abiertas":
        p = replace(p, abrir_ventanas=True)
    aplicar(p)


def restablecer():
    aplicar(Parametros())
    st.session_state["ejemplo"] = "Aula de ejemplo"


def cargar_escenario():
    try:
        archivo = st.session_state.get("archivo_escenario")
        if archivo is None:
            raise ValueError("Seleccioná un archivo JSON primero.")
        p = leer_escenario(archivo.getvalue())
        aplicar(p)
        st.session_state["mensaje_config"] = "Escenario cargado."
    except (ValueError, TypeError, KeyError, UnicodeDecodeError) as exc:
        st.session_state["mensaje_config"] = f"No se pudo cargar: {exc}"


if "inicializado" not in st.session_state:
    aplicar(Parametros())
    st.session_state["unidad_aire"] = "frigorías/h"
    st.session_state["unidad_anterior"] = "frigorías/h"
    st.session_state["capacidad_equipo"] = 6000.0
    st.session_state["inicializado"] = True


with st.sidebar:
    st.title("Configuración")
    st.selectbox("Probar un ejemplo", ["Aula de ejemplo", "Clase de 45 alumnos",
                                      "Aire de 3000 frigorías/h", "Ventanas abiertas"],
                 key="ejemplo", on_change=elegir_ejemplo)
    st.button("Restablecer ejemplo inicial", on_click=restablecer)
    with st.expander("Temperaturas y duración", expanded=True):
        st.slider("Duración de la simulación (min)", 30, 480, key="duracion_min",
                  step=1, on_change=cambiar_duracion)
        st.slider("Temperatura inicial del aula (°C)", 5.0, 50.0, step=.5,
                  key="temperatura_inicial_c")
        st.slider("Temperatura exterior inicial (°C)", -10.0, 50.0, step=.5,
                  key="exterior_inicial_c")
        st.checkbox("Cambiar la temperatura exterior durante la simulación", key="exterior_variable")
        if st.session_state["exterior_variable"]:
            st.slider("Temperatura exterior final (°C)", -10.0, 50.0, step=.5, key="exterior_final_c")
    duracion = int(st.session_state["duracion_min"])
    with st.expander("Alumnos y horario de clase", expanded=True):
        st.number_input("Cantidad de alumnos", 0, 150, key="alumnos", step=1)
        st.number_input("Cantidad de docentes", 0, 10, key="docentes", step=1)
        st.slider("Horario de ocupación (min)", 0, duracion, key="intervalo_clase")
        st.number_input("Calor sensible por persona (W)", 0.0, 200.0, key="calor_persona_w", step=5.0,
                        help="Supuesto ajustable. No incluye el calor latente de la transpiración.")
    with st.expander("Aire acondicionado", expanded=True):
        st.checkbox("Habilitar aire acondicionado", key="aire_habilitado")
        st.selectbox("Unidad de capacidad", list(FACTORES), key="unidad_aire", on_change=cambiar_unidad)
        unidad = st.session_state["unidad_aire"]
        st.number_input(f"Capacidad de cada equipo ({unidad})", min_value=0.0, max_value=25.0/FACTORES[unidad],
                        key="capacidad_equipo", step=100.0 if unidad != "kW frigoríficos" else .1,
                        format="%.2f")
        st.number_input("Cantidad de equipos", 1, 5, key="cantidad_equipos", step=1)
        capacidad_kw = (st.session_state["capacidad_equipo"] * FACTORES[unidad]
                        * st.session_state["cantidad_equipos"])
        st.caption(f"Capacidad térmica total: {capacidad_kw:.2f} kW · "
                   f"{capacidad_kw/BTUH_TO_KW:,.0f} BTU/h · "
                   f"{capacidad_kw/FRIGORIAS_H_TO_KW:,.0f} frigorías/h")
        st.slider("Temperatura deseada (°C)", 16.0, 30.0, step=.5, key="consigna_c")
        st.slider("Horario de habilitación del aire (min)", 0, duracion, key="intervalo_aire")
        st.selectbox("Control", ["Termostato", "Potencia fija"], key="modo_control")
        st.slider("Banda total del termostato (°C)", .2, 3.0, step=.1, key="banda_c",
                  help="Con 24 °C y banda 1 °C, enciende a 24,5 y apaga a 23,5.")
        st.slider("Fracción de capacidad que baja la temperatura", 0.0, 1.0, step=.01,
                  key="fraccion_sensible", help="La capacidad restante corresponde a carga latente; no se simula humedad.")
        st.number_input("COP del equipo", 1.0, 8.0, step=.1, key="cop",
                        help="Capacidad frigorífica total / potencia eléctrica. A igual capacidad, afecta consumo, no refrigeración.")
    with st.expander("Dimensiones y construcción"):
        st.number_input("Largo (m)", 3.0, 20.0, step=.5, key="largo_m")
        st.number_input("Ancho (m)", 3.0, 20.0, step=.5, key="ancho_m")
        st.number_input("Altura (m)", 2.0, 6.0, step=.1, key="alto_m")
        st.slider("Fracción de paredes que da al exterior", 0.0, 1.0, step=.05, key="fraccion_pared_exterior")
        st.number_input("Superficie de ventanas exteriores (m²)", 0.0, 100.0, step=.5, key="ventanas_m2")
        st.checkbox("Techo expuesto al exterior", key="techo_exterior")
        st.number_input("U de paredes (W/m²·K)", 0.0, 8.0, step=.1, key="u_pared_w_m2k")
        st.number_input("U de ventanas (W/m²·K)", 0.0, 10.0, step=.1, key="u_ventana_w_m2k")
        st.number_input("U del techo (W/m²·K)", 0.0, 8.0, step=.1, key="u_techo_w_m2k")
    with st.expander("Sol, luces y equipos"):
        st.slider("Radiación sobre las ventanas (W/m²)", 0.0, 1200.0, step=25.0, key="irradiancia_w_m2")
        st.slider("Factor solar del vidrio", 0.0, 1.0, step=.05, key="factor_solar_vidrio")
        st.slider("Fracción de sombra / cortina", 0.0, 1.0, step=.05, key="fraccion_sombra")
        st.number_input("Iluminación durante la clase (W/m²)", 0.0, 30.0, step=1.0, key="luces_w_m2")
        st.number_input("Otros equipos durante la clase (W)", 0.0, 10000.0, step=50.0, key="equipos_w")
    with st.expander("Ventilación y ventanas"):
        st.slider("Renovaciones de aire con ventanas cerradas (1/h)", 0.0, 20.0, step=.1,
                  key="renovaciones_base_h")
        st.checkbox("Abrir ventanas durante un intervalo", key="abrir_ventanas")
        st.slider("Renovaciones adicionales por ventanas abiertas (1/h)", 0.0, 30.0, step=.5,
                  key="renovaciones_extra_h")
        st.slider("Horario de ventanas abiertas (min)", 0, duracion, key="intervalo_ventanas")
        st.caption("El aire exterior puede calentar o enfriar según la diferencia de temperatura.")
    with st.expander("Inercia, cálculo y costo"):
        st.number_input("Masa térmica equivalente (kJ/m²·K)", 0.0, 400.0, step=5.0, key="masa_kj_m2k",
                        help="Parámetro efectivo de muebles y construcción; se debe calibrar con mediciones.")
        st.number_input("Paso de cálculo (s)", 1.0, 60.0, step=1.0, key="paso_s")
        st.number_input("Precio ilustrativo de la electricidad (ARS/kWh)", 0.0, 100000.0,
                        step=10.0, key="tarifa_kwh", help="Ingresá tu tarifa. No es una cotización actual.")
    with st.expander("Cargar un escenario guardado"):
        st.file_uploader("Escenario JSON", type="json", key="archivo_escenario")
        st.button("Cargar escenario", on_click=cargar_escenario)
        if "mensaje_config" in st.session_state:
            st.caption(st.session_state["mensaje_config"])

datos = {k: st.session_state[k] for k in BASE}
datos.update(
    capacidad_total_kw=capacidad_kw,
    exterior_final_c=(st.session_state["exterior_final_c"] if st.session_state["exterior_variable"]
                      else st.session_state["exterior_inicial_c"]),
    inicio_clase_min=st.session_state["intervalo_clase"][0],
    fin_clase_min=st.session_state["intervalo_clase"][1],
    inicio_aire_min=st.session_state["intervalo_aire"][0],
    fin_aire_min=st.session_state["intervalo_aire"][1],
    inicio_ventanas_min=st.session_state["intervalo_ventanas"][0],
    fin_ventanas_min=st.session_state["intervalo_ventanas"][1],
)
p = Parametros(**datos)

st.title("Aula térmica")
st.write("Explorá cómo cambian la temperatura y el consumo al agregar alumnos, abrir ventanas o encender el aire.")
st.caption("Prototipo de simulación · Temperatura media de una zona · Parámetros de ejemplo, ajustables")
try:
    p.validar()
except ValueError as exc:
    st.error(str(exc))
    st.stop()


@st.cache_data(show_spinner=False)
def resolver(parametros):
    return comparar(parametros)


con, sin = resolver(p)
resumen = resumir(con, p)
tiempo_banda = resumen["tiempo_hasta_banda_min"]
columnas = st.columns(4)
columnas[0].metric("Temperatura al final", f"{resumen['temperatura_final_c']:.1f} °C")
columnas[1].metric("Reducción frente a no usar aire", f"{sin.iloc[-1].temperatura_c - con.iloc[-1].temperatura_c:.1f} °C")
columnas[2].metric("Tiempo hasta la banda", f"{tiempo_banda:.0f} min" if tiempo_banda is not None else "No alcanzado",
                   help="Tiempo desde habilitar el aire hasta estar por debajo de consigna + media banda. No indica permanencia ni confort.")
columnas[3].metric("Electricidad estimada del aire", f"{resumen['energia_kwh']:.2f} kWh",
                   help="Incluye compresor idealizado. Excluye consumo en espera y ventiladores independientes.")
if not p.aire_habilitado:
    st.info("Aire deshabilitado: las dos curvas coinciden.")
elif p.modo_control == "Potencia fija":
    st.info("En potencia fija el equipo enfría todo el intervalo habilitado, aunque pase por debajo de la consigna.")

en_clase = con[(con.minuto >= p.inicio_clase_min) & (con.minuto < p.fin_clase_min)]
if not en_clase.empty and p.aire_habilitado:
    demanda = max(cargas(p, float(t), p.consigna_c)["ganancias_w"] for t in en_clase.minuto[::6])
    if demanda > p.refrigeracion_sensible_w:
        st.warning(f"Durante parte de la clase, la carga estimada a {p.consigna_c:.1f} °C llega a "
                   f"{demanda/1000:.2f} kW, por encima de los {p.refrigeracion_sensible_w/1000:.2f} kW "
                   "de refrigeración sensible disponible. La consigna puede ser inalcanzable en esas condiciones.")

simulacion, escenarios, modelo_datos = st.tabs(["Simulación", "Comparar equipos", "Modelo y datos"])
with simulacion:
    st.slider("Recorrer el tiempo de la simulación (min)", 0, int(p.duracion_min),
              key="inspeccionar_min", step=1)
    minuto = st.session_state["inspeccionar_min"]
    indice = int(np.argmin(np.abs(con.minuto.to_numpy() - minuto)))
    fila = con.iloc[indice]
    st.plotly_chart(curva_temperatura(con, sin, p, minuto), width="stretch", key="curva_principal")
    izquierda, derecha = st.columns([1, 1.2])
    with izquierda:
        st.plotly_chart(plano_aula(p, fila), width="stretch", key="plano")
        st.caption("Plano esquemático. El color representa la temperatura media: no calcula corrientes ni zonas frías/calientes.")
    with derecha:
        st.subheader(f"Balance de calor al minuto {minuto}")
        st.plotly_chart(balance(fila), width="stretch", key="balance")
        sentido = "sube" if fila.balance_w > 1 else "baja" if fila.balance_w < -1 else "se mantiene"
        st.write(f"El balance neto es **{fila.balance_w/1000:+.2f} kW**: la temperatura {sentido} en este instante.")
        st.caption(f"Aire: {'enfriando' if fila.aire_encendido else 'sin refrigerar'} · "
                   f"Exterior: {fila.exterior_c:.1f} °C · Renovación: {fila.ach_h:.1f}/h")
    st.caption(f"Aula: {p.area_m2:.1f} m² / {p.volumen_m3:.1f} m³ · "
               f"Costo del aire en toda la simulación: ARS {resumen['costo_ars']:,.0f}, "
               f"con la tarifa ingresada de {p.tarifa_kwh:,.0f} ARS/kWh.")

with escenarios:
    st.subheader("Mismo aula, distinta capacidad")
    st.write("La geometría, los alumnos, el horario y el clima se mantienen iguales. Se cambia la capacidad total de refrigeración.")
    fig = go.Figure()
    filas = []
    capacidades = sorted(set([0.0, 3000*FRIGORIAS_H_TO_KW, 4500*FRIGORIAS_H_TO_KW,
                              6000*FRIGORIAS_H_TO_KW, 9000*FRIGORIAS_H_TO_KW, p.capacidad_total_kw]))
    for capacidad in capacidades:
        alternativa = replace(p, capacidad_total_kw=capacidad, aire_habilitado=capacidad > 0)
        df = simular(alternativa)
        r = resumir(df, alternativa)
        nombre = "Sin aire" if capacidad == 0 else f"{capacidad/FRIGORIAS_H_TO_KW:,.0f} frigorías/h"
        fig.add_trace(go.Scatter(x=df.minuto, y=df.temperatura_c, name=nombre,
                                line=dict(width=3 if capacidad == p.capacidad_total_kw else 1.8)))
        filas.append({"Equipo / capacidad total": nombre, "Temperatura final (°C)": r["temperatura_final_c"],
                      "Máxima (°C)": r["temperatura_maxima_c"], "Electricidad (kWh)": r["energia_kwh"],
                      "Hasta la banda (min)": r["tiempo_hasta_banda_min"]})
    fig.update_layout(xaxis_title="Tiempo (min)", yaxis_title="Temperatura media (°C)", hovermode="x unified")
    st.plotly_chart(estilo(fig), width="stretch", key="alternativas")
    st.dataframe(pd.DataFrame(filas).round(2), hide_index=True, width="stretch")
    st.caption("Un guion en el tiempo hasta la banda significa que no se alcanzó dentro del intervalo habilitado, o que no hay aire.")

with modelo_datos:
    st.subheader("Balance térmico")
    st.latex(r"C_{ef}\frac{dT}{dt}=(UA+H_{vent})(T_{ext}-T)+Q_{personas}+Q_{luces}+Q_{equipos}+Q_{solar}-Q_{aire}")
    st.write("La temperatura cambia por el balance entre el calor que entra y el que extrae el aire. "
             "La capacidad térmica efectiva determina la velocidad del cambio.")
    st.latex(r"H_{vent}=\rho c_p V\frac{ACH}{3600},\quad C_{ef}=\rho c_p V+A_{piso}c_{masa}")
    st.latex(r"Q_{solar}=A_{vidrio}I\,g(1-s),\quad Q_{aire}=1000\,Q_{nominal,kW}\,f_{sensible}\,u")
    st.latex(r"P_{electrica,kW}=\frac{Q_{nominal,kW}}{COP}u,\quad E_{kWh}=\int P_{electrica,kW}\,dt_h")
    st.write(f"**Valores calculados:** UA = {p.ua_w_k:.1f} W/K · "
             f"C efectiva = {p.capacidad_j_k/1e6:.2f} MJ/K · "
             f"Refrigeración sensible máxima = {p.refrigeracion_sensible_w/1000:.2f} kW.")
    st.caption("u vale 0 o 1 según el termostato. La temperatura exterior puede variar linealmente. "
               "La radiación solar y la capacidad del equipo se consideran constantes.")
    with st.expander("Supuestos y cómo convertirlo en un gemelo digital", expanded=True):
        st.write("Esta versión es un prototipo físico de una zona. Para representar un aula real, "
                 "hay que medir temperatura interior/exterior, ocupación y estado/consumo del aire; "
                 "calibrar UA, renovaciones e inercia; y validar en una jornada distinta.")
        st.write("El modelo representa aire bien mezclado y masa equivalente a una sola temperatura. "
                 "No calcula humedad, CO₂, confort completo, paredes a otra temperatura ni flujo espacial. "
                 "La masa térmica, las renovaciones y los 75 W/persona iniciales son supuestos modificables. "
                 "El control es idealizado, sin mínimos de encendido ni curva de un equipo inverter.")
    st.subheader("Comparar con mediciones")
    st.caption("CSV con columnas minuto,temperatura_c. Los tiempos se cuentan desde el inicio de la simulación. "
               "El ejemplo incluido es sintético y está identificado como tal.")
    mediciones_archivo = st.file_uploader("Temperatura medida (CSV)", type="csv", key="archivo_mediciones")
    if mediciones_archivo is not None:
        try:
            mediciones = leer_mediciones(mediciones_archivo.getvalue(), p.duracion_min)
            prediccion = np.interp(mediciones.minuto, con.minuto, con.temperatura_c)
            error = mediciones.temperatura_c.to_numpy() - prediccion
            a, b = st.columns(2)
            a.metric("Error absoluto medio", f"{np.mean(np.abs(error)):.2f} °C")
            b.metric("RMSE", f"{np.sqrt(np.mean(error**2)):.2f} °C")
            st.plotly_chart(curva_temperatura(con, sin, p, mediciones=mediciones),
                            width="stretch", key="curva_mediciones")
            st.caption("La carga del CSV permite comparar; no modifica automáticamente los parámetros.")
        except (ValueError, TypeError, pd.errors.ParserError, UnicodeDecodeError) as exc:
            st.error(f"No se pudo leer el CSV: {exc}")
    st.subheader("Descargar resultados y configuración")
    exportacion = con.copy()
    exportacion["temperatura_sin_aire_c"] = sin.temperatura_c.to_numpy()
    st.download_button("Descargar simulación CSV", exportacion.to_csv(index=False).encode("utf-8-sig"),
                       "simulacion_aula.csv", "text/csv", key="csv_resultados")
    st.download_button("Guardar escenario JSON",
                       json.dumps({"version": 1, "parametros": asdict(p)}, ensure_ascii=False, indent=2),
                       "escenario_aula.json", "application/json", key="json_escenario")
    st.dataframe(exportacion.iloc[::max(1, int(60/p.paso_s))].round(3), hide_index=True, width="stretch")
    st.caption("La vista de tabla se reduce aproximadamente a un minuto; el CSV conserva todos los pasos.")
    st.markdown("Documentación: [Streamlit](https://docs.streamlit.io/) · "
                "[Balance térmico de zonas, EnergyPlus](https://bigladdersoftware.com/epx/docs/24-2/engineering-reference/air-heat-balance-manager-processes.html)")
