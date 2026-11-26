# Predicción de la hospitalización en la notificación de VIH (SIVIGILA, Colombia, 2018–2025)

Artículo final del curso Machine Learning 2026-II (Universidad Tecnológica de Bolívar) y su tablero interactivo.

Autores: Didier Agamez, Angel Vega, Germán de Armas y Karla Barraza.

El artículo se genera completo desde un único archivo Quarto (`articulo_ML_Agamez_final.qmd`): todas las cifras,
tablas y figuras salen del código. El tablero (`dashboard/`) lee lo que ese render deja en disco; no recalcula nada.

## Contenido

| Archivo | Qué es |
|---|---|
| `articulo_ML_Agamez_final.qmd` | Fuente del artículo: texto, análisis, modelos, tablas, figuras y exportación para el tablero |
| `referencias.bib`, `apa.csl` | Bibliografía y estilo APA |
| `BD_2008_2025_unido_850.csv.gz` | Microdatos del evento 850 del SIVIGILA (2008–2025), archivos anuales unidos |
| `modelo_hospitalizacion_vih.joblib` | Modelo definitivo (XGBoost) con su contrato. Lo genera el `.qmd` |
| `resultados/cv_resultados.csv` | Resultados por pliegue de la validación cruzada. Lo genera el `.qmd` |
| `resultados/tablero.json` | Cifras de las figuras y tablas para el tablero. Lo genera el bloque `exporta-tablero` del `.qmd` |
| `articulo_ML_Agamez_final.pdf` | Artículo generado con la base completa |
| `cargar_y_predecir.py` | Carga el modelo guardado y predice una notificación |
| `dashboard/` | Tablero en Dash (ver `dashboard/LEEME.md`) |
| `api/`, `vercel.json` | Despliegue en Vercel |
| `requirements-articulo.txt` | Entorno completo con que se genera el artículo (incluye torch y Jupyter) |
| `requirements.txt` | Entorno de la función de Vercel |
| `dashboard/requirements.txt` | Entorno mínimo del tablero |

El servicio Flask (`app.py`) de la entrega se retiró del repositorio: el tablero lo reemplaza y sigue en el historial de git.

## Tablero

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv -r dashboard/requirements.txt
.venv/bin/python dashboard/app.py          # http://127.0.0.1:8050
```

## Publicar en Vercel

El repositorio ya trae lo necesario para desplegar el tablero como una función Python de Vercel:

| Archivo | Para qué |
|---|---|
| `api/index.py` | Punto de entrada: expone el servidor Flask del tablero Dash como `app` |
| `vercel.json` | Envía todas las rutas a `api/index.py`; fija memoria, duración máxima y archivos excluidos |
| `requirements.txt` | Dependencias de la función (usa `xgboost-cpu` 3.4.1, el mismo xgboost sin librerías de GPU) |
| `.python-version` | Python 3.12 |
| `.vercelignore` | Deja fuera el artículo, el entorno local y los documentos de trabajo |

Pasos:

1. En https://vercel.com, **Add New → Project** e importar este repositorio de GitHub.
2. Framework preset: **Other**. Root directory: la raíz del repositorio. No hace falta comando de build ni variables
   de entorno.
3. **Deploy**. Cada push a `main` vuelve a desplegar.

Con la CLI: `npm i -g vercel`, luego `vercel` (vista previa) o `vercel --prod` desde la raíz.

La función pesa unos 300 MB sin comprimir (el límite de Vercel para Python es 500 MB). El primer acceso tras un rato
sin visitas tarda unos segundos mientras carga el modelo. Si se vuelve a generar el artículo, hay que hacer commit
de `modelo_hospitalizacion_vih.joblib` y `resultados/` para que el despliegue muestre las cifras nuevas.

## Reproducir el artículo

Requiere Python 3.12 y [Quarto](https://quarto.org) 1.10 o posterior con `xelatex` (`quarto install tinytex`).

```bash
uv pip install --python .venv -r requirements-articulo.txt
export QUARTO_PYTHON="$PWD/.venv/bin/python"
quarto render articulo_ML_Agamez_final.qmd --to pdf
```

- Con la base completa el render tarda alrededor de 75 minutos (la validación cruzada anidada es lo más lento).
- Para un ensayo rápido, cambie `MUESTRA_DESARROLLO = None` por `12_000` (unos 15 minutos). Esas cifras no son las
  del artículo y el tablero lo avisa; vuelva a dejar `None` antes del render definitivo.
- El render sobrescribe el `.joblib`, `resultados/cv_resultados.csv` y `resultados/tablero.json`, con la semilla fijada.

## Datos

Los microdatos son públicos. Se descargaron del [portal del SIVIGILA](https://portalsivigila.ins.gov.co/Paginas/Buscador.aspx)
del Instituto Nacional de Salud de Colombia. La fecha de descarga y la descripción de las variables están en el artículo.
