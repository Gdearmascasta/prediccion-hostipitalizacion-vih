"""Carga de lo que genera el artículo. El tablero no calcula métricas: las lee de estos archivos.

    modelo_hospitalizacion_vih.joblib   modelo y contrato (lo escribe el .qmd)
    resultados/cv_resultados.csv        AUC y AP por pliegue (lo escribe el .qmd)
    resultados/tablero.json             cifras de figuras y tablas del artículo (bloque exporta-tablero del .qmd)
    cargar_y_predecir.py                funciones cargar() y predecir()
"""
import datetime as dt
import json
import os
import sys
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
# Raíz del repositorio (donde están el .joblib y cargar_y_predecir.py). Se puede cambiar con CARPETA_ARTICULO.
CARPETA = Path(os.environ.get("CARPETA_ARTICULO", AQUI.parent)).resolve()
if not (CARPETA / "cargar_y_predecir.py").exists():
    raise SystemExit(f"No encuentro cargar_y_predecir.py en {CARPETA}. Ajuste la variable CARPETA_ARTICULO.")
sys.path.insert(0, str(CARPETA))
import cargar_y_predecir as cyp  # noqa: E402

ARCHIVO_TABLERO = CARPETA / "resultados" / "tablero.json"
DIAS_MAX = 3650                 # intervalos mayores se tratan como dato faltante, igual que en el artículo
AUTORES = ["Didier Agamez", "Angel Vega", "Germán de Armas", "Karla Barraza"]

ETIQ_GRUPOS = {
    "gestante": "Gestante", "migrante": "Migrante", "privado_libertad": "Privado de la libertad",
    "desplazado": "Desplazado", "discapacidad": "Con discapacidad", "habitante_calle": "Habitante de calle",
    "victima_violencia": "Víctima de violencia", "centro_psiquiatrico": "En centro psiquiátrico",
}
ETIQ_SEXO = {"F": "Mujer", "M": "Hombre"}

CONTRATO = cyp.cargar(str(CARPETA / cyp.ARCHIVO_MODELO))
CV = pd.read_csv(CARPETA / "resultados" / "cv_resultados.csv")
FICHAS = json.loads((AQUI / "datos" / "fichas_sinteticas.json").read_text(encoding="utf-8"))
POR_ID = {f["id"]: f for f in FICHAS}

UMBRAL = CONTRATO["umbral"]
MP = CONTRATO["metrica_prueba"]
PREV = CONTRATO["prevalencia_entrenamiento"]
CATS = CONTRATO["categorias"]
ANIO_INICIO = CONTRATO["anio_inicio"]


_cache = {"mtime": None, "datos": None}


def tablero():
    """Cifras exportadas por el .qmd, o None si el artículo aún no se generó con el bloque exporta-tablero.
    Se relee cuando el archivo cambia: si el artículo se vuelve a generar, basta con recargar la página."""
    if not ARCHIVO_TABLERO.exists():
        return None
    mtime = ARCHIVO_TABLERO.stat().st_mtime
    if _cache["mtime"] != mtime:
        _cache["datos"], _cache["mtime"] = json.loads(ARCHIVO_TABLERO.read_text(encoding="utf-8")), mtime
    return _cache["datos"]


_columnas = {}


def columnas_base():
    """Número de columnas de la base cruda, leído de su cabecera (una sola vez)."""
    if "n" not in _columnas:
        import gzip
        with gzip.open(CARPETA / "BD_2008_2025_unido_850.csv.gz", "rt", encoding="utf-8", errors="replace") as f:
            _columnas["n"] = len(f.readline().split(","))
    return _columnas["n"]


def anio_fin():
    """Último año con el que se entrenó: el del artículo si existe la exportación; si no, el de la caducidad."""
    t = tablero()
    return t["meta"]["anio_max"] if t else CONTRATO["revisar_al_cerrar_anio"] - CONTRATO["caducidad_anios"]


# Punto decimal y espacio como separador de miles, como en el artículo
def pct(x, d=1):
    return "sin dato" if x is None else f"{100 * x:.{d}f} %"


def num(x, d=3):
    return "sin dato" if x is None else f"{x:.{d}f}"


def miles(n):
    return f"{n:,.0f}".replace(",", " ")


def clasificar(filas):
    """La predicción vive en cargar_y_predecir.py: se llama a predecir() con el contrato cargado."""
    return cyp.predecir(CONTRATO, filas)


def fila_del_contrato(d):
    """Convierte lo que se digita en la ficha a las columnas que espera el modelo. Devuelve (fila, notas)."""
    notas = []
    f_not = d["fecha_notificacion"]
    f_not = f_not if isinstance(f_not, dt.date) else dt.date.fromisoformat(f_not)
    f_sin = d["fecha_sintomas"]
    if isinstance(f_sin, str):
        f_sin = dt.date.fromisoformat(f_sin)
    dias = None
    if f_sin is not None:
        dias = (f_not - f_sin).days
        if f_sin.month == 1 and f_sin.day == 1:
            dias = None
            notas.append("El 1 de enero como inicio de síntomas se trata como dato faltante.")
        elif dias < 0 or dias > DIAS_MAX:
            dias = None
            notas.append("El intervalo de síntomas no es válido y se trata como dato faltante.")
    if f_not.year > anio_fin():
        notas.append(f"El modelo se entrenó con fichas de {ANIO_INICIO} a {anio_fin()}; {f_not.year} está fuera de ese rango.")
    fila = {"edad": d["edad"], "anio": f_not.year - ANIO_INICIO, "estrato_n": d["estrato"], "dias_sintomas": dias,
            **{g: int(g in d["grupos"]) for g in CONTRATO["columnas_binarias"]},
            "sexo": d["sexo"], "regimen": d["regimen"], "area": d["area"], "etnia": d["etnia"], "region": d["region"]}
    return fila, notas
