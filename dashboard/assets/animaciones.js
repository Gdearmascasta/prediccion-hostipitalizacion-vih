/* ==========================================================================
   Coreografía de Sigma Analist (GSAP), adaptada a Dash:
     .revelar          sube 24 px y pasa de desenfocado a nítido al entrar en pantalla
     .ola              sus hijos .revelar entran en ola de izquierda a derecha
     [data-letras]     el titular entra letra a letra (con copia .sr-only para lectores de pantalla)
     [data-palabras]   los títulos entran palabra a palabra
     .contador         las cifras cuentan hasta su valor y terminan con el texto original exacto
     .regla            la línea bajo cada título se dibuja de izquierda a derecha
     [data-regla]      barras de la regla como las de modelos de Sigma: crecen en cascada al entrar en pantalla,
                       botones Prueba / Validación cruzada / Comparar y orden con animación FLIP
   Dash monta y desmonta el contenido de cada pestaña: un MutationObserver anima cada nodo nuevo una vez, y un
   IntersectionObserver dispara la entrada cuando el nodo aparece en pantalla (las posiciones que calcularía
   ScrollTrigger quedan viejas mientras Plotly termina de dibujar).
   Con prefers-reduced-motion no se mueve ni se parte nada.
   ========================================================================== */
(function () {
  'use strict';

  const reducir = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const hechos = new WeakSet();
  const DESDE = { autoAlpha: 0, y: 24, filter: 'blur(6px)' };
  const LIMPIAR = 'opacity,visibility,transform,filter';
  const HACIA = { autoAlpha: 1, y: 0, filter: 'blur(0px)', duration: 0.8, ease: 'power3.out', overwrite: true, clearProps: LIMPIAR };

  // Llama a fn una vez, cuando el elemento entra en pantalla
  const pendientes = new WeakMap();
  const vigia = new IntersectionObserver((entradas) => {
    entradas.forEach((e) => {
      if (!e.isIntersecting) return;
      const fn = pendientes.get(e.target);
      vigia.unobserve(e.target);
      pendientes.delete(e.target);
      if (fn) fn();
    });
  }, { rootMargin: '0px 0px -6% 0px', threshold: 0.01 });
  function alEntrar(el, fn) { pendientes.set(el, fn); vigia.observe(el); }

  function partirLetras(el) {
    const rotulo = el.textContent.replace(/\s+/g, ' ').trim();
    const frag = document.createDocumentFragment();
    rotulo.split(/( )/).forEach((parte) => {
      if (!parte) return;
      if (parte === ' ') { frag.append(' '); return; }
      const wd = document.createElement('span');
      wd.className = 'wd';
      Array.from(parte).forEach((c) => {
        const s = document.createElement('span');
        s.className = 'ch';
        s.setAttribute('aria-hidden', 'true');
        s.textContent = c;
        wd.append(s);
      });
      frag.append(wd);
    });
    const sr = document.createElement('span');
    sr.className = 'sr-only';
    sr.textContent = rotulo;
    el.textContent = '';
    el.append(frag, sr);
    return el.querySelectorAll('.ch');
  }

  function partirPalabras(el) {
    const palabras = el.textContent.trim().split(/\s+/);
    el.textContent = '';
    palabras.forEach((p, i) => {
      if (i) el.append(' ');
      const s = document.createElement('span');
      s.className = 'palabra';
      s.textContent = p;
      el.append(s);
    });
    return el.querySelectorAll('.palabra');
  }

  // Cuenta hasta la cifra respetando el formato del artículo: punto decimal y espacio de miles
  function contar(el, gsap) {
    const crudo = el.textContent;
    const m = crudo.match(/^(\D*?)(\d[\d\s.]*)(\D*)$/);
    if (!m) return;
    const [, prefijo, numero, sufijo] = m;
    const limpio = numero.trim().replace(/\s/g, '');
    const valor = Number(limpio);
    if (!Number.isFinite(valor)) return;
    const decimales = (limpio.split('.')[1] || '').length;
    const conMiles = /\d\s\d/.test(numero);
    const resto = numero.match(/\s+$/) ? numero.match(/\s+$/)[0] : '';
    const fmt = (v) => {
      const [e, d] = v.toFixed(decimales).split('.');
      return (conMiles ? e.replace(/\B(?=(\d{3})+(?!\d))/g, ' ') : e) + (d ? '.' + d : '');
    };
    const estado = { v: 0 };
    el.textContent = prefijo + fmt(0) + resto + sufijo;
    alEntrar(el, () => gsap.to(estado, {
      v: valor, duration: 1.2, ease: 'power2.out',
      onUpdate: () => { el.textContent = prefijo + fmt(estado.v) + resto + sufijo; },
      onComplete: () => { el.textContent = crudo; },
    }));
  }

  function animar(raiz, gsap) {
    const todos = (sel) => {
      const lista = raiz.matches && raiz.matches(sel) ? [raiz] : [];
      return lista.concat(Array.from(raiz.querySelectorAll ? raiz.querySelectorAll(sel) : []));
    };
    const nuevo = (el) => { if (hechos.has(el)) return false; hechos.add(el); return true; };

    todos('[data-letras]').filter(nuevo).forEach((el) => {
      const letras = partirLetras(el);
      gsap.set(letras, { autoAlpha: 0, y: 20, filter: 'blur(6px)' });
      gsap.to(letras, { autoAlpha: 1, y: 0, filter: 'blur(0px)', duration: 0.75, ease: 'power3.out',
                        stagger: 0.014, delay: 0.1, clearProps: LIMPIAR });
    });

    todos('[data-palabras]').filter(nuevo).forEach((el) => {
      const palabras = partirPalabras(el);
      gsap.set(palabras, DESDE);
      alEntrar(el, () => gsap.to(palabras, { ...HACIA, stagger: 0.045 }));
    });

    todos('.regla').filter(nuevo).forEach((el) => {
      gsap.set(el, { scaleX: 0 });
      alEntrar(el, () => gsap.to(el, { scaleX: 1, duration: 0.8, ease: 'power2.out', delay: 0.15 }));
    });

    todos('.ola').filter(nuevo).forEach((grupo) => {
      const items = Array.from(grupo.querySelectorAll(':scope > .revelar'));
      const caja = grupo.getBoundingClientRect();
      items.forEach((item) => {
        hechos.add(item);
        gsap.set(item, DESDE);
        const r = item.getBoundingClientRect();
        // retraso proporcional a la posición horizontal: la fila entra como una ola
        const retraso = caja.width > 0 ? ((r.left - caja.left) / caja.width) * 0.22 : 0;
        alEntrar(item, () => gsap.to(item, { ...HACIA, delay: retraso }));
      });
    });

    todos('.revelar').filter(nuevo).forEach((el) => {
      gsap.set(el, DESDE);
      alEntrar(el, () => gsap.to(el, HACIA));
    });

    todos('.contador').filter(nuevo).forEach((el) => contar(el, gsap));
  }

  // Tarjeta de la regla. Los botones funcionan siempre; el movimiento solo si el sistema no pide reducirlo.
  const reglas = new WeakSet();
  function prepararRegla(tarjeta) {
    if (reglas.has(tarjeta)) return;
    reglas.add(tarjeta);
    const lista = tarjeta.querySelector('.regla-lista');
    const filas = Array.from(lista.children);
    const idea = tarjeta.querySelector('[data-regla-idea]');
    const orden = tarjeta.querySelector('[data-ordenar]');
    const botones = Array.from(tarjeta.querySelectorAll('.segmentado [data-modo]'));
    let ordenado = false;
    // FLIP: se mide dónde estaba cada fila, se reordena y se anima desde la posición vieja
    function reordenar() {
      const clave = tarjeta.dataset.modo === 'cv' ? 'cv' : 'prueba';
      const destino = ordenado ? filas.slice().sort((a, b) => +b.dataset[clave] - +a.dataset[clave]) : filas;
      const antes = new Map(filas.map((f) => [f, f.getBoundingClientRect().top]));
      destino.forEach((f) => lista.append(f));
      if (reducir || typeof Element.prototype.animate !== 'function') return;
      filas.forEach((f) => {
        const dy = antes.get(f) - f.getBoundingClientRect().top;
        if (dy) f.animate([{ transform: `translateY(${dy}px)` }, { transform: 'none' }],
                          { duration: 480, easing: 'cubic-bezier(.16, 1, .3, 1)' });
      });
    }
    botones.forEach((b) => b.addEventListener('click', () => {
      const modo = b.dataset.modo;
      tarjeta.dataset.modo = modo;
      botones.forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      const texto = tarjeta.getAttribute('data-idea-' + modo);
      if (idea && texto) idea.textContent = texto;
      if (ordenado) reordenar();
    }));
    if (orden) orden.addEventListener('click', () => {
      ordenado = !ordenado;
      orden.setAttribute('aria-pressed', String(ordenado));
      reordenar();
    });
    // las barras crecen cuando la tarjeta entra en pantalla
    if (!reducir) {
      tarjeta.classList.add('pendiente');
      alEntrar(tarjeta, () => requestAnimationFrame(() => tarjeta.classList.remove('pendiente')));
    }
  }
  function buscarReglas(raiz) {
    if (raiz.matches && raiz.matches('[data-regla]')) prepararRegla(raiz);
    if (raiz.querySelectorAll) raiz.querySelectorAll('[data-regla]').forEach(prepararRegla);
  }

  function iniciar(intentos) {
    const listo = window.gsap && document.getElementById('react-entry-point');
    if (!listo) {
      if (intentos > 0) setTimeout(() => iniciar(intentos - 1), 120);
      return;
    }
    if (reducir) return;
    const { gsap } = window;
    const observador = new MutationObserver((cambios) => {
      cambios.forEach((c) => c.addedNodes.forEach((n) => {
        // los nodos internos de Plotly no llevan clases de animación: se saltan
        if (n.nodeType === 1 && !(n.closest && n.closest('.js-plotly-plot'))) animar(n, gsap);
      }));
    });
    observador.observe(document.body, { childList: true, subtree: true });
    animar(document.body, gsap);
  }

  // La tarjeta de la regla no depende de GSAP: si el CDN no carga, sus botones siguen funcionando
  function iniciarReglas() {
    new MutationObserver((cambios) => cambios.forEach((c) => c.addedNodes.forEach((n) => {
      if (n.nodeType === 1) buscarReglas(n);
    }))).observe(document.body, { childList: true, subtree: true });
    buscarReglas(document.body);
  }

  function arrancar() { iniciarReglas(); iniciar(80); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', arrancar);
  else arrancar();
})();
