"""Tablero del artículo
«Predicción de la hospitalización en la notificación de VIH con datos de vigilancia: SIVIGILA, Colombia, 2018–2025».

Uso, desde la raíz del repositorio y con el entorno activado:
    python dashboard/app.py            (http://127.0.0.1:8050)

No entrena nada: lee lo que genera el artículo (ver datos.py). Las cifras de las figuras salen de
resultados/tablero.json, que escribe el bloque exporta-tablero del .qmd; la predicción, de cargar_y_predecir.py.
"""
import datetime as dt
import json
import os

import dash
from dash import Input, Output, State, dcc, html, no_update

import datos as D
import figuras as F

GSAP = ["https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"]
app = dash.Dash(__name__, title="VIH · SIVIGILA · Tablero", external_scripts=GSAP,
                suppress_callback_exceptions=True, update_title=None)
server = app.server                     # para Posit Connect o gunicorn: dashboard.app:server
app.index_string = app.index_string.replace("<html>", '<html lang="es">')

REPOSITORIO = "https://github.com/DidierAgamez/Prediccion-Hostipitalizacion-VIH-colombia"   # el mismo del código QR

# ----------------------------------------------------------------------------------------------------------------------
# Piezas
# ----------------------------------------------------------------------------------------------------------------------
def ayuda(titulo, texto):
    """Botón flotante que explica en breve qué cuenta la gráfica."""
    return html.Div(className="ayuda", tabIndex=0, role="button", **{"aria-label": f"Qué muestra: {titulo}"}, children=[
        html.Span("i", className="ayuda-icono"),
        html.Div(className="ayuda-texto", role="tooltip", children=[html.Strong("Qué muestra"), html.P(texto)])])


def panel(titulo, sub, explicacion, *hijos, clase=""):
    cab = [html.Div([html.H3(titulo), html.P(sub) if sub else None])]
    if explicacion:
        cab.append(ayuda(titulo, explicacion))
    return html.Div(className=f"vidrio panel revelar {clase}", children=[html.Div(cab, className="panel-cabecera"), *hijos])


def sg(spec):
    """Gráfica en el formato de Sigma Analist: assets/graficas.js la dibuja a partir de su especificación."""
    return html.Div(className="sg", **{"data-spec": json.dumps(spec, ensure_ascii=False, separators=(",", ":"))})


def grafica(spec=None, id=None, alto=None):
    # el contenedor reserva la altura para que la página no salte mientras el SVG se dibuja
    alto = alto or (spec.get("alto") if spec else 340)
    return html.Div(id=id, className="grafica-caja", style={"minHeight": f"{alto + 40}px"},
                    children=sg(spec) if spec else None) if id else \
        html.Div(className="grafica-caja", style={"minHeight": f"{alto + 40}px"}, children=sg(spec))


def kpi(titulo, valor, detalle="", color="var(--azul)", contador=True, revelar=True):
    # las tarjetas que rehace un callback no se vuelven a animar en cada cambio del control
    return html.Div(className="kpi revelar" if revelar else "kpi", style={"--c": color}, children=[
        html.Span(titulo, className="kpi-titulo"),
        html.Span(valor, className="kpi-valor" + (" contador" if contador else "")),
        html.Span(detalle, className="kpi-detalle")])


def seccion(titulo, texto):
    return html.Div(className="seccion", children=[
        html.H2(titulo, **{"data-palabras": "1"}), html.P(texto, className="revelar"), html.Div(className="regla")])


def pastillas(id, opciones, valor):
    return dcc.RadioItems(id=id, options=[{"label": e, "value": v} for v, e in opciones], value=valor,
                          className="pastillas", inline=True)


def tabla(columnas, filas, destacar=None):
    return html.Div(className="tabla-envoltura", children=html.Table(className="tabla", children=[
        html.Thead(html.Tr([html.Th(c) for c in columnas])),
        html.Tbody([html.Tr([html.Td(v) for v in f], className="destacada" if destacar and destacar(i) else "")
                    for i, f in enumerate(filas)])]))


def falta_tablero():
    return html.Div(className="vidrio aviso ensayo revelar", children=[
        html.Span("!", className="aviso-icono"),
        html.Div([html.B("Faltan las cifras del artículo. "),
                  "No encuentro resultados/tablero.json. Genere el artículo una vez (quarto render "
                  "articulo_ML_Agamez_final.qmd) para que el bloque exporta-tablero escriba ese archivo."])])


def bandas_portada():
    """Las bandas curvas de la portada UTB, en SVG para que escalen sin imagen."""
    return html.Div(className="hero-bandas", children=dcc.Markdown(dangerously_allow_html=True, children="""
<svg viewBox="0 0 600 400" preserveAspectRatio="none" width="100%" height="100%" aria-hidden="true">
  <defs>
    <linearGradient id="gb1" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2BB3C0"/><stop offset="1" stop-color="#1A6FC0"/></linearGradient>
    <linearGradient id="gb2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2BB3C0" stop-opacity=".55"/><stop offset="1" stop-color="#1A6FC0" stop-opacity=".55"/></linearGradient>
  </defs>
  <path d="M170 0 C 250 90, 120 210, 260 400 L600 400 L600 0 Z" fill="url(#gb2)" opacity=".35"/>
  <path d="M280 0 C 360 110, 230 240, 380 400 L600 400 L600 0 Z" fill="url(#gb1)" opacity=".55"/>
  <path d="M400 0 C 470 120, 360 260, 490 400 L600 400 L600 0 Z" fill="url(#gb1)" opacity=".8"/>
</svg>"""))


