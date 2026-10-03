"""Gráficos y plano esquemático. El plano no estima una distribución espacial."""

import math
import numpy as np
import plotly.graph_objects as go
from plotly.colors import sample_colorscale

from modelo import Parametros

AZUL = "#157f9b"
NARANJA = "#da7948"


def estilo(fig, alto=390):
    fig.update_layout(
        template="plotly_white", height=alto, margin=dict(l=15, r=20, t=35, b=25),
        font=dict(family="Arial, sans-serif", color="#253c4a"),
        legend=dict(orientation="h", yanchor="bottom", y=1.04, x=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#fbfcfd",
    )
    return fig


def curva_temperatura(con, sin, p: Parametros, minuto=None, mediciones=None):
    fig = go.Figure()
    fig.add_hrect(y0=p.consigna_c - p.banda_c / 2, y1=p.consigna_c + p.banda_c / 2,
                  fillcolor="#c5e8df", opacity=.45, line_width=0,
                  annotation_text="Banda del termostato", annotation_position="bottom right")
    fig.add_trace(go.Scatter(x=sin.minuto, y=sin.temperatura_c, name="Sin aire",
                            line=dict(color=NARANJA, width=2, dash="dash")))
    fig.add_trace(go.Scatter(x=con.minuto, y=con.temperatura_c, name="Con la configuración elegida",
                            line=dict(color=AZUL, width=3)))
    fig.add_trace(go.Scatter(x=con.minuto, y=con.exterior_c, name="Exterior",
                            line=dict(color="#82949d", width=1.5, dash="dot")))
    if p.aire_habilitado:
        fig.add_vline(x=p.inicio_aire_min, line_dash="dot", line_color=AZUL,
                      annotation_text="Aire habilitado", annotation_position="top left")
    if minuto is not None:
        fig.add_vline(x=minuto, line_color="#253c4a", line_width=1)
    if mediciones is not None:
        fig.add_trace(go.Scatter(x=mediciones.minuto, y=mediciones.temperatura_c,
                                mode="markers", name="Mediciones cargadas",
                                marker=dict(color="#7950a8", size=8)))
    fig.update_layout(xaxis_title="Tiempo desde el inicio (min)", yaxis_title="Temperatura (°C)",
                      hovermode="x unified")
    fig.update_traces(hovertemplate="%{y:.2f} °C<extra>%{fullData.name}</extra>")
    return estilo(fig)


def plano_aula(p: Parametros, fila):
    temperatura = float(fila.temperatura_c)
    color = sample_colorscale("RdBu_r", [float(np.clip((temperatura - 18) / 20, 0, 1))])[0]
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, x1=p.ancho_m, y0=0, y1=p.largo_m,
                  fillcolor=color, opacity=.35, line=dict(color="#375765", width=3))
    fig.add_shape(type="rect", x0=p.ancho_m*.3, x1=p.ancho_m*.7, y0=.2, y1=.4,
                  fillcolor="#375765", line_width=0)
    fig.add_annotation(x=p.ancho_m/2, y=.05, text="Pizarrón", showarrow=False, yanchor="bottom")
    n = p.alumnos if int(fila.personas) else 0
    visibles = min(n, 100)
    columnas = max(1, min(10, math.ceil(math.sqrt(visibles * p.ancho_m / p.largo_m))))
    renglones = max(1, math.ceil(visibles / columnas))
    x, y = [], []
    for i in range(visibles):
        x.append((i % columnas + 1) * p.ancho_m / (columnas + 1))
        y.append(1.35 + (i // columnas + .5) * max(.1, p.largo_m - 2.4) / renglones)
    fig.add_trace(go.Scatter(x=x, y=y, mode="markers", name="Alumnos",
                            marker=dict(size=15, color="#31566d", symbol="square", opacity=.4),
                            hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x, y=[v-.12 for v in y], mode="markers", name="Alumnos",
                            marker=dict(size=9, color="#253c4a"), showlegend=False,
                            hovertemplate=f"Alumno · temperatura media {temperatura:.1f} °C<extra></extra>"))
    if int(fila.personas) and p.docentes:
        fig.add_trace(go.Scatter(x=[p.ancho_m/2], y=[.8], mode="markers", name="Docentes",
                                marker=dict(size=13, color="#986534", symbol="diamond"),
                                hovertemplate=f"{p.docentes} docente(s)<extra></extra>"))
    ventana_color = AZUL if bool(fila.ventanas_abiertas) else "#7ba8b6"
    if p.ventanas_m2:
        for y0 in np.linspace(p.largo_m*.25, p.largo_m*.75, 3):
            fig.add_shape(type="line", x0=0, x1=0, y0=y0-.3, y1=y0+.3,
                          line=dict(color=ventana_color, width=8))
    estado = "Enfriando" if bool(fila.aire_encendido) else ("En espera" if p.aire_habilitado else "Sin aire")
    fig.add_shape(type="rect", x0=p.ancho_m*.35, x1=p.ancho_m*.65,
                  y0=p.largo_m-.4, y1=p.largo_m-.1, fillcolor="#f2f7fa",
                  line=dict(color=AZUL if bool(fila.aire_encendido) else "#8a9ba3", width=2))
    fig.add_annotation(x=p.ancho_m/2, y=p.largo_m-.25, text=estado, showarrow=False,
                       font=dict(size=11, color="#253c4a"))
    if bool(fila.aire_encendido):
        fig.add_annotation(x=p.ancho_m/2, y=p.largo_m-1.3, ax=p.ancho_m/2, ay=p.largo_m-.6,
                           axref="x", ayref="y", arrowhead=3, arrowwidth=3, arrowcolor=AZUL,
                           text="", showarrow=True)
    fig.update_layout(title=f"{temperatura:.1f} °C de temperatura media · {int(fila.personas)} personas",
                      showlegend=False,
                      xaxis=dict(range=[-.45, p.ancho_m+.45], title="Ancho (m)", showgrid=False, zeroline=False),
                      yaxis=dict(range=[-.35, p.largo_m+.45], title="Largo (m)", showgrid=False,
                                 zeroline=False, scaleanchor="x", scaleratio=1))
    if n > 100:
        fig.add_annotation(x=p.ancho_m/2, y=p.largo_m+0.15, text=f"Se dibujan 100 de {n} alumnos",
                           showarrow=False, font=dict(size=10))
    return estilo(fig, 430)


def balance(fila):
    nombres = ["Personas", "Iluminación", "Equipos", "Sol", "Envolvente", "Ventilación", "Aire acondicionado"]
    valores = [fila.personas_w, fila.luces_w, fila.equipos_w, fila.solar_w,
               fila.envolvente_w, fila.ventilacion_w, -fila.refrigeracion_w]
    fig = go.Figure(go.Bar(y=nombres, x=np.array(valores)/1000, orientation="h",
                          marker_color=[NARANJA if v >= 0 else AZUL for v in valores],
                          hovertemplate="%{y}: %{x:.2f} kW<extra></extra>"))
    fig.add_vline(x=0, line_width=1, line_color="#526773")
    fig.update_layout(xaxis_title="Calor que entra (+) o sale (-), en kW", yaxis=dict(autorange="reversed"))
    return estilo(fig, 370)
