"""Balance térmico sensible de un aula de una zona, independiente de Streamlit.

El estado representa una temperatura interior uniforme. La capacidad efectiva
incluye aire y una masa térmica equivalente en equilibrio con esa temperatura.
"""

from dataclasses import asdict, dataclass, replace
import math
from numbers import Integral, Real

import numpy as np
import pandas as pd

RHO_AIR_KG_M3 = 1.2
CP_AIR_J_KG_K = 1006.0
BTUH_TO_KW = 0.00029307107
FRIGORIAS_H_TO_KW = 0.001163


@dataclass(frozen=True)
class Parametros:
    largo_m: float = 8.0
    ancho_m: float = 6.0
    alto_m: float = 3.0
    fraccion_pared_exterior: float = 0.5
    ventanas_m2: float = 6.0
    u_pared_w_m2k: float = 1.8
    u_ventana_w_m2k: float = 5.8
    u_techo_w_m2k: float = 0.7
    techo_exterior: bool = True
    masa_kj_m2k: float = 40.0
    alumnos: int = 25
    docentes: int = 1
    calor_persona_w: float = 75.0
    inicio_clase_min: float = 0.0
    fin_clase_min: float = 240.0
    luces_w_m2: float = 8.0
    equipos_w: float = 200.0
    irradiancia_w_m2: float = 350.0
    factor_solar_vidrio: float = 0.65
    fraccion_sombra: float = 0.4
    renovaciones_base_h: float = 0.7
    abrir_ventanas: bool = False
    renovaciones_extra_h: float = 5.0
    inicio_ventanas_min: float = 0.0
    fin_ventanas_min: float = 240.0
    temperatura_inicial_c: float = 30.0
    exterior_inicial_c: float = 34.0
    exterior_final_c: float = 34.0
    aire_habilitado: bool = True
    capacidad_total_kw: float = 6.978
    fraccion_sensible: float = 0.85
    cop: float = 3.2
    consigna_c: float = 24.0
    banda_c: float = 1.0
    modo_control: str = "Termostato"
    inicio_aire_min: float = 15.0
    fin_aire_min: float = 240.0
    duracion_min: float = 240.0
    paso_s: float = 10.0
    tarifa_kwh: float = 300.0

    @property
    def area_m2(self) -> float:
        return self.largo_m * self.ancho_m

    @property
    def volumen_m3(self) -> float:
        return self.area_m2 * self.alto_m

    @property
    def superficie_exterior_m2(self) -> float:
        return 2 * (self.largo_m + self.ancho_m) * self.alto_m * self.fraccion_pared_exterior

    @property
    def ua_w_k(self) -> float:
        pared = (self.superficie_exterior_m2 - self.ventanas_m2) * self.u_pared_w_m2k
        ventana = self.ventanas_m2 * self.u_ventana_w_m2k
        techo = self.area_m2 * self.u_techo_w_m2k if self.techo_exterior else 0.0
        return pared + ventana + techo

    @property
    def capacidad_j_k(self) -> float:
        aire = RHO_AIR_KG_M3 * CP_AIR_J_KG_K * self.volumen_m3
        return aire + self.area_m2 * self.masa_kj_m2k * 1000

    @property
    def refrigeracion_sensible_w(self) -> float:
        return self.capacidad_total_kw * self.fraccion_sensible * 1000

    def validar(self) -> None:
        booleanos = {"techo_exterior", "abrir_ventanas", "aire_habilitado"}
        for nombre, valor in asdict(self).items():
            if nombre == "modo_control":
                continue
            if nombre in booleanos:
                if not isinstance(valor, bool):
                    raise ValueError(f"{nombre} debe ser verdadero o falso.")
            elif not isinstance(valor, Real) or isinstance(valor, bool) or not math.isfinite(valor):
                raise ValueError(f"{nombre} debe ser un número finito.")
        for nombre in ["largo_m", "ancho_m", "alto_m", "cop", "duracion_min", "paso_s", "banda_c"]:
            if getattr(self, nombre) <= 0:
                raise ValueError(f"{nombre} debe ser mayor que cero.")
        for nombre in ["alumnos", "docentes"]:
            if not isinstance(getattr(self, nombre), Integral) or getattr(self, nombre) < 0:
                raise ValueError(f"{nombre} debe ser un entero no negativo.")
        for nombre in ["fraccion_pared_exterior", "factor_solar_vidrio", "fraccion_sombra", "fraccion_sensible"]:
            if not 0 <= getattr(self, nombre) <= 1:
                raise ValueError(f"{nombre} debe estar entre 0 y 1.")
        for nombre in ["ventanas_m2", "u_pared_w_m2k", "u_ventana_w_m2k", "u_techo_w_m2k",
                       "masa_kj_m2k", "calor_persona_w", "luces_w_m2", "equipos_w",
                       "irradiancia_w_m2", "renovaciones_base_h", "renovaciones_extra_h",
                       "capacidad_total_kw", "tarifa_kwh"]:
            if getattr(self, nombre) < 0:
                raise ValueError(f"{nombre} no puede ser negativo.")
        if self.ventanas_m2 > self.superficie_exterior_m2 + 1e-8:
            raise ValueError("La superficie de ventanas supera la de paredes exteriores. Ajustá la geometría o las ventanas.")
        for inicio, fin in [(self.inicio_clase_min, self.fin_clase_min),
                            (self.inicio_aire_min, self.fin_aire_min),
                            (self.inicio_ventanas_min, self.fin_ventanas_min)]:
            if not 0 <= inicio <= fin <= self.duracion_min:
                raise ValueError("Los horarios deben cumplir 0 ≤ inicio ≤ fin ≤ duración.")
        if self.modo_control not in {"Termostato", "Potencia fija"}:
            raise ValueError("Modo de control desconocido.")
        if self.duracion_min > 1440 or self.paso_s < 1:
            raise ValueError("Usá hasta 1440 minutos y un paso de al menos 1 segundo.")