def tarjeta_regla(T):
    """Lo que logra la regla, con la coreografía de las barras de modelos de Sigma Analist: cifras que cuentan,
    barras que crecen en cascada, botones Prueba / Validación cruzada / Comparar y orden con animación.
    La interacción vive en assets/animaciones.js ([data-regla]); aquí solo van los datos."""
    mp, P = D.MP, (T["prueba"] if T else None)
    prueba = {"sens": mp["sensibilidad"], "espec": mp["especificidad"], "prec": mp["precision"],
              "alerta": P["alerta"] if P else None}
    cv = None
    if T:
        r = min(T["umbral"]["malla"], key=lambda f: abs(f["u"] - T["umbral"]["u_def"]))
        cv = {"sens": r["sens"], "espec": r["espec"], "prec": r["prec"], "alerta": r["alerta"]}
    filas_def = [("sens", "Hospitalizados detectados", "sensibilidad"),
                 ("espec", "No hospitalizados bien descartados", "especificidad"),
                 ("prec", "Aciertos entre los marcados", "precisión"),
                 ("alerta", "Notificaciones que se marcan", "carga de contactos")]
    filas = []
    for i, (k, nombre, sub) in enumerate(filas_def):
        vp, vc = prueba[k], (cv[k] if cv else None)
        if vp is None:
            continue
        vc = vp if vc is None else vc
        filas.append(html.Li(className="regla-fila" + (" campeona" if k == "sens" else ""),
                             style={"--i": i}, **{"data-prueba": f"{vp:.4f}", "data-cv": f"{vc:.4f}"}, children=[
            html.Span([nombre, html.Small(sub)], className="regla-nombre"),
            html.Span(className="regla-pista", **{"aria-hidden": "true"}, children=[
                html.Span(className="regla-barra cv", style={"--v": f"{vc:.4f}"}),
                html.Span(className="regla-barra prueba", style={"--v": f"{vp:.4f}"})]),
            html.B(className="regla-valor", children=[
                html.Span(D.pct(vp), className="v-prueba"), html.Span(D.pct(vc), className="v-cv"),
                html.Span(f"{D.pct(vc)} → {D.pct(vp)}", className="v-ambos")]),
        ]))
    n_pru = mp["casos"]
    ideas = {"prueba": f"En {D.miles(n_pru)} notificaciones nunca vistas, la regla encuentra a {round(100 * mp['sensibilidad'])} "
                       f"de cada 100 hospitalizados y acierta en {round(100 * mp['precision'])} de cada 100 marcados.",
             "cv": "Con las probabilidades fuera de pliegue y el mismo umbral, las cifras son casi las mismas: la regla "
                   "no se ajustó a la prueba." if cv else "",
             "ambos": "Barra clara: validación cruzada; barra intensa: prueba. Si casi coinciden, el desempeño es "
                      "estable fuera de los datos de entrenamiento." if cv else ""}
    botones = [("prueba", "Prueba")] + ([("cv", "Validación cruzada"), ("ambos", "Comparar")] if cv else [])
    stats = [(f"{round(100 * mp['sensibilidad'])}", "de cada 100 hospitalizados la regla los envía a ruta prioritaria"),
             (f"{round(100 * mp['precision'])}", "de cada 100 marcados sí estaban hospitalizados"),
             (f"{1 / mp['precision']:.1f}", "contactos por cada hospitalizado que se encuentra")]
    return html.Div(children=[
        html.Ul(className="stats-sigma ola", children=[
            html.Li(className="stat-sigma revelar", children=[html.B(v, className="contador"), html.Span(e)]) for v, e in stats]),
        html.Figure(className="tarjeta-regla", **{"data-regla": "1", "data-modo": "prueba",
                                                   "data-idea-prueba": ideas["prueba"], "data-idea-cv": ideas["cv"],
                                                   "data-idea-ambos": ideas["ambos"]}, children=[
            html.Div(className="regla-herramientas", children=[
                html.Div(className="segmentado", role="group", **{"aria-label": "Conjunto de datos"}, children=[
                    html.Button(e, type="button", **{"data-modo": m, "aria-pressed": "true" if m == "prueba" else "false"})
                    for m, e in botones]),
                html.Button("Ordenar de mayor a menor", type="button", className="chip", **{"data-ordenar": "1",
                                                                                           "aria-pressed": "false"}),
            ]),
            html.P(className="regla-leyenda", children=[
                html.Span([html.I(className="muestra prueba"), "Prueba (28 476 casos, usada una vez)".replace(
                    "28 476", D.miles(n_pru))]),
                html.Span([html.I(className="muestra cv"), "Validación cruzada, mismo umbral"]) if cv else None]),
            html.Ol(filas, className="regla-lista"),
            html.Figcaption(ideas["prueba"], className="regla-idea", **{"data-regla-idea": "1"}),
        ]),
    ])


PASOS_LIMPIEZA = [   # nombre corto, título y explicación de cada filtro del .qmd, reconocido por su texto
    ("duplicad", "Duplicados", "Se quitan los duplicados",
     "Registros repetidos en la llave de ocho campos (fecha, edad, sexo, institución, municipio y fechas clínicas)."),
    ("edad", "Edad", "Solo edades posibles",
     "Edades por encima de 100 años son errores de digitación y el registro sale."),
    ("sexo", "Sexo y hosp.", "Sexo y hospitalización válidos",
     "Sin sexo registrado o sin el dato de hospitalización, el caso no se puede usar para el modelo."),
]


def recorrido_datos(T):
    """Datos de la tarjeta de pasos (assets/recorrido.js): todo sale de tablero.json, del contrato y de la base."""
    M, C, flujo = T["meta"], D.CONTRATO, T["flujo"]
    n_col, n_var = D.columnas_base(), len(C["columnas"])
    n_tv, n_pru = M["n_ent"] + M["n_val"], M["n_pru"]
    menos = lambda n: "ninguno sale" if n == 0 else f"−{D.miles(n)} registros"
    pasos = [{"nombre": "Base unida", "titulo": "Entran los registros", "tipo": "entra",
              "texto": f"Los archivos anuales del evento 850 se unen en una sola base: {D.miles(M['n_crudo'])} "
                       f"notificaciones con {n_col} columnas cada una.",
              "antes": M["n_crudo"], "valor_filas": M["n_crudo"], "valor": M["n_crudo"], "unidad": "registros",
              "delta": None, "delta_texto": f"{n_col} columnas por registro"},
             {"nombre": "Periodo", "titulo": f"Solo {M['anio_inicio']}–{M['anio_max']}", "tipo": "filtra",
              "texto": f"El estrato y la pertenencia étnica solo existen desde la ficha de {M['anio_inicio']}: "
                       "los años anteriores quedan fuera del estudio.",
              "antes": flujo[0]["Registros"], "valor_filas": flujo[1]["Registros"], "valor": flujo[1]["Registros"],
              "unidad": "registros", "delta": -flujo[1]["Excluidos"], "delta_texto": menos(flujo[1]["Excluidos"])}]
    for f, previo in zip(flujo[2:], flujo[1:]):
        clave = next((p for p in PASOS_LIMPIEZA if p[0] in f["Paso"].lower()), None)
        nombre, titulo, texto = clave[1:] if clave else (f["Paso"], f["Paso"], f["Paso"])
        pasos.append({"nombre": nombre, "titulo": titulo, "texto": texto, "tipo": "filtra",
                      "antes": previo["Registros"], "valor_filas": f["Registros"], "valor": f["Registros"],
                      "unidad": "registros", "delta": -f["Excluidos"], "delta_texto": menos(f["Excluidos"])})
    pasos[-1]["unidad"] = "casos útiles"
    pasos.append({"nombre": "Variables", "titulo": "De columnas a variables", "tipo": "columnas",
                  "texto": f"Se construyen {n_var} variables: {len(C['columnas_numericas'])} numéricas (edad, año, estrato, "
                           f"días con síntomas), {len(C['columnas_binarias'])} grupos poblacionales y "
                           f"{len(C['categorias'])} categorías. El resto de columnas no entra al modelo.",
                  "antes": n_col, "valor": n_var, "unidad": "variables", "delta": n_var - n_col,
                  "delta_texto": f"−{n_col - n_var} columnas",
                  "indices_quedan": [round(k * (n_col - 1) / (n_var - 1)) for k in range(n_var)]})
    pasos.append({"nombre": "Partición", "titulo": "Desarrollo y prueba", "tipo": "particion",
                  "texto": f"Una partición estratificada aparta el {D.pct(n_pru / M['n_util'], 0)} para la prueba, que se usa "
                           "una sola vez; el resto elige y ajusta el modelo con validación cruzada.",
                  "antes": M["n_util"], "valor_filas": M["n_util"], "valor": n_tv, "unidad": "casos para desarrollar",
                  "delta": None, "delta_texto": f"{D.miles(n_pru)} apartados para la prueba",
                  "prop_prueba": n_pru / M["n_util"], "etq_a": f"desarrollo · {D.pct(n_tv / M['n_util'], 0)}",
                  "etq_b": f"prueba · {D.pct(n_pru / M['n_util'], 0)}"})
    for p, color in zip(pasos, F.CATEG):
        p["color"] = color
    return {"total": M["n_crudo"], "pasos": pasos,
            "nota_punto": f"Cada punto representa unos {D.miles(M['n_crudo'] / 200)} registros."}


