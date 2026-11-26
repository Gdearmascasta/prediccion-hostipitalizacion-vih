/* ==========================================================================
   Recorrido de los datos, con la tarjeta de pasos de Sigma Analist («Técnicas comparadas»):
   círculos numerados que avanzan solos, se señalan para verlos y se tocan para fijarlos; cada paso
   tiene una ilustración animada (los registros entran como puntos y en cada filtro se quedan o se
   van), su título, su descripción y una cifra que cuenta hasta el nuevo total.
   Dash escribe <div class="recorrido" data-recorrido="{…}">; app.py arma los datos desde el .qmd.
   ========================================================================== */
(function () {
  'use strict';

  const NS = 'http://www.w3.org/2000/svg';
  const reducir = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const PUNTOS = 200, COLS = 25;            // 200 puntos: cada uno representa total / 200 registros
  const PASO_MS = 4200;
  const QUEDA = '#00929E', SALE = '#B8761C', PRUEBA = '#1A6FC0';
  const fmt = (v) => Math.round(v).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  const el = (tag, attrs = {}, padre) => {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (padre) padre.append(n);
    return n;
  };

  function montar(raiz) {
    if (raiz._rec) return;
    let D;
    try { D = JSON.parse(raiz.getAttribute('data-recorrido')); } catch (e) { return; }
    raiz._rec = { actual: 0, fijo: false, reloj: null, visible: false };
    raiz.innerHTML = `
      <div class="rec-cabeza"><span class="rec-rotulo">Recorrido de los datos</span>
        <span class="rec-cuenta">${D.pasos.length} pasos · 1 base</span></div>
      <ol class="rec-pasos" role="tablist" aria-label="Pasos del recorrido"></ol>
      <div class="rec-progreso"><span></span></div>
      <div class="rec-cuerpo">
        <div class="rec-ilustracion"><svg viewBox="0 0 420 190" aria-hidden="true"></svg></div>
        <div class="rec-texto" aria-live="polite">
          <h4 class="rec-titulo"></h4><p class="rec-desc"></p>
          <div class="rec-cifra"><b class="rec-num"></b><span class="rec-unidad"></span></div>
          <span class="rec-delta"></span>
        </div>
      </div>
      <p class="rec-pista">Señale un paso para verlo; tóquelo para fijarlo. ${D.nota_punto}</p>`;
    const lista = raiz.querySelector('.rec-pasos');
    D.pasos.forEach((p, i) => {
      const li = document.createElement('li');
      li.innerHTML = `<button type="button" role="tab" style="--c:${p.color}" aria-selected="false">
        <span class="rec-circulo">${String(i + 1).padStart(2, '0')}</span><span class="rec-nombre">${p.nombre}</span></button>`;
      const b = li.querySelector('button');
      b.addEventListener('mouseenter', () => { if (!raiz._rec.fijo) ir(raiz, D, i, true); });
      b.addEventListener('focus', () => ir(raiz, D, i, true));
      b.addEventListener('click', () => {
        raiz._rec.fijo = raiz._rec.fijo && raiz._rec.actual === i ? false : true;
        raiz.classList.toggle('fijo', raiz._rec.fijo);
        ir(raiz, D, i, true);
        reanudar(raiz, D);
      });
      lista.append(li);
    });
    raiz.addEventListener('mouseleave', () => reanudar(raiz, D));
    ir(raiz, D, 0, false);
    // avanza solo mientras está en pantalla, como la tarjeta de Sigma
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(([e]) => {
        raiz._rec.visible = e.isIntersecting;
        if (e.isIntersecting) { ir(raiz, D, raiz._rec.actual, true); reanudar(raiz, D); }
        else clearTimeout(raiz._rec.reloj);
      }, { threshold: 0.35 }).observe(raiz);
    }
  }

  function reanudar(raiz, D) {
    clearTimeout(raiz._rec.reloj);
    if (raiz._rec.fijo || reducir || !raiz._rec.visible) return;
    raiz._rec.reloj = setTimeout(() => { ir(raiz, D, (raiz._rec.actual + 1) % D.pasos.length, true); reanudar(raiz, D); }, PASO_MS);
  }

  function ir(raiz, D, i, animar) {
    const p = D.pasos[i], previo = i > 0 ? D.pasos[i - 1] : null;
    raiz._rec.actual = i;
    raiz.style.setProperty('--c', p.color);
    raiz.querySelectorAll('.rec-pasos button').forEach((b, k) => {
      b.setAttribute('aria-selected', String(k === i));
      b.classList.toggle('hecho', k < i);
    });
    const barra = raiz.querySelector('.rec-progreso span');
    barra.style.transition = 'none';
    barra.style.width = `${(100 * i) / D.pasos.length}%`;
    requestAnimationFrame(() => {
      barra.style.transition = raiz._rec.fijo || reducir ? 'none' : `width ${PASO_MS}ms linear`;
      barra.style.width = `${(100 * (i + (raiz._rec.fijo ? 1 : 1))) / D.pasos.length}%`;
    });
    raiz.querySelector('.rec-titulo').textContent = p.titulo;
    raiz.querySelector('.rec-desc').textContent = p.texto;
    raiz.querySelector('.rec-unidad').textContent = p.unidad;
    const delta = raiz.querySelector('.rec-delta');
    delta.textContent = p.delta_texto || '';
    delta.className = 'rec-delta' + (p.delta < 0 ? ' baja' : p.delta === 0 ? ' igual' : '');
    const num = raiz.querySelector('.rec-num');
    const desde = previo && previo.unidad === p.unidad ? previo.valor : 0;
    const g = !reducir && window.gsap;
    if (g && animar) {
      const est = { v: desde };
      g.to(est, { v: p.valor, duration: 1.1, ease: 'power2.out', onUpdate: () => { num.textContent = fmt(est.v); } });
    } else num.textContent = fmt(p.valor);
    ilustrar(raiz.querySelector('.rec-ilustracion svg'), D, p, animar && g ? g : null);
  }

  // ------------------------------------------------------------------------
  // Ilustraciones: la rejilla de puntos de los registros, o las columnas
  // ------------------------------------------------------------------------
  function rejilla(svg, n, x0, y0, paso) {
    const pts = [];
    for (let k = 0; k < n; k++) pts.push([x0 + (k % COLS) * paso, y0 + Math.floor(k / COLS) * paso]);
    return pts;
  }

  function ilustrar(svg, D, p, g) {
    if (g) g.killTweensOf(svg.querySelectorAll('*'));
    svg.textContent = '';
    const tipo = p.tipo;
    if (tipo === 'columnas') return columnas(svg, D, p, g);
    const antes = Math.round(PUNTOS * p.antes / D.total), despues = Math.round(PUNTOS * p.valor_filas / D.total);
    // la rejilla se centra en vertical según cuántas filas tenga
    const y0 = Math.max(22, Math.round((168 - Math.ceil(antes / COLS) * 13) / 2));
    const pts = rejilla(svg, antes, 26, y0, 13);
    const fuera = el('g', {}, svg);
    if (tipo !== 'entra' && tipo !== 'particion') {
      el('rect', { x: 352, y: 22, width: 52, height: 116, rx: 10, class: 'rec-bandeja' }, fuera);
      el('text', { x: 378, y: 156, class: 'rec-etq' }, fuera).textContent = 'fuera';
    }
    const salen = antes - despues;
    pts.forEach(([x, y], k) => {
      const sale = tipo === 'filtra' && k >= antes - salen;
      const c = el('circle', { cx: x, cy: y, r: 4.6, fill: QUEDA }, svg);
      if (tipo === 'entra' && g) {
        g.from(c, { attr: { cx: -20 }, opacity: 0, duration: 0.7, ease: 'power3.out', delay: (k % COLS) * 0.025 + Math.floor(k / COLS) * 0.05 });
      }
      if (sale) {
        // se apilan en la bandeja «fuera»: 8 por fila, más pequeños para que quepan
        const j = k - (antes - salen);
        const destino = [357 + (j % 8) * 6, 30 + Math.floor(j / 8) * 6];
        if (g) {
          g.to(c, { attr: { fill: SALE }, duration: 0.35, delay: 0.3 });
          g.to(c, { attr: { cx: destino[0], cy: destino[1], r: 2.5 }, duration: 0.9, ease: 'power2.inOut', delay: 0.7 + (j % 20) * 0.02 });
        } else { c.setAttribute('fill', SALE); c.setAttribute('cx', destino[0]); c.setAttribute('cy', destino[1]); c.setAttribute('r', 2.5); }
      }
      if (tipo === 'particion') {
        const prueba = k >= Math.round(antes * (1 - p.prop_prueba));
        const j = prueba ? k - Math.round(antes * (1 - p.prop_prueba)) : k;
        const destino = prueba ? [300 + (j % 7) * 13, y0 + Math.floor(j / 7) * 13] : [26 + (j % 19) * 13, y0 + Math.floor(j / 19) * 13];
        if (g) {
          g.to(c, { attr: { cx: destino[0], cy: destino[1] }, duration: 1, ease: 'power3.inOut', delay: 0.4 + (k % 25) * 0.012 });
          if (prueba) g.to(c, { attr: { fill: PRUEBA }, duration: 0.4, delay: 0.3 });
        } else { c.setAttribute('cx', destino[0]); c.setAttribute('cy', destino[1]); if (prueba) c.setAttribute('fill', PRUEBA); }
      }
    });
    // pasos que quitan menos de un punto: se dice, no se dibujan puntos inventados
    if (tipo === 'filtra' && salen === 0) {
      const ult = pts[pts.length - 1] || [26, 22];
      const lupa = el('g', {}, svg);
      el('circle', { cx: ult[0], cy: ult[1], r: 9, class: 'rec-lupa' }, lupa);
      const t = el('text', { x: 378, y: 86, class: 'rec-etq fuerte' }, lupa);
      t.textContent = p.delta === 0 ? 'nadie' : `−${fmt(-p.delta)}`;
      const t2 = el('text', { x: 378, y: 102, class: 'rec-etq' }, lupa);
      t2.textContent = p.delta === 0 ? 'sale' : '< 1 punto';
      if (g) g.from(lupa, { opacity: 0, scale: 0.6, transformOrigin: '50% 50%', duration: 0.6, ease: 'back.out(2)', delay: 0.5 });
    }
    if (tipo === 'particion') {
      el('text', { x: 140, y: 178, class: 'rec-etq' }, svg).textContent = p.etq_a;
      el('text', { x: 339, y: 178, class: 'rec-etq' }, svg).textContent = p.etq_b;
    }
  }

  function columnas(svg, D, p, g) {
    const n0 = p.antes, n1 = p.valor, ancho = 360 / n0;
    const quedan = new Set(p.indices_quedan);
    for (let k = 0; k < n0; k++) {
      const queda = quedan.has(k);
      const r = el('rect', { x: 30 + k * ancho, y: 30, width: Math.max(ancho - 1.2, 1.5), height: 104, rx: 1.5, fill: QUEDA }, svg);
      if (!queda) {
        if (g) {
          g.to(r, { attr: { fill: SALE }, duration: 0.3, delay: 0.3 });
          g.to(r, { attr: { y: 150, height: 6 }, opacity: 0.25, duration: 0.8, ease: 'power2.in', delay: 0.6 + k * 0.006 });
        } else { r.setAttribute('fill', SALE); r.setAttribute('y', 150); r.setAttribute('height', 6); r.setAttribute('opacity', 0.25); }
      } else if (g) g.to(r, { attr: { height: 112, y: 26 }, duration: 0.5, ease: 'back.out(2)', delay: 1.4 });
    }
    el('text', { x: 210, y: 182, class: 'rec-etq' }, svg).textContent = `${n0} columnas crudas → ${n1} variables del modelo`;
  }

  function buscar(r) {
    if (r.matches && r.matches('.recorrido[data-recorrido]')) montar(r);
    if (r.querySelectorAll) r.querySelectorAll('.recorrido[data-recorrido]').forEach(montar);
  }
  function arrancar() {
    new MutationObserver((cs) => cs.forEach((c) => c.addedNodes.forEach((n) => { if (n.nodeType === 1) buscar(n); })))
      .observe(document.body, { childList: true, subtree: true });
    buscar(document.body);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', arrancar);
  else arrancar();
})();
