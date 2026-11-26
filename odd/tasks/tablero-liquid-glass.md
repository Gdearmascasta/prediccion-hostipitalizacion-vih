# Tablero liquid glass (Dash) alimentado por el qmd
Objetivo: rehacer el tablero en Dash con la estética liquid glass de la guía de Posit, la paleta UTB de la última captura y las animaciones de Sigma Analist, leyendo todas las cifras de lo que exporta el qmd.
Rama: main (sin commits: los pide el usuario). Entrega: un solo bloque. Pruebas: smoke tests con `dash.testing`-free (import + callbacks) y navegador real.

## Specs
- S1. "Quiero que a este tablero le incorpores la interfaz de liquid glass como te la paso en el link de posit cloud" — guía: https://01a2057d-f00e-0325-72e3-2329520e3b87.share.connect.posit.cloud/ (app Dash, `assets/estilos.css`).
- S2. "usa la paleta de colores de la ultima captura que tome" — `~/Imágenes/Capturas de pantalla/Captura desde 2026-11-25 17-52-39.png`: marino #14305A, turquesa #2BB3C0, azul #1A6FC0, blanco y celeste.
- S3. "Usa las animaciones de la pagina que te pase (sigma analist)" — https://sigma-utb.vercel.app/ (GSAP: revelado con desenfoque, títulos palabra a palabra, titular letra a letra, cifras que cuentan, filas en ola).
- S4. "la interfaz debe ser acorde a la tematica del proyecto"
- S5. "todo debe ser interactivo, todas las graficas deben de tener leyendas y ser interactivas ademas de tener los valores a la vista"
- S6. "deben de tener un boton flotante que explique brevemente lo que hablan ( no pueden haber dos graficas que expliquen lo mismo, asi que elige lo mas adecuado)"
- S7. "Integra paneles modernos."
- S8. "El tablero debee de correr con la informacion directa de los qmd" — decisión del usuario: el qmd vuelve al repo, un bloque final exporta `resultados/tablero.json` y se renderiza completo una vez.
- S9. "debe de mantener las funciones que ya tiene por defecto" — resumen, comparación de modelos, clasificar una ficha (formulario + fichas sintéticas en lote), límites y despliegue (contrato).
- S10. "en la grafica de "De la base unida a los casos útiles" resume la informacion o deja que el usuario decida cuantas barras ver, ya que como no hay mucha diferencia entre categorias la grafica parece que sobra"
- S11. "en el apartado "Qué logra la regla en la prueba" muestra los datos con animaciones parecido a los modelos de la app de sigma analist"
- S12. "integra en despliegue el codigo qr del proyecto. esta en descargas" — `~/Descargas/Entrega_Proyecto_ML_Agamez/Qr_github.jpeg`.
- S13. "haz una animacion de archify ahi que muestre como caminan los datos y como van cambiando" y luego "vamos mejorando, pero te decia algo asi ( mira mi ultima grabacion de pantalla)" / "con eso haz la animacion donde ingresen los datosy se quede o se le saque algo y asi" — referencia: tarjeta «Técnicas comparadas» de Sigma.
- S14. "cambia el formato de las graficas hechas en plotly y pon las que estan en el formato de sigma analist" — excepción posterior: "la grafica de "Costo esperado según el umbral" dejala como estaba antes, me gustaba mas".
- Decisión del usuario: migrar de Streamlit a Dash (publicación en Posit Connect Cloud).