# ----------------------------------------------------------------------------------------------------------------------
# Pestañas
# ----------------------------------------------------------------------------------------------------------------------
def tab_resumen(T):
    mp, u = D.MP, D.UMBRAL
    n_util = D.miles(T["meta"]["n_util"]) if T else "—"
    hijos = [
        seccion("¿Quién llegó hospitalizado al diagnóstico?",
                "Con lo que trae la ficha de notificación, el modelo estima qué tan probable es que la persona haya "
                "llegado hospitalizada. La hospitalización al notificar es una señal de diagnóstico tardío: la "
                "secretaría de salud usa esa probabilidad para decidir a quién contactar el mismo día."),
        html.Div(className="kpis ola", children=[
            kpi("Casos analizados", n_util, f"notificaciones de VIH, {D.ANIO_INICIO}–{D.anio_fin()}", "var(--azul)"),
            kpi("Hospitalizados al notificar", D.pct(D.PREV), "prevalencia en el entrenamiento", "var(--prioritaria)"),
            kpi("AUC en prueba", D.num(mp["AUC"]), f"en {D.miles(mp['casos'])} casos nunca vistos", "var(--turquesa)"),
            kpi("Sensibilidad en prueba", D.pct(mp["sensibilidad"]), "hospitalizados que la regla marca", "var(--turquesa)"),
            kpi("Umbral de decisión", D.num(u, 2), "elegido por costo, no por exactitud", "var(--marino)"),
        ]),
        html.Div(className="rejilla iguales", children=[
            panel("Qué logra la regla en la prueba", "Con el umbral elegido por costo",
                  "Las cuatro cifras con que se juzga la regla: a cuántos hospitalizados encuentra, a cuántos sanos "
                  "deja tranquilos, cuántos de los marcados aciertan y qué parte de las notificaciones genera contacto. "
                  "Cambie entre la prueba y la validación cruzada, o compárelas.",
                  tarjeta_regla(T)),
            panel("Por qué el umbral es bajo", "Equivocarse hacia un lado cuesta más que hacia el otro", None,
                  html.Ul([
                      html.Li(["No encontrar a un hospitalizado (falso negativo) se valoró en ",
                               html.B(f"{D.miles(T['meta']['c_fn'] if T else 1_500_000)} pesos"), "."]),
                      html.Li(["Contactar a alguien sin necesidad (falso positivo), en ",
                               html.B(f"{D.miles(T['meta']['c_fp'] if T else 300_000)} pesos"), "."]),
                      html.Li([f"Con esos costos el umbral teórico es "
                               f"{D.num(T['umbral']['p_star']) if T else '0.167'}; el que minimiza el costo en los datos es ",
                               html.B(D.num(u, 2)), "."]),
                      html.Li(["Por eso se prefiere marcar de más: sensibilidad ", html.B(D.pct(mp["sensibilidad"])),
                               ", especificidad ", html.B(D.pct(mp["especificidad"])), "."]),
                  ], className="texto"),
                  html.P(className="nota", children="La pestaña «Umbral y prueba» deja mover el umbral y ver el costo.")),
        ]),
    ]
    if T:
        hijos.append(panel("De la base unida a los casos útiles", "Cómo entran los datos y qué se queda en cada paso",
                           "Los registros entran como puntos y en cada filtro se quedan o salen hacia «fuera»; después las "
                           "columnas se vuelven variables y los casos se reparten entre desarrollo y prueba. Avanza solo; "
                           "señale un paso para verlo o tóquelo para fijarlo.",
                           html.Div(className="recorrido", **{"data-recorrido": json.dumps(recorrido_datos(T),
                                                                                          ensure_ascii=False)})))
    return hijos


FACTORES = [("edad", "Edad"), ("dias", "Días con síntomas"), ("regimen", "Régimen"), ("region", "Región"),
            ("sexo", "Sexo"), ("area", "Área"), ("etnia", "Etnia"), ("grupos", "Grupo poblacional")]


def tab_datos(T):
    if not T:
        return [falta_tablero()]
    m = T["meta"]
    return [
        seccion("Los datos de vigilancia",
                f"Microdatos del evento 850 del SIVIGILA ({m['fuente']}), descargados el {m['fecha_descarga']}. "
                f"El estudio usa {D.miles(m['n_util'])} notificaciones útiles de {m['anio_inicio']} a {m['anio_max']}."),
        html.Div(className="kpis ola", children=[
            kpi("Registros en la base unida", D.miles(m["n_crudo"]), "todos los años del evento 850"),
            kpi(f"Notificados {m['anio_inicio']}–{m['anio_max']}", D.miles(m["n_periodo"]), "periodo con estrato y etnia"),
            kpi("Edad media al notificarse", f"{m['edad_media']:.1f} años", f"mediana {m['edad_mediana']:.0f} años",
                "var(--turquesa)"),
            kpi("Hospitalizados", D.pct(m["prev_total"]), "de los casos útiles", "var(--prioritaria)"),
        ]),
        html.Div(className="rejilla dos", children=[
            panel("Hospitalización al notificar, año por año", "Proporción de casos que ya estaban hospitalizados",
                  "Cómo cambió con los años la proporción de personas que llegaron hospitalizadas al diagnóstico. "
                  "Pase el cursor por una barra para ver cuántos casos se notificaron ese año.",
                  grafica(F.anual(T["descriptivo"]["por_anio"], m["prev_total"]))),
            panel("A qué edad se notifica", "Casos por grupos de diez años",
                  "La distribución de la edad al notificarse, que es el objetivo numérico del artículo. La línea "
                  "punteada marca la edad media.",
                  grafica(F.hist_edad(T["descriptivo"]["hist_edad"], m["edad_media"]))),
        ]),
        panel("Explorador de factores", "Elija una característica de la ficha y compare la hospitalización entre sus niveles",
              "Qué niveles de una característica se alejan del promedio. Barras por encima de la línea: grupos que "
              "llegan hospitalizados con más frecuencia. Es una asociación, no una causa.",
              html.Div(pastillas("sel-factor", FACTORES, "dias"), className="controles-fila"),
              grafica(id="fig-factor", alto=340)),
        html.Div(className="rejilla", children=[
            panel("Departamentos de residencia", "Los 15 primeros; el color indica el porcentaje de hospitalizados",
                  "Dónde viven las personas notificadas. La longitud es el número de casos y el color, qué proporción "
                  "llegó hospitalizada. Solo se muestran departamentos con al menos 200 casos.",
                  html.Div(pastillas("sel-deptos", [("casos", "Por número de casos"), ("prop", "Por % hospitalizados")],
                                     "casos"), className="controles-fila"),
                  grafica(id="fig-deptos", alto=470)),
        ]),
    ]