def exterior(p: Parametros, minuto: float) -> float:
    """Temperatura exterior con interpolación lineal durante la simulación."""
    return p.exterior_inicial_c + (p.exterior_final_c - p.exterior_inicial_c) * minuto / p.duracion_min


def cargas(p: Parametros, minuto: float, temperatura_c: float) -> dict:
    en_clase = p.inicio_clase_min <= minuto < p.fin_clase_min
    abiertas = p.abrir_ventanas and p.inicio_ventanas_min <= minuto < p.fin_ventanas_min
    personas = (p.alumnos + p.docentes) if en_clase else 0
    ach = p.renovaciones_base_h + (p.renovaciones_extra_h if abiertas else 0)
    h_vent = RHO_AIR_KG_M3 * CP_AIR_J_KG_K * p.volumen_m3 * ach / 3600
    t_ext = exterior(p, minuto)
    personas_w = personas * p.calor_persona_w
    luces_w = p.area_m2 * p.luces_w_m2 if en_clase else 0.0
    equipos_w = p.equipos_w if en_clase else 0.0
    solar_w = p.ventanas_m2 * p.irradiancia_w_m2 * p.factor_solar_vidrio * (1 - p.fraccion_sombra)
    envolvente_w = p.ua_w_k * (t_ext - temperatura_c)
    ventilacion_w = h_vent * (t_ext - temperatura_c)
    return {
        "exterior_c": t_ext, "personas": personas, "ventanas_abiertas": abiertas,
        "ach_h": ach, "h_vent_w_k": h_vent,
        "personas_w": personas_w, "luces_w": luces_w, "equipos_w": equipos_w,
        "solar_w": solar_w, "envolvente_w": envolvente_w, "ventilacion_w": ventilacion_w,
        "ganancias_w": personas_w + luces_w + equipos_w + solar_w + envolvente_w + ventilacion_w,
    }


def _control(p: Parametros, minuto: float, temperatura_c: float, funcionando: bool) -> bool:
    if not (p.aire_habilitado and p.capacidad_total_kw > 0
            and p.inicio_aire_min <= minuto < p.fin_aire_min):
        return False
    if p.modo_control == "Potencia fija":
        return True
    if funcionando and temperatura_c <= p.consigna_c - p.banda_c / 2:
        return False
    if not funcionando and temperatura_c >= p.consigna_c + p.banda_c / 2:
        return True
    return funcionando


