# Tablero VIH · SIVIGILA

Repo del artículo (Quarto) y de su tablero en Dash (`dashboard/`). El tablero no reentrena ni recalcula: lee lo
que el render del `.qmd` deja en disco.

## Reglas
- Código, comentarios y textos de la UI en español (como el código existente). Punto decimal y espacio de miles.
- Ninguna cifra escrita a mano en el tablero: todo sale del contrato (`.joblib`), de `resultados/cv_resultados.csv`
  o de `resultados/tablero.json`. Si falta un dato, se añade al bloque `exporta-tablero` del `.qmd` (al final).
- No editar a mano el `.joblib` ni `resultados/*`: los genera el `.qmd`.
- Solo modo claro (pedido del usuario). Paleta de la portada UTB: marino #14305A, turquesa #2BB3C0, azul #1A6FC0.
  La categórica de `figuras.py` está validada con el validador de la skill dataviz; si se cambia, revalidar.
- Cada gráfica: leyenda, valores a la vista, hover y botón «i» con una explicación que no repita la de otra.
- Gráficas en formato Sigma Analist: `figuras.py` devuelve especificaciones y `assets/graficas.js` las dibuja en SVG.
  Excepción pedida por el usuario: «Costo esperado según el umbral» se queda en Plotly.
- «De la base unida a los casos útiles» es la tarjeta de pasos de `assets/recorrido.js` (como «Técnicas comparadas»
  de sigma-utb.vercel.app); el usuario descartó la cascada, el Sankey y la animación de archify.
- Versiones de numpy/pandas/scikit-learn/xgboost iguales a `contrato["versiones"]` (Python 3.12).
- `app.py` (Flask) archivado en `../articulo_archivo/`.

## Comandos
- Entorno del tablero: `uv venv --python 3.12 .venv && uv pip install --python .venv -r dashboard/requirements.txt`
- Correr: `.venv/bin/python dashboard/app.py` (puerto 8050; en esta máquina lo usa otra app: `PORT=8060`).
- Render del artículo: `uv pip install --python .venv -r requirements-articulo.txt`, luego
  `QUARTO_PYTHON=$PWD/.venv/bin/python quarto render articulo_ML_Agamez_final.qmd --to pdf` (~75 min; ensayo con
  `MUESTRA_DESARROLLO = 12_000`, ~15 min, mejor en una copia aparte para no sobrescribir los resultados).
- Prueba de humo sin navegador: importar `dashboard/app.py`, llamar `construir()` y cada `cb_*` con sus opciones.

## Datos
- `tablero.json` (claves): meta, flujo, disfrazados, descriptivo, cv, curvas, prev_tv, umbral, prueba, subgrupos,
  importancia, monitoreo, equidad, no_supervisado, edad_regresion, serie.
- Contrato del `.joblib`: pipeline, modelo, umbral, columnas, columnas_numericas/binarias, categorias,
  metrica_prueba, prevalencia_entrenamiento, anio_inicio, caducidad_anios, revisar_al_cerrar_anio, versiones.
- Base cruda: 230 828 filas, 70 columnas del SIVIGILA; el artículo usa 142 379 casos útiles de 2018–2025.