def tab_modelos(T):
    hijos = [
        seccion("Siete clasificadores, las mismas reglas",
                "Todos se midieron en los mismos cinco pliegues de la validación cruzada anidada, así que la comparación "
                "es pareada: pliegue contra pliegue."),
        html.Div(id="kpis-pliegues", className="kpis"),
        panel("Resultado de cada modelo en cada pliegue", "El rombo es la media; los puntos, cada pliegue",
              "Cada punto es el resultado de un modelo en un pliegue y el rombo, su media. Más a la derecha es mejor; "
              "si los puntos de dos modelos se mezclan, la diferencia puede ser ruido. Clic en la leyenda para ocultar.",
              html.Div(pastillas("sel-metrica", [("AUC", "AUC (qué tan bien ordena)"),
                                                 ("AP", "Precisión media (curva precisión-sensibilidad)")], "AUC"),
                       className="controles-fila"),
              grafica(id="fig-pliegues", alto=400)),
    ]
    if not T:
        return hijos + [falta_tablero()]
    cv = T["cv"]
    filas = sorted(cv["resumen"], key=lambda r: -r["auc_media"])
    hijos += [
        html.Div(className="rejilla dos", children=[
            panel("Curvas con los puntajes fuera de pliegue", "Todos los umbrales a la vez",
                  "La curva ROC muestra cuántos hospitalizados se detectan a cambio de cuántos sanos se marcan, para "
                  "cualquier umbral; la de precisión y sensibilidad, cuántos de los marcados aciertan. Entre más arriba, mejor.",
                  html.Div(pastillas("sel-curva", [("roc", "ROC"), ("pr", "Precisión y sensibilidad")], "roc"),
                           className="controles-fila"),
                  grafica(id="fig-curvas", alto=400)),
            html.Div(className="vidrio panel revelar", children=[
                html.Div(className="panel-cabecera", children=html.Div([html.H3("Comprobaciones del modelo definitivo"),
                                                                        html.P("Dos pruebas de que el resultado no depende de un atajo")])),
                html.Div(className="kpis", style={"gridTemplateColumns": "1fr"}, children=[
                    kpi(f"Entrenado hasta {cv['anio_corte']}, evaluado después", D.num(cv["auc_temporal"]),
                        f"AUC en {D.miles(cv['n_temp_eva'])} casos posteriores; cae {D.num(cv['caida_temporal'])} "
                        f"frente a la validación cruzada", "var(--turquesa)"),
                    kpi("Sin los días con síntomas", D.num(cv["sin_dias"][1]["sin_media"]),
                        f"AUC de {cv['definitivo']} sin esa variable (con ella: {D.num(cv['sin_dias'][1]['con_media'])})",
                        "var(--prioritaria)"),
                    kpi("Ventaja sobre la logística", f"+{D.num(cv['sin_dias'][2]['con_media'], 4)}",
                        f"diferencia pareada de AUC (sin la variable: +{D.num(cv['sin_dias'][2]['sin_media'], 4)})",
                        "var(--azul)"),
                ])]),
        ]),
        panel("Tabla de la validación cruzada", "Hiperparámetros elegidos y métricas medias de los pliegues externos", None,
              tabla(["Modelo", "Hiperparámetros", "best_score_", "AUC anidado", "D. E.", "AP", "Optimismo"],
                    [[r["Modelo"], r["hiper"], D.num(r["best_score"], 4), D.num(r["auc_media"], 4), D.num(r["auc_sd"], 4),
                      D.num(r["ap_media"]), D.num(r["optimismo"], 4)] for r in filas],
                    destacar=lambda i: filas[i]["Modelo"] == cv["definitivo"])),
        panel("Objetivo numérico: la edad al diagnóstico", "Regresión lineal, Ridge y Lasso en los mismos pliegues", None,
              tabla(["Modelo", "Alpha elegido", "MAE (años)", "RECM (años)", "D. E. RECM", "R²"],
                    [[r["modelo"], "no aplica" if r["alpha"] is None else str(r["alpha"]), D.num(r["mae"]),
                      D.num(r["recm"]), D.num(r["recm_sd"]), D.num(r["r2"], 4)] for r in T["edad_regresion"]["modelos"]]),
              html.P(className="nota", children="La edad se explica poco con estas variables; Ridge y Lasso no mejoran la "
                                                 "regresión lineal.")),
    ]
    return hijos


def tab_umbral(T):
    if not T:
        return [falta_tablero()]
    U, P = T["umbral"], T["prueba"]
    m = P["metricas"]
    return [
        seccion("El umbral se elige por costo",
                "Mueva el umbral y vea qué pasa con el costo, con los hospitalizados que se detectan y con los contactos "
                "que no hacían falta. Las cifras salen de las probabilidades fuera de pliegue del modelo definitivo."),
        html.Div(className="vidrio panel revelar", children=[
            html.Div(className="panel-cabecera", children=[
                html.Div([html.H3("Su umbral"), html.P("Arrastre el control; el modelo guardado usa el elegido por costo")]),
                ayuda("Su umbral", "Por encima del umbral la ficha pasa a ruta prioritaria. Bajarlo detecta más "
                                   "hospitalizados a cambio de más contactos innecesarios; las tarjetas se recalculan.")]),
            html.Div(className="control-umbral", children=dcc.Slider(
                id="sel-umbral", min=0.01, max=0.99, step=0.01, value=round(U["u_def"], 2),
                marks={0.05: "0.05", round(U["u_def"], 2): f"elegido {U['u_def']:.2f}", 0.5: "0.50", 0.95: "0.95"},
                tooltip={"placement": "top", "always_visible": True})),
            html.Div(id="kpis-umbral", className="kpis", style={"marginTop": "14px", "marginBottom": "4px"}),
        ]),
        html.Div(className="rejilla dos", children=[
            panel("Costo esperado según el umbral", "Falsos negativos y falsos positivos valorados en pesos",
                  "Cuánto cuesta en total equivocarse con cada umbral. El mínimo de la curva es el umbral que quedó "
                  "guardado; el punto blanco es el que usted eligió arriba.",
                  dcc.Graph(id="fig-costo", className="grafica", style={"height": "360px"},
                            config={"displaylogo": False, "responsive": True,
                                    "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"]})),
            panel("¿Se puede creer la probabilidad?", "Calibración por deciles",
                  "Si el modelo dice 30 %, ¿llegan hospitalizados 3 de cada 10? Los puntos sobre la diagonal indican "
                  f"probabilidades bien calibradas. Brier {U['brier']:.3f} frente a {U['brier_base']:.3f} de adivinar "
                  "siempre la prevalencia.",
                  grafica(F.calibracion(U["calibracion"]["pred"], U["calibracion"]["obs"]))),
        ]),
        html.Div(className="rejilla dos-inv", children=[
            panel("La prueba final, caso por caso", f"{D.miles(P['VP'] + P['FN'] + P['FP'] + P['VN'])} casos usados una sola vez",
                  "Qué pasó con cada persona del conjunto de prueba al aplicar el umbral elegido: arriba, los que sí "
                  "llegaron hospitalizados; a la izquierda, los que la regla envió a ruta prioritaria.",
                  grafica(F.confusion(P["VP"], P["FN"], P["FP"], P["VN"]))),
            panel("Si los costos fueran otros", "Umbral que minimiza el costo con otras razones entre los dos errores", None,
                  tabla(["Razón de costos", "Umbral teórico", "Umbral empírico", "Sensibilidad", "Precisión", "Casos marcados"],
                        [[f"{r['razon']} a 1", D.num(r["p_star"]), D.num(r["u"], 2), D.num(r["sens"]), D.num(r["prec"]),
                          D.pct(r["alerta"])] for r in U["sens_costos"]],
                        destacar=lambda i: abs(U["sens_costos"][i]["razon"] - T["meta"]["c_fn"] / T["meta"]["c_fp"]) < 1e-9),
                  html.P(className="nota", children=[
                      "Con el umbral elegido, el costo por cada 1 000 casos notificados es de ",
                      html.B(f"{D.miles(P['costo_1000'])} pesos"), f" y se marca el {D.pct(P['alerta'])} de los casos; "
                      f"uno de cada {P['uno_de_cada']:.1f} marcados estaba hospitalizado. La sensibilidad de prueba es "
                      f"{D.num(m['Sensibilidad'])}."])),
        ]),
    ]


