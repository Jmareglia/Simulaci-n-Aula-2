"""Lectura validada de escenarios y mediciones, sin dependencia de Streamlit."""

import io
import json

import numpy as np
import pandas as pd

from modelo import Parametros


def leer_escenario(contenido: bytes) -> Parametros:
    payload = json.loads(contenido)
    if not isinstance(payload, dict) or type(payload.get("version")) is not int or payload["version"] != 1:
        raise ValueError("El JSON debe tener version: 1 y el objeto parametros.")
    if not isinstance(payload.get("parametros"), dict):
        raise ValueError("parametros debe ser un objeto JSON.")
    p = Parametros(**payload["parametros"])
    p.validar()
    limites = {
        "largo_m": (3, 20), "ancho_m": (3, 20), "alto_m": (2, 6),
        "ventanas_m2": (0, 100), "alumnos": (0, 150), "docentes": (0, 10),
        "calor_persona_w": (0, 200), "luces_w_m2": (0, 30), "equipos_w": (0, 10000),
        "irradiancia_w_m2": (0, 1200), "renovaciones_base_h": (0, 20),
        "renovaciones_extra_h": (0, 30), "temperatura_inicial_c": (5, 50),
        "exterior_inicial_c": (-10, 50), "exterior_final_c": (-10, 50),
        "capacidad_total_kw": (0, 125), "cop": (1, 8), "consigna_c": (16, 30),
        "banda_c": (.2, 3), "masa_kj_m2k": (0, 400), "duracion_min": (30, 480),
        "paso_s": (1, 60), "tarifa_kwh": (0, 100000),
        "u_pared_w_m2k": (0, 8), "u_ventana_w_m2k": (0, 10), "u_techo_w_m2k": (0, 8),
    }
    for nombre, (menor, mayor) in limites.items():
        if not menor <= getattr(p, nombre) <= mayor:
            raise ValueError(f"{nombre} está fuera del rango de esta app: {menor} a {mayor}.")
    for nombre in ["duracion_min", "inicio_clase_min", "fin_clase_min", "inicio_aire_min",
                   "fin_aire_min", "inicio_ventanas_min", "fin_ventanas_min"]:
        if float(getattr(p, nombre)) != int(getattr(p, nombre)):
            raise ValueError("La interfaz carga horarios en minutos enteros.")
    return p


def leer_mediciones(contenido: bytes, duracion_min: float) -> pd.DataFrame:
    mediciones = pd.read_csv(io.BytesIO(contenido))
    if not {"minuto", "temperatura_c"}.issubset(mediciones.columns):
        raise ValueError("Faltan las columnas minuto y temperatura_c.")
    mediciones = mediciones[["minuto", "temperatura_c"]].apply(pd.to_numeric, errors="raise")
    if len(mediciones) < 2 or not np.isfinite(mediciones.to_numpy()).all():
        raise ValueError("Se necesitan al menos dos mediciones numéricas finitas.")
    if (mediciones.minuto < 0).any() or (mediciones.minuto > duracion_min).any():
        raise ValueError("Los minutos medidos deben estar dentro de la duración configurada.")
    return mediciones.sort_values("minuto").reset_index(drop=True)
