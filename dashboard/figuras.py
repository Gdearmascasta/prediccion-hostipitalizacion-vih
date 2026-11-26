"""Gráficas del tablero en el formato de Sigma Analist: cada función devuelve la especificación (un dict)
que dibuja assets/graficas.js en SVG propio, con leyenda que enciende y apaga series, valores a la vista,
tooltip y animación.

La paleta sale de la portada UTB (marino, turquesa, azul) y la categórica se validó contra la superficie clara
con el validador de la guía de visualización: banda de luminosidad, croma, daltonismo y contraste.
"""

# Paleta de la portada, en modo claro: texto marino sobre vidrio blanco
MARINO, AZUL, CELESTE = "#14305A", "#1A6FC0", "#7FC8F8"
TURQUESA = "#00929E"               # turquesa de la portada con el croma suficiente para trazos sobre fondo claro
PRIORITARIA = "#B8761C"            # ruta prioritaria (siempre acompañada de la palabra, nunca solo color)
NEUTRO = "#9AA8BC"                 # referencias: promedio, azar, diagonal

# Categórica validada contra la superficie clara (orden fijo; el color sigue al modelo, no a su puesto)
CATEG = ["#00929E", "#B8761C", "#1A6FC0", "#C2456E", "#7A5BD0", "#5E8A1F", "#A64FB0"]
COLOR_MODELO = {"XGBoost": CATEG[0], "Random Forest": CATEG[2], "Red neuronal": CATEG[4],
                "Árbol de decisión": CATEG[1], "KNN": CATEG[5], "Regresión logística": CATEG[3],
                "SVM gaussiana": CATEG[6]}
# Secuencial de una sola tinta (turquesa), de claro a intenso
CLARO, INTENSO = "#9FD6DD", "#006A73"


def may(s):
    """Primera letra en mayúscula sin tocar el resto (capitalize() rompería «XGBoost»)."""
    return s[:1].upper() + s[1:]


def miles(n):
    return f"{n:,.0f}".replace(",", " ")