def campo(rotulo, control, ancho="c2"):
    return html.Div(className=f"campo {ancho}", children=[html.Label(rotulo), control])


def selector(id, opciones, etiquetas=None):
    return dcc.Dropdown(id=id, options=[{"label": (etiquetas or {}).get(o, str(o)), "value": o} for o in opciones],
                        clearable=False, searchable=False, className="selector")


def tab_ficha():
    cats = D.CATS
    return [
        seccion("Clasificar una ficha",
                "Elija una ficha de prueba o cambie los datos: el resultado se recalcula al instante con el modelo "
                "guardado. Las fichas son inventadas."),
        html.Div(className="rejilla dos-inv", children=[
            panel("Ficha de notificación", "Los mismos campos que llegan al SIVIGILA", None,
                  html.Div(className="formulario", children=[
                      campo("Cargar una ficha de prueba (sintética)",
                            dcc.Dropdown(id="f-ficha", options=[{"label": f"{f['id']} · {f['titulo']}", "value": f["id"]}
                                                                for f in D.FICHAS],
                                         value=D.FICHAS[0]["id"], clearable=False, className="selector"), "c6"),
                      campo("Edad (años)", dcc.Input(id="f-edad", type="number", min=0, max=100, step=1, debounce=True)),
                      campo("Sexo", dcc.RadioItems(id="f-sexo", options=[{"label": D.ETIQ_SEXO[s], "value": s}
                                                                         for s in cats["sexo"]],
                                                   className="pastillas", inline=True)),
                      campo("Estrato", selector("f-estrato", [1, 2, 3, 4, 5, 6, "Sin dato"])),
                      campo("Régimen de salud", selector("f-regimen", cats["regimen"]), "c3"),
                      campo("Área de residencia", selector("f-area", cats["area"]), "c3"),
                      campo("Región", selector("f-region", cats["region"]), "c3"),
                      campo("Pertenencia étnica", selector("f-etnia", cats["etnia"]), "c3"),
                      campo("Fecha de notificación", dcc.Input(id="f-fecha-not", type="date",
                                                               min=f"{D.ANIO_INICIO}-01-01", debounce=True), "c3"),
                      campo("Inicio de síntomas", dcc.Input(id="f-fecha-sin", type="date", debounce=True), "c3"),
                      html.Div(className="campo c6 chequeo", children=dcc.Checklist(
                          id="f-sin-fecha", options=[{"label": "La ficha no trae fecha de inicio de síntomas",
                                                      "value": "si"}])),
                      campo("Grupo poblacional", dcc.Checklist(
                          id="f-grupos", options=[{"label": D.ETIQ_GRUPOS[g], "value": g}
                                                  for g in D.CONTRATO["columnas_binarias"]],
                          className="pastillas", inline=True), "c6"),
                  ])),
            panel("Resultado", "Probabilidad estimada y decisión con el umbral guardado",
                  "Qué tan probable es, según casos parecidos del SIVIGILA, que esta persona haya llegado hospitalizada, "
                  "y si eso alcanza el umbral para la ruta prioritaria. No es un diagnóstico.",
                  html.Div(id="resultado-ficha")),
        ]),
        panel("Clasificar todas las fichas de prueba", "Las ocho fichas sintéticas, ordenadas por probabilidad",
              "Cómo ordena el modelo las fichas de prueba de mayor a menor probabilidad. Las que cruzan la línea "
              "del umbral pasan a ruta prioritaria.",
              html.Div(className="controles-fila", children=html.Button("Clasificar el lote", id="btn-lote", className="boton")),
              html.Div(id="salida-lote")),
    ]


DIMENSIONES = ["Sexo", "Edad (años)", "Régimen", "Región", "Pertenencia étnica", "Migrante"]


def filas_subgrupo(T, dim):
    """Desempeño por subgrupo en la prueba: el .qmd lo calcula por sexo, edad, régimen y región, y por atributo
    protegido (que añade pertenencia étnica y migrante)."""
    filas = [f for f in T["subgrupos"] if f["dim"] == dim]
    if not filas:
        filas = [f for f in T["equidad"]["tabla"] if f["atributo"] == dim]
    # los grupos de edad («0 a 24», «25 a 34», …, «45 o más») se ordenan de menor a mayor
    return sorted(filas, key=lambda f: f["nivel"]) if dim.startswith("Edad") else filas


def tab_variables(T):
    if not T:
        return [falta_tablero()]
    E = T["equidad"]
    return [
        seccion("Qué pesa y para quién funciona",
                "Qué variables usa el modelo para decidir y si la regla trata igual a los distintos grupos de la población."),
        html.Div(className="rejilla iguales", children=[
            panel("Qué variables usa el modelo", "Importancia por permutación del modelo definitivo",
                  "Cuánto empeora el modelo (caída del AUC) si se desordena una variable. Entre más larga la barra, más "
                  "depende la predicción de ella. La línea fina es la variación entre repeticiones.",
                  grafica(F.importancia(T["importancia"]))),
            panel("¿Funciona igual para todos?", "Desempeño en la prueba por subgrupo, con el umbral elegido",
                  "Para cada grupo: qué parte de sus hospitalizados se detecta (sensibilidad), qué parte de los no "
                  "hospitalizados se descarta bien (especificidad) y a qué proporción se marca.",
                  html.Div(pastillas("sel-subgrupo", [(d, d) for d in DIMENSIONES], "Edad (años)"),
                           className="controles-fila"),
                  grafica(id="fig-subgrupos", alto=370)),
        ]),
        html.Div(className="rejilla iguales", children=[
            panel("¿Se puede adivinar el atributo protegido?", "Logística que intenta reconstruirlo con las demás columnas",
                  "Si el resto de la ficha permite adivinar el sexo, la etnia, el régimen o la condición de migrante, "
                  "quitar ese atributo del modelo no lo vuelve ciego a él. Un AUC cercano a 0.5 es azar.",
                  grafica(F.proxy(E["proxy"], E["auc_proxy_alto"]))),
            panel("¿Y si se quita el sexo del modelo?", "Mismos hiperparámetros y pliegues, con y sin la variable",
                  "Compara la versión con el sexo y la versión sin él: qué parte de los hospitalizados se detecta y qué "
                  "parte de los sanos se marca en mujeres y en hombres. Si las barras casi no cambian, la brecha no "
                  "viene de la variable.",
                  grafica(F.sin_atributo(E["sin_atributo"]))),
        ]),
    ]


