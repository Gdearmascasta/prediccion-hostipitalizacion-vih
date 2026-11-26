# Tablero del artículo

Tablero en Dash con estética de vidrio líquido (modo claro, paleta de la portada UTB) y las animaciones de
Sigma Analist (GSAP). Muestra los resultados del artículo y clasifica fichas de prueba. No entrena nada y no
modifica los archivos del artículo: lee lo que el `.qmd` genera.

## Correrlo en el computador

Desde la raíz del repositorio:

```bash
uv venv --python 3.12 .venv                                   # una sola vez
uv pip install --python .venv -r dashboard/requirements.txt   # una sola vez
.venv/bin/python dashboard/app.py
```

Se abre en http://127.0.0.1:8050. Si ese puerto está ocupado: `PORT=8060 .venv/bin/python dashboard/app.py`.

## Qué lee

| Archivo (en la raíz) | Para qué |
|---|---|
| `modelo_hospitalizacion_vih.joblib` | Modelo, umbral, métricas de prueba, categorías y caducidad |
| `cargar_y_predecir.py` | Funciones `cargar()` y `predecir()` |
| `resultados/cv_resultados.csv` | AUC y AP por pliegue |
| `resultados/tablero.json` | Cifras de todas las demás figuras y tablas. Lo escribe el bloque `exporta-tablero` al final del `.qmd` |
| `dashboard/datos/fichas_sinteticas.json` | Ocho fichas inventadas; se pueden editar o agregar más |

Ninguna cifra está escrita a mano en el tablero. Si el artículo se vuelve a generar, basta con recargar la página.
Si `tablero.json` viene de un render de ensayo (`MUESTRA_DESARROLLO = 12_000`), el tablero lo avisa con un
recuadro naranja: antes de presentar, vuelva a generar el artículo con `None`. Sin `tablero.json`, el tablero
funciona con el modelo (resumen, comparación por pliegues, clasificación) y avisa qué falta.

## Pestañas

1. **Resumen**: la pregunta, cifras clave, qué logra la regla (barras estilo Sigma: Prueba / Validación cruzada /
   Comparar y orden animado) y el recorrido de los datos: tarjeta de 7 pasos como la de Sigma, donde los registros
   entran como puntos y en cada filtro se quedan o salen, las columnas se vuelven variables y los casos se reparten.
2. **Los datos**: hospitalización por año, edad al notificarse, explorador de factores y departamentos.
3. **Modelos**: los siete clasificadores pliegue a pliegue, curvas ROC y de precisión, comprobaciones y tablas.
4. **Umbral y prueba**: deslizador del umbral con costo y métricas en vivo, calibración, matriz de la prueba.
5. **Clasificar una ficha**: formulario que reclasifica al instante y clasificación del lote de fichas.
6. **Variables y equidad**: importancia, desempeño por subgrupo, reconstrucción del atributo protegido, modelo sin sexo.
7. **Monitoreo**: PSI, desempeño por año, perfiles de K-means y pronóstico LSTM de la serie semanal.
8. **Límites y despliegue**: límites declarados, prueba con intervalos, cómo viaja una ficha, contrato, código QR
   del repositorio y equipo.

Cada gráfica tiene leyenda, valores a la vista, detalle al pasar el cursor y un botón «i» que explica en breve qué
muestra; ninguna repite lo que explica otra. Siguen el formato de las gráficas de Sigma Analist (barras que crecen,
líneas que se dibujan, tooltip en tarjeta, flechas del teclado y una tabla accesible con los mismos datos).

## Archivos

| Archivo | Qué es |
|---|---|
| `app.py` | Layout y callbacks (punto de entrada; expone `server`) |
| `datos.py` | Carga del contrato, los resultados y las fichas; conversión de la ficha a las columnas del contrato |
| `figuras.py` | Una función por gráfica: devuelve la especificación que dibuja `graficas.js` (la de costo según el umbral sigue en Plotly, a pedido) y la paleta validada |
| `assets/estilos.css` | Vidrio líquido en modo claro |
| `assets/animaciones.js` | Coreografía de Sigma Analist: revelado con desenfoque, ola, palabras, letras, contadores y la tarjeta de la regla |
| `assets/graficas.js` | Gráficas en el formato de Sigma Analist: SVG propio, leyenda que enciende y apaga series, tooltip, teclado y animación |
| `assets/recorrido.js` | Tarjeta de pasos del recorrido de los datos (pestaña 1) |
| `assets/qr_github.jpeg` | Código QR del repositorio en GitHub (pestaña 8) |

## Publicarlo en la web

**Vercel** (recomendado): ver la sección «Publicar en Vercel» del `README.md` de la raíz. El repositorio trae
`api/index.py`, `vercel.json`, `requirements.txt` y `.python-version`; basta con importar el repositorio en Vercel.

**Cualquier servidor con gunicorn**, desde la raíz:

```bash
gunicorn api.index:app
```