def simular(p: Parametros) -> pd.DataFrame:
    """Resolver C*dT/dt = H*(Tout-T) + Qinternas + Qsolar - Qfrío.

    Se usa la solución exponencial exacta para coeficientes constantes en cada
    intervalo. La temperatura exterior se evalúa en el punto medio. Se agregan
    los horarios de eventos a la grilla para no retrasar entradas ni encendidos.
    El controlador se evalúa en cada nodo (paso por defecto: 10 s).
    """
    p.validar()
    fin_s = p.duracion_min * 60
    eventos = [0, fin_s] + [60 * m for m in (
        p.inicio_clase_min, p.fin_clase_min, p.inicio_aire_min, p.fin_aire_min,
        p.inicio_ventanas_min, p.fin_ventanas_min)]
    tiempos = np.unique(np.r_[np.arange(0, fin_s, p.paso_s), eventos])
    temperatura = p.temperatura_inicial_c
    funcionando = False
    energia_kwh = 0.0
    tiempo_aire_s = 0.0
    filas = []
    for i, tiempo_s in enumerate(tiempos):
        minuto = tiempo_s / 60
        funcionando = _control(p, minuto, temperatura, funcionando)
        frio_w = p.refrigeracion_sensible_w if funcionando else 0.0
        electrica_kw = p.capacidad_total_kw / p.cop if funcionando else 0.0
        carga = cargas(p, minuto, temperatura)
        filas.append({
            "minuto": minuto, "temperatura_c": temperatura, **carga,
            "aire_encendido": funcionando, "refrigeracion_w": frio_w,
            "balance_w": carga["ganancias_w"] - frio_w,
            "electrica_kw": electrica_kw, "energia_kwh": energia_kwh,
            "tiempo_aire_min": tiempo_aire_s / 60,
            "costo_ars": energia_kwh * p.tarifa_kwh,
        })
        if i == len(tiempos) - 1:
            break
        dt_s = tiempos[i + 1] - tiempo_s
        medio_min = (tiempo_s + dt_s / 2) / 60
        medio = cargas(p, medio_min, temperatura)
        h = p.ua_w_k + medio["h_vent_w_k"]
        internas = medio["personas_w"] + medio["luces_w"] + medio["equipos_w"] + medio["solar_w"]
        if h == 0:
            temperatura += (internas - frio_w) * dt_s / p.capacidad_j_k
        else:
            equilibrio = medio["exterior_c"] + (internas - frio_w) / h
            temperatura = equilibrio + (temperatura - equilibrio) * math.exp(-h * dt_s / p.capacidad_j_k)
        energia_kwh += electrica_kw * dt_s / 3600
        tiempo_aire_s += dt_s if funcionando else 0
    return pd.DataFrame(filas)


def tiempo_hasta_banda(df: pd.DataFrame, p: Parametros) -> float | None:
    """Minutos desde habilitar el aire hasta T <= borde superior de la banda.

    Es el primer ingreso por debajo del límite superior, no tiempo de permanencia
    ni indicador de confort. Si el aula ya está debajo, devuelve cero.
    """
    if not p.aire_habilitado or p.capacidad_total_kw <= 0 or p.inicio_aire_min >= p.fin_aire_min:
        return None
    candidatos = df[(df.minuto >= p.inicio_aire_min) & (df.minuto <= p.fin_aire_min)]
    alcanza = candidatos[candidatos.temperatura_c <= p.consigna_c + p.banda_c / 2]
    return float(alcanza.iloc[0].minuto - p.inicio_aire_min) if not alcanza.empty else None


def comparar(p: Parametros) -> tuple[pd.DataFrame, pd.DataFrame]:
    return simular(p), simular(replace(p, aire_habilitado=False))


def resumir(df: pd.DataFrame, p: Parametros) -> dict:
    return {
        "temperatura_final_c": float(df.iloc[-1].temperatura_c),
        "temperatura_maxima_c": float(df.temperatura_c.max()),
        "energia_kwh": float(df.iloc[-1].energia_kwh),
        "costo_ars": float(df.iloc[-1].costo_ars),
        "tiempo_hasta_banda_min": tiempo_hasta_banda(df, p),
    }