def tab_monitoreo(T):
    if not T:
        return [falta_tablero()]
    M, NS, S = T["monitoreo"], T["no_supervisado"], T["serie"]
    g = {str(f["grupo"]): f for f in NS["perfil"]}
    return [
        seccion("Monitoreo y más allá del clasificador",
                "Si la población cambia con los años, el modelo envejece. Además: perfiles sin etiqueta y un pronóstico "
                "de la serie semanal de notificaciones."),
        html.Div(className="rejilla dos-inv", children=[
            panel("¿Cambió la población?", "Índice de estabilidad poblacional (PSI) por variable y año",
                  "Compara la distribución de cada variable en cada año con la de los años de referencia. Por debajo de "
                  f"{M['bandas'][0]} es estable; entre {M['bandas'][0]} y {M['bandas'][1]}, vigilar; por encima, actuar.",
                  grafica(F.psi(M["psi"], M["anios_psi"], M["bandas"]))),
            panel("¿Envejece el modelo?", "Desempeño por año con las probabilidades fuera de pliegue",
                  "Año por año: si el modelo sigue ordenando bien (AUC) y detectando (sensibilidad), o si su probabilidad "
                  "media se separa de la proporción real de hospitalizados. Detecta derivas que el PSI no ve.",
                  html.Div(pastillas("sel-anio", [("disc", "Discriminación"), ("cal", "Calibración")], "disc"),
                           className="controles-fila"),
                  grafica(id="fig-anio", alto=340)),
        ]),
        html.Div(className="rejilla iguales", children=[
            panel("Perfiles que aparecen sin etiqueta", f"K-means con {NS['k']} grupos sobre el mapa del análisis de componentes",
                  "Cada punto es un caso proyectado en los dos primeros componentes principales y coloreado por su grupo de "
                  "K-means. Los grupos se buscaron sin mirar la hospitalización.",
                  grafica(F.acp(NS["acp"], NS["nombres"]))),
            panel("Qué distingue a los grupos", "Proporciones en unidades originales",
                  "En qué se diferencian los grupos de K-means. *La hospitalización es solo descriptiva: no se usó para "
                  "formarlos. " + " · ".join(f"Grupo {k}: edad media {v['edad_media']:.1f} años, mediana de "
                                             f"{v['dias_mediana']:.0f} días con síntomas" for k, v in g.items()) + ".",
                  grafica(F.perfil(NS["perfil"], NS["nombres"]))),
        ]),
        panel("Pronóstico de la serie semanal de notificaciones", "LSTM frente al mejor pronóstico ingenuo",
              "Casos notificados por semana. En la zona sombreada, los años de evaluación: la red LSTM y el mejor "
              f"pronóstico ingenuo intentan anticipar la semana siguiente (Diebold-Mariano p = {S['dm_p']:.3f}). "
              "Use la barra inferior para acercarse.",
              grafica(F.serie(S))),
    ]


def tab_limites(T):
    mp, C = D.MP, D.CONTRATO
    limite_grupos = "La sensibilidad es menor en los más jóvenes y en el régimen contributivo."
    if T:
        peor = min(T["subgrupos"], key=lambda f: f["sens"])
        mejor = max(T["subgrupos"], key=lambda f: f["sens"])
        limite_grupos = (f"La sensibilidad más baja está en {peor['nivel']} ({peor['dim'].lower()}, {D.num(peor['sens'])}) "
                         f"y la más alta en {mejor['nivel']} ({mejor['dim'].lower()}, {D.num(mejor['sens'])}).")
    filas_prueba = [["AUC", D.num(mp["AUC"]), ""], ["Sensibilidad", D.pct(mp["sensibilidad"]), ""],
                    ["Especificidad", D.pct(mp["especificidad"]), ""], ["Precisión", D.pct(mp["precision"]), ""],
                    ["Casos de prueba", D.miles(mp["casos"]), ""]]
    if T:
        ic = T["prueba"]["ic"]
        filas_prueba[0][2] = f"{D.num(ic['AUC'][0])} a {D.num(ic['AUC'][1])}"
        filas_prueba[1][2] = f"{D.pct(ic['Sens'][0])} a {D.pct(ic['Sens'][1])}"
        filas_prueba[2][2] = f"{D.pct(ic['Esp'][0])} a {D.pct(ic['Esp'][1])}"
    contrato = {k: v for k, v in C.items() if k != "pipeline"}
    return [
        seccion("Límites y despliegue", "Lo que el modelo no hace, cómo viaja una ficha y qué se publica."),
        html.Div(className="rejilla iguales", children=[
            html.Div(children=[
                panel("Límites declarados", None, None, html.Ul(className="texto", children=[
                    html.Li([html.B("Depende de la fecha de síntomas. "), "Es la variable que más pesa, y su ausencia se "
                             "concentra en ciertas instituciones: en parte el modelo aprende quién notifica."]),
                    html.Li([html.B("No trata igual a todos los grupos. "), limite_grupos]),
                    html.Li([html.B("Caduca. "), f"Se entrenó con {D.ANIO_INICIO}–{D.anio_fin()} y debe revisarse al "
                             f"cerrar {C['revisar_al_cerrar_anio']}."]),
                    html.Li([html.B("Marca de más a propósito. "), f"Con el umbral {D.num(D.UMBRAL, 2)} la precisión es "
                             f"{D.pct(mp['precision'])}: la mayoría de los marcados no estaba hospitalizada."]),
                    html.Li([html.B("Asociación no es causa. "), "Ninguna variable prueba por qué alguien llega hospitalizado."]),
                ])),
                html.Div(style={"height": "18px"}),
                panel("Desempeño en la prueba", "Leído del contrato guardado; la prueba se usó una sola vez", None,
                      tabla(["Métrica", "Valor", "IC 95 %"], filas_prueba)),
            ]),
            html.Div(children=[
                panel("Cómo viaja una ficha", None, None, html.Ol(className="pasos", children=[
                    html.Li(["El formulario se convierte a las ", html.B(f"{len(C['columnas'])} columnas"), " del contrato."]),
                    html.Li(["El tablero llama a ", html.Code("predecir()"), " de ", html.Code("cargar_y_predecir.py"), "."]),
                    html.Li(["El ", html.Code("Pipeline"), " guardado imputa los faltantes, codifica y calcula la probabilidad."]),
                    html.Li(["Se compara con el umbral ", html.B(D.num(D.UMBRAL, 2)), " y se devuelve la decisión."]),
                ])),
                html.Div(style={"height": "18px"}),
                panel("Qué se despliega", None, None,
                      html.Ul(className="texto", children=[
                          html.Li([html.B("Una sola aplicación: "), "este tablero, con el archivo del modelo, ",
                                   html.Code("cargar_y_predecir.py"), " y las cifras que exporta el artículo."]),
                          html.Li([html.B("Sin reentrenar: "), "el modelo se carga ya entrenado desde el ", html.Code(".joblib"), "."]),
                      ]),
                      html.Details(className="detalle", children=[
                          html.Summary("Contrato del modelo"),
                          html.Pre(json.dumps(contrato, ensure_ascii=False, indent=2, default=str), className="json")])),
                html.Div(style={"height": "18px"}),
                panel("Código del proyecto", "Escanee el código o abra el enlace", None,
                      html.Div(className="qr-proyecto", children=[
                          html.A(href=REPOSITORIO, target="_blank", rel="noopener", className="qr-marco", children=html.Img(
                              src=app.get_asset_url("qr_github.jpeg"), alt="Código QR del repositorio del proyecto en GitHub")),
                          html.Div(className="qr-texto", children=[
                              html.P("El artículo en Quarto, los datos del SIVIGILA, el modelo guardado y este tablero "
                                     "están en un solo repositorio.", className="texto"),
                              html.A(REPOSITORIO.replace("https://", ""), href=REPOSITORIO, target="_blank",
                                     rel="noopener", className="qr-enlace"),
                          ]),
                      ])),
                html.Div(style={"height": "18px"}),
                panel("Equipo", "Machine Learning 2026-II · Universidad Tecnológica de Bolívar", None,
                      html.Div(className="equipo ola", children=[html.Span(n, className="revelar") for n in D.AUTORES])),
            ]),
        ]),
    ]