def mezcla(t, a=CLARO, b=INTENSO):
    """Color de la escala secuencial en la posición t (0 a 1)."""
    t = max(0.0, min(1.0, t))
    ca, cb = (int(a[i:i + 2], 16) for i in (1, 3, 5)), (int(b[i:i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ca, cb))


# ----------------------------------------------------------------------------------------------------------------------
# Los datos
# ----------------------------------------------------------------------------------------------------------------------
def anual(por_anio, prev):
    return {"tipo": "barras", "titulo": "Hospitalización al notificar por año", "alto": 330, "pct": True, "dec": 1,
            "categorias": [str(r["anio"]) for r in por_anio],
            "series": [{"nombre": "Hospitalizados al notificar", "color": TURQUESA, "datos": [r["prop"] for r in por_anio]}],
            "refs": [{"eje": "y", "valor": prev, "nombre": f"Promedio del periodo ({100 * prev:.1f} %)", "color": NEUTRO}],
            "extra_tip": [{"nombre": "Casos notificados", "datos": [miles(r["n"]) for r in por_anio]}],
            "eje_y": {"titulo": "Hospitalizados"}}


def hist_edad(h, media, ancho=10):
    """Casos por grupo de edad. El .qmd exporta tramos de 5 años; se suman de a dos para que las columnas
    tengan espacio para su valor."""
    b0, c0 = h["bordes"], h["casos"]
    k = max(1, round(ancho / (b0[1] - b0[0])))
    b = b0[::k] if (len(b0) - 1) % k == 0 else b0[::k] + [b0[-1]]
    c = [sum(c0[i:i + k]) for i in range(0, len(c0), k)]
    etq = [f"{int(b[i])}–{int(b[i + 1]) - 1}" for i in range(len(c))]
    return {"tipo": "barras", "titulo": "Edad al notificarse", "alto": 330, "dec": 0, "unidad": "casos",
            "categorias": etq,
            "series": [{"nombre": f"Casos por grupo de {ancho} años", "color": AZUL, "datos": c,
                        "etiquetas": [f"{v / 1000:.1f} mil" if v >= 1000 else str(v) for v in c]}],
            "refs": [{"eje": "x", "valor": min(int(media // ancho), len(c) - 1), "nombre": f"Edad media ({media:.1f} años)",
                      "color": PRIORITARIA}],
            "eje_y": {"titulo": "Casos"}}


def factor(filas, nombre, prev):
    return {"tipo": "barras", "titulo": f"Hospitalizados según {nombre}", "alto": 340, "pct": True, "dec": 1,
            "categorias": [f["nivel"] for f in filas],
            "series": [{"nombre": f"Hospitalizados según {nombre}", "color": TURQUESA, "datos": [f["prop"] for f in filas]}],
            "refs": [{"eje": "y", "valor": prev, "nombre": f"Promedio ({100 * prev:.1f} %)", "color": NEUTRO}],
            "extra_tip": [{"nombre": "Casos", "datos": [miles(f["n"]) for f in filas]}],
            "eje_y": {"titulo": "Hospitalizados"}}


def departamentos(filas, orden, top=15):
    clave = "n" if orden == "casos" else "prop"
    sel = sorted([f for f in filas if f["n"] >= 200], key=lambda f: f[clave], reverse=True)[:top]
    lo, hi = min(f["prop"] for f in sel), max(f["prop"] for f in sel)
    return {"tipo": "barras_h", "titulo": "Departamentos de residencia", "alto": 470, "dec": 0, "unidad": "casos",
            "categorias": [f["nivel"] for f in sel],
            "series": [{"nombre": "Casos notificados", "color": INTENSO, "datos": [f["n"] for f in sel],
                        "colores": [mezcla((f["prop"] - lo) / ((hi - lo) or 1)) for f in sel],
                        "etiquetas": [f"{miles(f['n'])} · {100 * f['prop']:.1f} %" for f in sel]}],
            "leyenda_extra": [{"nombre": f"Menos hospitalizados ({100 * lo:.1f} %)", "color": CLARO, "cuadro": True},
                              {"nombre": f"Más hospitalizados ({100 * hi:.1f} %)", "color": INTENSO, "cuadro": True}],
            "extra_tip": [{"nombre": "Hospitalizados", "datos": [f"{100 * f['prop']:.1f} %" for f in sel]}],
            "eje_x": {"titulo": "Casos notificados"}}


# ----------------------------------------------------------------------------------------------------------------------
# Modelos
# ----------------------------------------------------------------------------------------------------------------------
def pliegues(cv, metrica, elegido):
    d = cv[cv.metrica == metrica]
    res = d.groupby("modelo").valor.agg(["mean", "std"]).sort_values("mean", ascending=False)
    filas = [{"nombre": m, "color": COLOR_MODELO.get(m, NEUTRO), "elegido": m == elegido,
              "valores": d[d.modelo == m].sort_values("pliegue").valor.round(6).tolist(),
              "media": float(res.loc[m, "mean"]), "de": float(res.loc[m, "std"])} for m in res.index]
    return {"tipo": "tiras", "titulo": f"{metrica} de cada modelo en cada pliegue", "alto": 400, "filas": filas,
            "leyenda_extra": [{"nombre": "Media del modelo (rombo)", "color": MARINO, "cuadro": True},
                              {"nombre": "Cada pliegue (puntos)", "color": NEUTRO, "cuadro": True},
                              {"nombre": "Una desviación típica (barra)", "color": NEUTRO, "guion": False}],
            "eje_x": {"titulo": f"{metrica} fuera de pliegue"}}


def curvas(c, tipo, orden, prev):
    roc = tipo == "roc"
    series = [{"nombre": f"{m} · {c[m]['auc' if roc else 'ap']:.3f}", "color": COLOR_MODELO.get(m, NEUTRO),
               "x": c[m]["roc" if roc else "pr"]["x"], "y": c[m]["roc" if roc else "pr"]["y"],
               "ancho": 3.2 if m == "XGBoost" else 2} for m in orden]
    ref = [0, 1] if roc else [prev, prev]
    series.append({"nombre": f"Sin información · {0.5 if roc else prev:.3f}", "color": NEUTRO, "x": [0, 1], "y": ref,
                   "guion": True, "sin_tip": True})
    return {"tipo": "xy", "titulo": "Curvas ROC" if roc else "Curvas de precisión y sensibilidad", "alto": 400,
            "series": series, "dec": 3, "dec_x": 2,
            "titulo_x": "1 − especificidad " if roc else "sensibilidad ",
            "eje_x": {"min": 0, "max": 1, "titulo": "1 − especificidad (sanos marcados)" if roc else "Sensibilidad"},
            "eje_y": {"min": 0, "max": 1, "titulo": "Sensibilidad" if roc else "Precisión"}}


# ----------------------------------------------------------------------------------------------------------------------
# Umbral y prueba
# ----------------------------------------------------------------------------------------------------------------------
def costo(malla, u_sel, u_def, p_star):
    """Costo esperado según el umbral. A pedido del usuario se conserva en Plotly, como estaba antes del formato
    Sigma: área turquesa, líneas del umbral elegido y del óptimo teórico, y el punto blanco del umbral elegido arriba."""
    import plotly.graph_objects as go
    tenue, rejilla = "rgba(20,48,90,0.62)", "rgba(20,48,90,0.08)"
    u = [r["u"] for r in malla]
    c = [r["costo"] / 1e9 for r in malla]
    fig = go.Figure(go.Scatter(x=u, y=c, mode="lines", name="Costo esperado (miles de millones de pesos)",
                               line=dict(color=TURQUESA, width=2.5), fill="tozeroy", fillcolor="rgba(0,146,158,0.10)",
                               hovertemplate="umbral %{x:.2f}<br>%{y:.2f} mil millones<extra></extra>"))
    sel = min(malla, key=lambda r: abs(r["u"] - u_sel))
    for x, nombre, color, guion in [(u_def, f"Elegido por costo ({u_def:.2f})", PRIORITARIA, "solid"),
                                    (p_star, f"Óptimo teórico ({p_star:.3f})", CELESTE, "dash")]:
        trazo = dict(color=color, dash=guion, width=1.5)
        fig.add_vline(x=x, line=trazo, layer="below")
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name=nombre, line=trazo, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[sel["u"]], y=[sel["costo"] / 1e9], mode="markers+text", name=f"Su umbral ({sel['u']:.2f})",
                             text=[f"{sel['costo'] / 1e9:.2f}"], textposition="top right", textfont=dict(color=MARINO),
                             marker=dict(size=14, color="#FFFFFF", line=dict(width=3, color=MARINO)),
                             hovertemplate="su umbral %{x:.2f}<br>%{y:.2f} mil millones<extra></extra>"))
    fig.update_layout(
        height=360, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", separators=". ", showlegend=True,
        font=dict(family="Inter, Segoe UI, sans-serif", color=MARINO, size=12.5), margin=dict(l=10, r=14, t=46, b=10),
        hoverlabel=dict(bgcolor="rgba(255,255,255,0.97)", bordercolor="rgba(0,146,158,0.55)",
                        font=dict(family="Inter, sans-serif", color=MARINO, size=12.5)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)"),
        modebar=dict(bgcolor="rgba(0,0,0,0)", color=tenue, activecolor=AZUL),
        transition=dict(duration=450, easing="cubic-in-out"))
    fig.update_xaxes(title="Umbral de decisión", range=[0, 1], gridcolor=rejilla, zeroline=False, linecolor=rejilla,
                     tickfont=dict(color=tenue), title_font=dict(color=tenue, size=12))
    fig.update_yaxes(title="Costo (miles de millones)", rangemode="tozero", gridcolor=rejilla, zeroline=False,
                     linecolor=rejilla, tickfont=dict(color=tenue), title_font=dict(color=tenue, size=12))
    return fig


def calibracion(pred, obs):
    hasta = round(max(max(pred), max(obs)) * 1.12, 2)
    return {"tipo": "xy", "titulo": "Calibración por deciles", "alto": 360, "pct": True, "pct_x": True, "dec": 1,
            "titulo_x": "predicho ",
            "series": [{"nombre": "Modelo definitivo (deciles)", "color": TURQUESA, "x": pred, "y": obs, "puntos": True,
                        "etiquetas": [f"{100 * v:.0f}%" for v in obs]},
                       {"nombre": "Calibración perfecta", "color": NEUTRO, "x": [0, hasta], "y": [0, hasta], "guion": True,
                        "sin_tip": True}],
            "eje_x": {"min": 0, "max": hasta, "titulo": "Probabilidad predicha"},
            "eje_y": {"min": 0, "max": hasta, "titulo": "Proporción observada"}}


def confusion(vp, fn, fp, vn):
    n = vp + fn + fp + vn
    z = [[vp, fn], [fp, vn]]
    etq = [["Detectado", "No detectado"], ["Contacto de más", "Bien descartado"]]
    return {"tipo": "calor", "titulo": "Matriz de la prueba", "alto": 330, "nombre_z": "Casos",
            "filas": ["Hospitalizado", "No hospitalizado"], "columnas": ["Ruta prioritaria", "Trámite habitual"],
            "z": z, "escala": ["#E6F4F6", "#2BB3C0"],
            "texto": [[f"{etq[i][j]}\n{miles(z[i][j])}\n{100 * z[i][j] / n:.1f} %" for j in range(2)] for i in range(2)],
            "leyenda_extra": [{"nombre": "Pocos casos", "color": "#E6F4F6", "cuadro": True},
                              {"nombre": "Muchos casos", "color": "#2BB3C0", "cuadro": True}]}


# ----------------------------------------------------------------------------------------------------------------------
# Clasificación en lote
# ----------------------------------------------------------------------------------------------------------------------
def lote(filas, umbral):
    filas = sorted(filas, key=lambda f: -f["prob"])
    return {"tipo": "barras_h", "titulo": "Fichas de prueba ordenadas por probabilidad", "alto": 360, "pct": True, "dec": 1,
            "categorias": [f["id"] for f in filas], "titulos": [f"{f['id']} · {f['titulo']}" for f in filas],
            "series": [{"nombre": "Probabilidad de haber llegado hospitalizado", "color": AZUL,
                        "datos": [f["prob"] for f in filas],
                        "colores": [PRIORITARIA if f["prioritaria"] else AZUL for f in filas]}],
            "refs": [{"eje": "x", "valor": umbral, "nombre": f"Umbral ({100 * umbral:.0f} %)", "color": MARINO}],
            "leyenda_extra": [{"nombre": "Ruta prioritaria", "color": PRIORITARIA, "cuadro": True},
                              {"nombre": "Trámite habitual", "color": AZUL, "cuadro": True}],
            "extra_tip": [{"nombre": "Decisión", "datos": ["Ruta prioritaria" if f["prioritaria"] else "Trámite habitual"
                                                           for f in filas]}],
            "eje_x": {"min": 0, "max": 1, "titulo": "Probabilidad"}}


# ----------------------------------------------------------------------------------------------------------------------
# Variables y equidad
# ----------------------------------------------------------------------------------------------------------------------
def importancia(filas):
    filas = sorted(filas, key=lambda f: -f["media"])
    return {"tipo": "barras_h", "titulo": "Importancia por permutación", "alto": 460, "dec": 4,
            "categorias": [may(f["etiqueta"]) for f in filas],
            "series": [{"nombre": "Caída del AUC al desordenar la variable", "color": TURQUESA,
                        "datos": [f["media"] for f in filas], "error": [f["sd"] for f in filas]}],
            "extra_tip": [{"nombre": "Desviación entre repeticiones", "datos": [f"{f['sd']:.4f}" for f in filas]}],
            "eje_x": {"titulo": "Caída del AUC"}}


def subgrupos(filas):
    return {"tipo": "barras", "titulo": "Desempeño por subgrupo", "alto": 370, "pct": True, "dec": 0, "dec_tip": 1,
            "categorias": [f["nivel"] for f in filas],
            "series": [{"nombre": "Sensibilidad", "color": TURQUESA, "datos": [f["sens"] for f in filas]},
                       {"nombre": "Especificidad", "color": AZUL, "datos": [f["espec"] for f in filas]},
                       {"nombre": "Casos marcados", "color": PRIORITARIA, "datos": [f["alerta"] for f in filas]}],
            "extra_tip": [{"nombre": "Casos de prueba", "datos": [miles(f["n"]) for f in filas]}],
            "eje_y": {"min": 0, "max": 1}}


def proxy(filas, alto):
    return {"tipo": "barras", "titulo": "Reconstrucción del atributo protegido", "alto": 340, "dec": 3,
            "categorias": [f["atributo"] for f in filas],
            "series": [{"nombre": "AUC al reconstruir el atributo", "color": AZUL, "datos": [f["auc"] for f in filas],
                        "error": [f["sd"] for f in filas],
                        "colores": [PRIORITARIA if f["auc"] >= alto else AZUL for f in filas]}],
            "refs": [{"eje": "y", "valor": 0.5, "nombre": "Azar (0.50)", "color": NEUTRO},
                     {"eje": "y", "valor": alto, "nombre": f"Se reconstruye (≥ {alto:.2f})", "color": PRIORITARIA}],
            "extra_tip": [{"nombre": "Proporción", "datos": [f"{100 * f['prev']:.1f} %" for f in filas]}],
            "eje_y": {"min": 0.4, "max": 1, "titulo": "AUC"}}


def sin_atributo(filas):
    idx = {(f["version"], f["nivel"]): f for f in filas}
    cats = [(k, s) for k in ("tpr", "fpr") for s in ("Mujer", "Hombre")]
    nombre = {"tpr": "detectados", "fpr": "sanos marcados"}
    return {"tipo": "barras", "titulo": "Modelo con y sin el sexo", "alto": 340, "pct": True, "dec": 1,
            "categorias": [s for _, s in cats], "sub": [nombre[k] for k, _ in cats],
            "series": [{"nombre": "Con el sexo en el modelo", "color": TURQUESA, "datos": [idx[("con", s)][k] for k, s in cats]},
                       {"nombre": "Sin el sexo", "color": CATEG[4], "datos": [idx[("sin", s)][k] for k, s in cats]}],
            "eje_y": {"min": 0, "max": 1}}


# ----------------------------------------------------------------------------------------------------------------------
# Monitoreo y más allá del clasificador
# ----------------------------------------------------------------------------------------------------------------------
def psi(filas, anios, bandas):
    banda = lambda v: "estable" if v < bandas[0] else ("vigilar" if v < bandas[1] else "actuar")
    z = [[f[str(a)] for a in anios] for f in filas]
    tope = max(bandas[1], max(max(r) for r in z))
    c0, c1 = "#EEF7FA", "#2BB3C0"
    return {"tipo": "calor", "titulo": "Índice de estabilidad poblacional", "alto": 440, "nombre_z": "PSI",
            "filas": [may(f["etiqueta"]) for f in filas], "columnas": [str(a) for a in anios], "z": z,
            "zmin": 0, "zmax": tope, "escala": [c0, c1],
            "texto": [[f"{v:.3f}\n{banda(v)}" for v in fila] for fila in z],
            "leyenda_extra": [{"nombre": f"Estable (< {bandas[0]})", "color": mezcla(0, c0, c1), "cuadro": True},
                              {"nombre": f"Vigilar ({bandas[0]}–{bandas[1]})", "color": mezcla(bandas[0] / tope, c0, c1),
                               "cuadro": True},
                              {"nombre": f"Actuar (≥ {bandas[1]})", "color": mezcla(bandas[1] / tope, c0, c1), "cuadro": True}]}


def por_anio_modelo(filas, vista):
    disc = vista == "disc"
    series = ([("auc", "AUC", TURQUESA), ("sens", "Sensibilidad", PRIORITARIA)] if disc else
              [("obs", "Hospitalizados observados", TURQUESA), ("p_media", "Probabilidad media del modelo", CATEG[4])])
    spec = {"tipo": "lineas", "titulo": "Desempeño por año", "alto": 340,
            "categorias": [str(r["anio"]) for r in filas],
            "series": [{"nombre": n, "color": c, "datos": [r[k] for r in filas]} for k, n, c in series],
            "eje_x": {"titulo": "Año de notificación"}}
    spec.update({"dec": 3} if disc else {"pct": True, "dec": 1})
    return spec


ORDEN_GRUPOS = [0, 1, 2, 4, 3, 5]


def acp(a, nombres):
    grupos = sorted(set(a["grupo"]))
    series = []
    for i, g in enumerate(grupos):
        m = [j for j, x in enumerate(a["grupo"]) if x == g]
        series.append({"nombre": f"{g}. {nombres.get(str(g), f'Grupo {g}')} ({len(m)} puntos)",
                       "color": CATEG[ORDEN_GRUPOS[i % 6]], "x": [round(a["pc1"][j], 3) for j in m],
                       "y": [round(a["pc2"][j], 3) for j in m]})
    v = a["var"]
    return {"tipo": "dispersion", "titulo": "Mapa del análisis de componentes", "alto": 380, "series": series,
            "eje_x": {"titulo": f"Componente 1 ({100 * v[0]:.1f} % de la varianza)"},
            "eje_y": {"titulo": f"Componente 2 ({100 * v[1]:.1f} %)"}}


PERFIL_CAMPOS = [("hombres", "Hombres"), ("contributivo", "Contributivo"), ("subsidiado", "Subsidiado"),
                 ("no_asegurado", "No asegurado"), ("migrante", "Migrante"), ("caribe", "Región Caribe"),
                 ("sin_fecha", "Sin fecha de síntomas"), ("hosp", "Hospitalizados*")]


def perfil(filas, nombres):
    return {"tipo": "barras", "titulo": "Qué distingue a los grupos", "alto": 360, "pct": True, "dec": 0, "dec_tip": 1,
            "categorias": [e for _, e in PERFIL_CAMPOS],
            "series": [{"nombre": f"{f['grupo']}. {nombres.get(str(f['grupo']), '')}", "color": CATEG[ORDEN_GRUPOS[i % 6]],
                        "datos": [f[k] for k, _ in PERFIL_CAMPOS]} for i, f in enumerate(filas)],
            "eje_y": {"min": 0, "max": 1}}


def serie(s):
    n = len(s["casos"])
    ev = [i for i, e in enumerate(s["evaluacion"]) if e]
    inicios = [i for i in range(n) if i == 0 or s["anio"][i] != s["anio"][i - 1]]
    mae_ing = s["err_ingenuos"][s["nombre_ingenuo"]]["mae"]
    return {"tipo": "xy", "titulo": "Casos notificados por semana", "alto": 380, "dec": 0, "unidad": "casos",
            "etiquetas_x": [f"{a} · semana {w}" for a, w in zip(s["anio"], s["semana"])],
            "series": [{"nombre": "Casos observados", "color": "#6B7A90", "x": list(range(n)), "y": s["casos"], "ancho": 1.6},
                       {"nombre": f"LSTM (MAE {s['err_lstm']['mae']['media']:.1f})", "color": TURQUESA, "x": ev,
                        "y": [round(v, 1) for v in s["lstm"]], "ancho": 2.4},
                       {"nombre": f"{s['nombre_ingenuo']} (MAE {mae_ing:.1f})", "color": PRIORITARIA, "x": ev,
                        "y": s["ingenuo"], "guion": True, "ancho": 1.8}],
            "bandas": [{"x0": ev[0], "x1": ev[-1], "etiqueta": "evaluación"}],
            "ticks_x": [{"x": i, "etiqueta": str(s["anio"][i])} for i in inicios],
            "rangos": [{"etiqueta": "Todo el periodo", "x0": 0, "x1": n - 1},
                       {"etiqueta": "Años de evaluación", "x0": ev[0], "x1": ev[-1]}],
            "eje_y": {"titulo": "Casos por semana"}}
