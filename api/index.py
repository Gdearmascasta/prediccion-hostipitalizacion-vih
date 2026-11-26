"""Punto de entrada de Vercel: expone el servidor Flask del tablero Dash (dashboard/app.py) como `app`.

Vercel enruta todas las peticiones aquí (ver vercel.json). El tablero lee el modelo, cargar_y_predecir.py y la
carpeta resultados/ desde la raíz del repositorio, igual que en local.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "dashboard"))

from app import server as app  # noqa: E402,F401