PESTANAS = [("resumen", "1 · Resumen"), ("datos", "2 · Los datos"), ("modelos", "3 · Modelos"),
            ("umbral", "4 · Umbral y prueba"), ("ficha", "5 · Clasificar una ficha"),
            ("variables", "6 · Variables y equidad"), ("monitoreo", "7 · Monitoreo"), ("limites", "8 · Límites y despliegue")]


def construir():
    """Se arma en cada carga de la página: si el artículo se vuelve a generar, basta con recargar."""
    T = D.tablero()
    C, mp = D.CONTRATO, D.MP
    avisos = [html.Div(className="vidrio aviso revelar", children=[
        html.Span("i", className="aviso-icono"),
        html.Div([html.B("Demostración académica. "), "Las fichas que se clasifican aquí son inventadas. El sistema no "
                  "decide hospitalizar ni reemplaza el criterio clínico: ordena a quién contactar primero."])])]
    if T and T["meta"]["muestra_desarrollo"] is not None:
        avisos.append(html.Div(className="vidrio aviso ensayo revelar", children=[
            html.Span("!", className="aviso-icono"),
            html.Div([html.B("Cifras de ensayo. "), f"resultados/tablero.json se generó con MUESTRA_DESARROLLO = "
                      f"{T['meta']['muestra_desarrollo']}: no son las cifras del artículo. Vuelva a generar el artículo "
                      "con None antes de presentar."])]))
    elif not T:
        avisos.append(falta_tablero())
    contenido = {"resumen": tab_resumen(T), "datos": tab_datos(T), "modelos": tab_modelos(T), "umbral": tab_umbral(T),
                 "ficha": tab_ficha(), "variables": tab_variables(T), "monitoreo": tab_monitoreo(T),
                 "limites": tab_limites(T)}
    return html.Div(className="fondo", children=[
        html.Div(className="mancha m1"), html.Div(className="mancha m2"), html.Div(className="mancha m3"),
        html.Div(className="contenedor", children=[
            html.Header(className="vidrio hero", children=[
                bandas_portada(),
                html.Div(className="hero-texto", children=[
                    html.Div("Entrega final · Machine Learning 2026-II · SIVIGILA · Colombia", className="sobretitulo revelar"),
                    html.H1("Predicción de la hospitalización en la notificación de VIH con datos de vigilancia",
                            **{"data-letras": "1"}),
                    html.P(f"Con datos de vigilancia del SIVIGILA, {D.ANIO_INICIO}–{D.anio_fin()}: a quién contacta "
                           "primero la secretaría de salud.", className="sub revelar"),
                    html.Div(className="autores revelar", children=[html.Span(n) for n in D.AUTORES]),
                ]),
                html.Div(className="vidrio sello revelar", children=[
                    html.Span("Modelo cargado", className="rot"),
                    html.Strong(f"{C['modelo']} · v{C['version_modelo']}"),
                    html.Span(f"Umbral {D.num(D.UMBRAL, 2)} · AUC {D.num(mp['AUC'])}"),
                    html.Span(f"Entrenado el {C['entrenado_el']}"),
                ]),
            ]),
            *avisos,
            dcc.Tabs(id="pestanas", value="resumen", className="pestanas", parent_className="pestanas-padre",
                     children=[dcc.Tab(label=e, value=v, className="tab", selected_className="tab--selected",
                                       children=html.Div(contenido[v])) for v, e in PESTANAS]),
            html.Footer(className="pie", children=[
                html.P(f"Fuente de los datos: SIVIGILA, Instituto Nacional de Salud, evento 850 · Modelo {C['modelo']} "
                       f"v{C['version_modelo']} · Demostración académica"),
                html.P(f"Cifras exportadas por el artículo el {T['meta']['generado_el'].replace('T', ' ')}" if T else ""),
            ]),
        ]),
    ])


app.layout = construir


# ----------------------------------------------------------------------------------------------------------------------
# Interacción
# ----------------------------------------------------------------------------------------------------------------------
@app.callback(Output("fig-factor", "children"), Input("sel-factor", "value"))
def cb_factor(clave):
    T = D.tablero()
    filas = T["descriptivo"][clave]
    if clave == "grupos":
        filas = [{**f, "nivel": D.ETIQ_GRUPOS.get(f["nivel"], f["nivel"])} for f in filas if f["prop"] is not None]
    return sg(F.factor(filas, dict(FACTORES)[clave].lower(), T["meta"]["prev_total"]))


@app.callback(Output("fig-deptos", "children"), Input("sel-deptos", "value"))
def cb_deptos(orden):
    return sg(F.departamentos(D.tablero()["descriptivo"]["departamento"], orden))


@app.callback(Output("fig-pliegues", "children"), Output("kpis-pliegues", "children"), Input("sel-metrica", "value"))
def cb_pliegues(metrica):
    cv = D.CV[D.CV.metrica == metrica]
    res = cv.groupby("modelo").valor.agg(["mean", "std"]).sort_values("mean", ascending=False)
    a, b = res.index[0], res.index[1]
    ancho = cv.pivot(index="pliegue", columns="modelo", values="valor")
    dif = ancho[a] - ancho[b]
    tarjetas = [
        kpi("Mejor modelo", a, f"{metrica} medio {res['mean'][a]:.4f} (D. E. {res['std'][a]:.4f})", "var(--turquesa)", False),
        kpi("Segundo", b, f"{metrica} medio {res['mean'][b]:.4f} (D. E. {res['std'][b]:.4f})", "var(--azul)", False),
        kpi("Diferencia pareada", f"{dif.mean():+.4f}", f"{a} gana en {(dif > 0).sum()} de {len(dif)} pliegues",
            "var(--prioritaria)", False),
    ]
    return sg(F.pliegues(D.CV[D.CV.metrica.isin(["AUC", "AP"])], metrica, D.CONTRATO["modelo"])), tarjetas


@app.callback(Output("fig-curvas", "children"), Input("sel-curva", "value"))
def cb_curvas(tipo):
    T = D.tablero()
    return sg(F.curvas(T["curvas"], tipo, T["cv"]["orden"], T["prev_tv"]))


