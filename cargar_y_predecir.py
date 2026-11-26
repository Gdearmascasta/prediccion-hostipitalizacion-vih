"""Carga el modelo guardado por articulo_ML_Agamez_final.qmd y predice una notificación nueva.

Uso:  python cargar_y_predecir.py
El archivo .joblib es un diccionario: el Pipeline completo (imputación, codificación y modelo) y su contrato.
"""
import sys
import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost

ARCHIVO_MODELO = "modelo_hospitalizacion_vih.joblib"

# Una fila cruda con las columnas del contrato. dias_sintomas queda vacía (la ficha no trae la fecha de
# inicio de síntomas): la imputación del Pipeline la resuelve igual que en el entrenamiento.
FILA_EJEMPLO = {
    "edad": 41, "anio": 7, "estrato_n": 2, "dias_sintomas": None,
    "gestante": 0, "migrante": 0, "privado_libertad": 0, "desplazado": 0, "discapacidad": 0,
    "habitante_calle": 0, "victima_violencia": 0, "centro_psiquiatrico": 0,
    "sexo": "M", "regimen": "Subsidiado", "area": "Cabecera", "etnia": "Otro", "region": "Caribe",
}


def cargar(ruta=ARCHIVO_MODELO):
    contrato = joblib.load(ruta)
    instaladas = {"numpy": np.__version__, "pandas": pd.__version__,
                  "scikit-learn": sklearn.__version__, "xgboost": xgboost.__version__}
    for paquete, version in instaladas.items():
        if contrato["versiones"].get(paquete) != version:
            print(f"Aviso: {paquete} {version} instalado; el modelo se guardó con {contrato['versiones'].get(paquete)}",
                  file=sys.stderr)
    return contrato


def predecir(contrato, filas):
    """filas: diccionario o lista de diccionarios con las columnas del contrato. None o NaN = dato faltante."""
    if isinstance(filas, dict):
        filas = [filas]
    X = pd.DataFrame(filas)
    faltan = [c for c in contrato["columnas"] if c not in X.columns]
    if faltan:
        raise ValueError(f"Faltan columnas del contrato: {faltan}")
    X = X[contrato["columnas"]]
    for c in contrato["columnas_numericas"] + contrato["columnas_binarias"]:
        X[c] = pd.to_numeric(X[c], errors="coerce")          # None -> NaN
    # En el entrenamiento, un departamento sin dato se codificó como "Exterior o sin dato"
    X["region"] = X["region"].fillna("Exterior o sin dato")
    p = contrato["pipeline"].predict_proba(X)[:, 1]
    return [{"probabilidad": float(pi), "ruta_prioritaria": bool(pi >= contrato["umbral"])} for pi in p]


if __name__ == "__main__":
    contrato = cargar()
    print(f"Modelo {contrato['modelo']} v{contrato['version_modelo']} ({contrato['hiperparametros']}), "
          f"entrenado el {contrato['entrenado_el']}; umbral {contrato['umbral']:.2f}")
    print("Fila cruda:", FILA_EJEMPLO)
    r = predecir(contrato, FILA_EJEMPLO)[0]
    print(f"Probabilidad de hospitalización: {r['probabilidad']:.3f} -> "
          f"{'ruta prioritaria' if r['ruta_prioritaria'] else 'trámite habitual'}")