## Tasks
| ID | Specs | Ruta | Estado | Evidencia |
|---|---|---|---|---|
| T1 | S8 | inline | hecho | bloque `exporta-tablero` (134 líneas añadidas, 0 borradas); ensayo 12 000 en scratch: exit 0, tablero.json 213 KB |
| T2 | S8 | inline (render en segundo plano) | hecho | render completo exit 0 en 23.6 min; contrato igual (AUC 0.795, umbral 0.18); cv_resultados difiere ≤ 2e-8 |
| T3 | S1-S4, S7 | inline | hecho | app.py, estilos.css (modo claro), animaciones.js (GSAP + IntersectionObserver) |
| T4 | S9 | inline | hecho | resumen, comparación, ficha (en vivo) + lote, límites y contrato; 9/9 pruebas de interacción en Chrome |
| T5 | S5, S6, S8 | inline | hecho | 25 gráficas, 25 con leyenda, botón «i» en cada una; paleta validada (5/5 PASS, superficie clara) |
| T7 | S10, S11 | inline | hecho | flujo resumen/detalle; tarjeta de la regla estilo Sigma; 14/14 comprobaciones en Chrome |
| T8 | S12 | inline | hecho | QR (decodificado: github.com/DidierAgamez/Prediccion-Hostipitalizacion-VIH-colombia) en la pestaña 8 |
| T9 | S13 | inline | hecho | tarjeta de pasos del recorrido (recorrido.js): avanza sola, se fija al tocar; Chrome sin errores |
| T10 | S14 | inline | hecho | 17 gráficas en formato Sigma (graficas.js); leyenda alternable, tooltip, teclado; 1440 y 390 px sin errores |
| T6 | todas | inline | hecho | con cifras reales: 25/25 gráficas con leyenda, 0 bloques invisibles, 9/9 interacciones, 390 px sin desborde, 0 errores JS; gunicorn sirve; docs al día |

## Log
- L1 (2026-11-25, pedido original): "Quiero que a este tablero le incorpores la interfaz de liquid glass como te la paso en el link de posit cloud, usa la paleta de colores de la ultima captura que tome. Usa las animaciones de la pagina que te pase (sigma analist), la interfaz debe ser acorde a la tematica del proyecto, todo debe ser interactivo, todas las graficas deben de tener leyendas y ser interactivas ademas de tener los valores a la vista, deben de tener un boton flotante que explique brevemente lo que hablan ( no pueden haber dos graficas que expliquen lo mismo, asi que elige lo mas adecuado). Integra paneles modernos. El tablero debee de correr con la informacion directa de los qmd y debe de mantener las funciones que ya tiene por defecto"
- L2: el usuario eligió "Migrar a Dash (Recomendado)" y "Sí, exportar y renderizar (Recomendado)".
- L3: rutas inline (ningún disparador de escritor: una sola unidad de comportamiento encadenada). Mirror Engram pendiente: el hook bloquea `mem_save` en modo automático.
- L4 (2026-11-25): "agrega las figuras que veas necesarias" — el usuario delega la elección de figuras.
- L5 (2026-11-25): "no agregues modo oscuro, solo modo claro" — S1/S2 se aplican sobre la variante clara de la guía.
- L6: Streamlit retirado (dashboard.py y .streamlit/ con git rm); Dash 4.5.1, Plotly 7.2.0, gunicorn 23.0.0.
- L7: ScrollTrigger dejaba bloques invisibles (posiciones viejas al montar pestañas); se reemplazó por IntersectionObserver con las mismas tweens de Sigma.
- L8: mientras no termine el render completo, tablero.json es el del ensayo y el tablero muestra el aviso «Cifras de ensayo».
- L9: render completo terminado; el aviso de ensayo desaparece solo. IC de la AUC de prueba 0.789–0.801. Sin commits (NEPTUNO: solo si el usuario los pide).
- L10 (2026-11-25): "en la grafica de "De la base unida a los casos útiles" resume la informacion o deja que el usuario decida cuantas barras ver..." y "en el apartado "Qué logra la regla en la prueba" muestra los datos con animaciones parecido a los modelos de la app de sigma analist". La tarjeta reemplaza al waffle (no dos explicaciones de lo mismo).
- L11 (2026-11-25): "integra en despliegue el codigo qr del proyecto. esta en descargas". Los dos QR de Descargas son idénticos y apuntan al repositorio.
- L12 (2026-11-25): "elige otro tipo de grafica para De la base unida a los casos útiles" → Sankey; luego archify (validado showcase 9/9, visual-check pass); luego la tarjeta de pasos de la grabación, que reemplaza a ambos.
- L13 (2026-11-25): gráficas a formato Sigma con motor SVG propio; "Costo esperado según el umbral" vuelve a Plotly a pedido.