@app.callback(Output("fig-costo", "figure"), Output("kpis-umbral", "children"), Input("sel-umbral", "value"))
def cb_umbral(u):
    T = D.tablero()
    U, meta = T["umbral"], T["meta"]
    r = min(U["malla"], key=lambda f: abs(f["u"] - u))
    n = meta["n_tv"]
    tarjetas = [
        kpi("Hospitalizados detectados", D.pct(r["sens"]), "sensibilidad", "var(--turquesa)", False, False),
        kpi("No hospitalizados bien descartados", D.pct(r["espec"]), "especificidad", "var(--azul)", False, False),
        kpi("Aciertos entre los marcados", D.pct(r["prec"]), "precisión", "var(--marino)", False, False),
        kpi("Casos que se marcan", D.pct(r["alerta"]), f"de {D.miles(n)} casos de entrenamiento y validación",
            "var(--prioritaria)", False, False),
        kpi("Costo por cada 1 000 casos", f"{r['costo'] / n * 1000 / 1e6:.1f} millones",
            f"{'+' if r['costo'] >= U['costo_def'] else ''}{100 * (r['costo'] / U['costo_def'] - 1):.1f} % frente al umbral elegido",
            "var(--prioritaria)", False, False),
    ]
    return F.costo(U["malla"], u, U["u_def"], U["p_star"]), tarjetas


@app.callback(Output("fig-subgrupos", "children"), Input("sel-subgrupo", "value"))
def cb_subgrupos(dim):
    return sg(F.subgrupos(filas_subgrupo(D.tablero(), dim)))


@app.callback(Output("fig-anio", "children"), Input("sel-anio", "value"))
def cb_anio(vista):
    return sg(F.por_anio_modelo(D.tablero()["monitoreo"]["por_anio"], vista))


@app.callback(Output("f-edad", "value"), Output("f-sexo", "value"), Output("f-estrato", "value"),
              Output("f-regimen", "value"), Output("f-area", "value"), Output("f-region", "value"),
              Output("f-etnia", "value"), Output("f-fecha-not", "value"), Output("f-fecha-sin", "value"),
              Output("f-sin-fecha", "value"), Output("f-grupos", "value"), Input("f-ficha", "value"))
def cb_cargar_ficha(ficha_id):
    d = D.POR_ID[ficha_id]["datos"]
    sin = d["fecha_sintomas"] is None
    return (d["edad"], d["sexo"], "Sin dato" if d["estrato"] is None else d["estrato"], d["regimen"], d["area"],
            d["region"], d["etnia"], d["fecha_notificacion"], d["fecha_notificacion"] if sin else d["fecha_sintomas"],
            ["si"] if sin else [], list(d["grupos"]))


@app.callback(Output("f-fecha-sin", "disabled"), Input("f-sin-fecha", "value"))
def cb_sin_fecha(sin):
    return bool(sin)


@app.callback(Output("resultado-ficha", "children"),
              Input("f-edad", "value"), Input("f-sexo", "value"), Input("f-estrato", "value"),
              Input("f-regimen", "value"), Input("f-area", "value"), Input("f-region", "value"),
              Input("f-etnia", "value"), Input("f-fecha-not", "value"), Input("f-fecha-sin", "value"),
              Input("f-sin-fecha", "value"), Input("f-grupos", "value"))
def cb_clasificar(edad, sexo, estrato, regimen, area, region, etnia, f_not, f_sin, sin_fecha, grupos):
    if edad is None or not f_not or None in (sexo, estrato, regimen, area, region, etnia):
        return html.P("Complete la edad y la fecha de notificación para ver el resultado.", className="nota")
    digitado = {"edad": edad, "sexo": sexo, "regimen": regimen, "area": area, "etnia": etnia, "region": region,
                "estrato": None if estrato == "Sin dato" else estrato, "fecha_notificacion": dt.date.fromisoformat(f_not),
                "fecha_sintomas": None if (sin_fecha or not f_sin) else dt.date.fromisoformat(f_sin),
                "grupos": grupos or []}
    fila, notas = D.fila_del_contrato(digitado)
    pred = D.clasificar(fila)[0]
    p, u, pri = pred["probabilidad"], D.UMBRAL, pred["ruta_prioritaria"]
    tono = F.PRIORITARIA if pri else F.TURQUESA
    return html.Div(className="resultado", children=[
        html.Div("Probabilidad estimada de haber llegado hospitalizado", className="rot"),
        html.Div(f"{100 * p:.1f} %", className="prob", style={"color": tono}),
        html.Div(className="barra", children=[
            html.Div(className="lleno", style={"width": f"{100 * p:.1f}%", "background": tono}),
            html.Div(className="umbral", style={"left": f"{100 * u:.1f}%"}, children=html.Span(f"umbral {u:.2f}"))]),
        html.Span(("▲ RUTA PRIORITARIA" if pri else "● TRÁMITE HABITUAL"), className="pastilla-decision",
                  style={"background": tono}),
        html.P("La probabilidad alcanza el umbral: contacto el mismo día y verificación con la institución que notifica."
               if pri else "La probabilidad queda por debajo del umbral: seguimiento por el trámite habitual.", className="nota"),
        *[html.Div(n, className="alerta-nota") for n in notas],
        html.P("Calculado por: cargar_y_predecir.py · predecir(). Es una estimación a partir de casos parecidos del "
               "SIVIGILA; no es un diagnóstico ni una afirmación sobre esta persona.", className="nota"),
        html.Details(className="detalle", children=[
            html.Summary("Lo que se envió al modelo y lo que respondió"),
            html.Pre(json.dumps({"fila": fila, "respuesta": pred}, ensure_ascii=False, indent=2), className="json")]),
    ])


@app.callback(Output("salida-lote", "children"), Input("btn-lote", "n_clicks"), prevent_initial_call=True)
def cb_lote(_):
    filas = [D.fila_del_contrato(f["datos"])[0] for f in D.FICHAS]
    pred = D.clasificar(filas)
    res = [{"id": f["id"], "titulo": f["titulo"], "dias": x["dias_sintomas"], "prob": q["probabilidad"],
            "prioritaria": q["ruta_prioritaria"]} for f, x, q in zip(D.FICHAS, filas, pred)]
    orden = sorted(res, key=lambda r: -r["prob"])
    n_pri = sum(r["prioritaria"] for r in res)
    return [
        html.Div(className="rejilla dos", style={"marginBottom": "4px"}, children=[
            grafica(F.lote(res, D.UMBRAL)),
            tabla(["Ficha", "Descripción", "Días con síntomas", "Probabilidad", "Decisión"],
                  [[r["id"], r["titulo"], "sin dato" if r["dias"] is None else str(r["dias"]),
                    html.Span([html.Span(className="barrita", style={"width": f"{60 * r['prob']:.0f}px"}),
                               f"{100 * r['prob']:.1f} %"]),
                    "Ruta prioritaria" if r["prioritaria"] else "Trámite habitual"] for r in orden],
                  destacar=lambda i: orden[i]["prioritaria"]),
        ]),
        html.P(f"{n_pri} de {len(res)} fichas pasan a ruta prioritaria con el umbral {D.UMBRAL:.2f}. "
               "Calculado por: cargar_y_predecir.py · predecir()", className="nota"),
    ]


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 8050)), debug=False)
