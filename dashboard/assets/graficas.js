/* ==========================================================================
   Gráficas del tablero en el formato de Sigma Analist (tarjetas al estilo tweakcn/shadcn):
   SVG propio sin librerías, leyenda que enciende y apaga series, columna resaltada con tooltip,
   flechas del teclado, valores a la vista y una tabla .sr-only con los mismos datos.
   Animación con GSAP al entrar en pantalla: las barras crecen desde la base, las líneas se dibujan,
   los puntos aparecen. Sin GSAP o con movimiento reducido se dibuja quieta.

   Dash escribe cada gráfica como <div class="sg" data-spec="{…}">; figuras.py arma la especificación.
   Tipos: barras, barras_h, lineas, xy, tiras, dispersion, calor.
   ========================================================================== */
(function () {
  'use strict';

  const NS = 'http://www.w3.org/2000/svg';
  const reducir = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const anim = () => (!reducir && window.gsap ? window.gsap : null);

  // Punto decimal y espacio de miles, como en el artículo
  const fmt = (v, dec = 0) => {
    if (v == null || Number.isNaN(v)) return 'sin dato';
    const s = Math.abs(v).toFixed(dec).split('.');
    return (v < 0 ? '−' : '') + s[0].replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + (s[1] ? '.' + s[1] : '');
  };
  const valor = (spec, v, dec) => {
    const d = dec != null ? dec : (spec.dec != null ? spec.dec : 0);
    if (v == null) return 'sin dato';
    return spec.pct ? fmt(100 * v, d) + ' %' : fmt(v, d) + (spec.unidad ? ' ' + spec.unidad : '');
  };
  const eje = (spec, v, paso) => {
    const d = paso < 1 ? Math.min(3, Math.ceil(-Math.log10(paso))) : 0;
    return spec.pct ? fmt(100 * v, Math.max(0, d - 2)) + ' %' : fmt(v, d);
  };

  const el = (tag, attrs = {}, padre) => {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) if (attrs[k] != null) n.setAttribute(k, attrs[k]);
    if (padre) padre.append(n);
    return n;
  };
  // Marcas "redondas" para el eje: 1, 2, 2.5 o 5 por potencia de diez
  function marcas(min, max, n = 5) {
    if (min === max) { min -= 1; max += 1; }
    const crudo = (max - min) / n;
    const mag = Math.pow(10, Math.floor(Math.log10(crudo)));
    const paso = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= crudo);
    const lo = Math.floor(min / paso + 1e-9) * paso, hi = Math.ceil(max / paso - 1e-9) * paso;
    const out = [];
    for (let v = lo; v <= hi + paso / 2; v += paso) out.push(+v.toFixed(10));
    return { ticks: out, paso };
  }
  const ancho = (txt, px = 12) => String(txt).length * px * 0.56;

  // ------------------------------------------------------------------------
  // Tarjeta: leyenda, área del gráfico, tooltip y tabla accesible
  // ------------------------------------------------------------------------
  function montar(raiz) {
    if (raiz._sg) return;
    let spec;
    try { spec = JSON.parse(raiz.getAttribute('data-spec')); } catch (e) { return; }
    raiz._sg = { spec, ocultas: new Set(), rango: 0, animada: false };
    raiz.textContent = '';
    const leyenda = document.createElement('div');
    leyenda.className = 'sg-leyenda';
    const herramientas = document.createElement('div');
    herramientas.className = 'sg-herramientas';
    const plot = document.createElement('div');
    plot.className = 'sg-plot';
    plot.tabIndex = 0;
    plot.setAttribute('role', 'img');
    plot.setAttribute('aria-label', (spec.titulo || 'Gráfica') + '. Use las flechas para recorrer los valores.');
    raiz.append(herramientas, leyenda, plot);
    raiz._sg.nodos = { leyenda, herramientas, plot };
    armarLeyenda(raiz);
    armarRangos(raiz);
    dibujar(raiz, false);
    const g = anim();
    if (g && 'IntersectionObserver' in window) {
      const io = new IntersectionObserver(([e]) => {
        if (e.isIntersecting && !raiz._sg.animada) { io.disconnect(); raiz._sg.animada = true; dibujar(raiz, true); }
      }, { threshold: 0.2 });
      io.observe(raiz);
    }
  }

  function series(spec) { return spec.series || []; }

  function armarLeyenda(raiz) {
    const { spec, ocultas, nodos } = raiz._sg;
    nodos.leyenda.textContent = '';
    const alternables = ['barras', 'barras_h', 'lineas', 'xy', 'dispersion'].includes(spec.tipo) && series(spec).length > 1;
    series(spec).forEach((s) => {
      if (s.sin_leyenda) return;
      const b = document.createElement(alternables ? 'button' : 'span');
      b.className = 'lg-btn' + (alternables ? '' : ' fijo');
      if (alternables) b.type = 'button';
      b.innerHTML = '<i></i><span></span>';
      const i = b.querySelector('i');
      i.style.background = s.color;
      if (s.guion) i.classList.add('guion');
      b.querySelector('span').textContent = s.nombre;
      if (alternables) {
        b.setAttribute('aria-pressed', String(!ocultas.has(s.nombre)));
        b.addEventListener('click', () => {
          const visibles = series(spec).filter((x) => !ocultas.has(x.nombre));
          if (!ocultas.has(s.nombre) && visibles.length === 1) return;   // siempre queda una serie
          if (ocultas.has(s.nombre)) ocultas.delete(s.nombre); else ocultas.add(s.nombre);
          b.setAttribute('aria-pressed', String(!ocultas.has(s.nombre)));
          dibujar(raiz, true);
        });
      }
      nodos.leyenda.append(b);
    });
    (spec.refs || []).concat(spec.leyenda_extra || []).forEach((r) => {
      const b = document.createElement('span');
      b.className = 'lg-btn fijo';
      b.innerHTML = '<i></i><span></span>';
      const i = b.querySelector('i');
      i.style.background = r.color || 'var(--marino)';
      if (r.guion !== false && !r.cuadro) i.classList.add('linea');
      b.querySelector('span').textContent = r.nombre;
      nodos.leyenda.append(b);
    });
  }

  function armarRangos(raiz) {
    const { spec, nodos } = raiz._sg;
    nodos.herramientas.textContent = '';
    if (!spec.rangos || spec.rangos.length < 2) return;
    const seg = document.createElement('div');
    seg.className = 'segmentado';
    seg.setAttribute('role', 'group');
    seg.setAttribute('aria-label', 'Periodo');
    spec.rangos.forEach((r, k) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = r.etiqueta;
      b.setAttribute('aria-pressed', String(k === raiz._sg.rango));
      b.addEventListener('click', () => {
        raiz._sg.rango = k;
        seg.querySelectorAll('button').forEach((x, j) => x.setAttribute('aria-pressed', String(j === k)));
        dibujar(raiz, true);
      });
      seg.append(b);
    });
    nodos.herramientas.append(seg);
  }

  // ------------------------------------------------------------------------
  // Dibujo
  // ------------------------------------------------------------------------
  function dibujar(raiz, animar) {
    const { spec, nodos } = raiz._sg;
    const plot = nodos.plot;
    const W = Math.max(300, Math.round(plot.clientWidth || raiz.clientWidth || 640));
    const H = spec.alto || 320;
    plot.textContent = '';
    const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, class: 'sg-svg', 'aria-hidden': 'true', focusable: 'false' }, plot);
    const tip = document.createElement('div');
    tip.className = 'sg-tip';
    tip.hidden = true;
    plot.append(tip);
    const ctx = { raiz, spec, svg, tip, plot, W, H, animar: animar && anim(), g: anim() };
    const tipos = { barras, barras_h: barrasH, lineas, xy, tiras, dispersion, calor };
    (tipos[spec.tipo] || barras)(ctx);
    tablaAccesible(ctx);
  }

  function visibles(ctx) { return series(ctx.spec).filter((s) => !ctx.raiz._sg.ocultas.has(s.nombre)); }

  // Tooltip con título y filas (color, nombre, valor), anclado junto al cursor
  function mostrar(ctx, titulo, filas, ax, ay) {
    const { tip, plot, W } = ctx;
    tip.innerHTML = '';
    const t = document.createElement('p');
    t.className = 'sg-tip-titulo';
    t.textContent = titulo;
    tip.append(t);
    filas.forEach(([color, nombre, texto]) => {
      const r = document.createElement('p');
      r.className = 'sg-tip-fila';
      r.innerHTML = '<i></i><span></span><b></b>';
      r.querySelector('i').style.background = color;
      r.querySelector('span').textContent = nombre;
      r.querySelector('b').textContent = texto;
      tip.append(r);
    });
    tip.hidden = false;
    const caja = plot.getBoundingClientRect();
    const k = caja.width / W;
    const x = ax * k, tw = tip.offsetWidth;
    tip.style.left = Math.max(0, x + 14 + tw > caja.width ? x - 14 - tw : x + 14) + 'px';
    tip.style.top = Math.max(0, Math.min((ay != null ? ay * k : 8) - 20, caja.height - tip.offsetHeight)) + 'px';
  }

  // Rejilla horizontal y etiquetas del eje y (o del eje x en barras horizontales)
  function rejillaY(ctx, M, y0, y1, paso, Y) {
    const g = el('g', { class: 'grid' }, ctx.svg);
    marcasEnRango(y0, y1, paso).forEach((t) => {
      el('line', { x1: M.l, x2: ctx.W - M.r, y1: Y(t), y2: Y(t), class: Math.abs(t) < 1e-12 ? 'zero' : '' }, g);
      el('text', { x: M.l - 8, y: Y(t) + 4, class: 'ylab' }, g).textContent = eje(ctx.spec, t, paso);
    });
    const ty = ctx.spec.eje_y && ctx.spec.eje_y.titulo;
    if (ty) el('text', { x: 12, y: M.t + (ctx.H - M.t - M.b) / 2, class: 'ytitle',
                         transform: `rotate(-90 12 ${M.t + (ctx.H - M.t - M.b) / 2})` }, ctx.svg).textContent = ty;
  }
  function marcasEnRango(a, b, paso) {
    const out = [];
    for (let v = Math.ceil(a / paso - 1e-9) * paso; v <= b + paso / 1e6; v += paso) out.push(+v.toFixed(10));
    return out;
  }
  function rangoY(ctx, valores, refsY) {
    const e = ctx.spec.eje_y || {};
    let lo = e.min != null ? e.min : Math.min(0, ...valores, ...refsY);
    let hi = e.max != null ? e.max : Math.max(...valores, ...refsY, 0);
    if (e.max == null) hi += (hi - lo) * (ctx.spec.valores === false ? 0.04 : 0.14);   // aire para las etiquetas
    const { paso } = marcas(lo, hi);
    if (e.min == null) lo = Math.floor(lo / paso + 1e-9) * paso;
    if (e.max == null) hi = Math.ceil(hi / paso - 1e-9) * paso;
    return { lo, hi, paso };
  }

  function refsH(ctx, M, Y, X) {
    (ctx.spec.refs || []).forEach((r) => {
      if (r.eje === 'x' && X) {
        const x = X(r.valor);
        el('line', { x1: x, x2: x, y1: M.t, y2: ctx.H - M.b, class: 'ref' + (r.guion === false ? '' : ' guion'),
                     style: `stroke:${r.color || 'var(--marino)'}` }, ctx.svg);
      } else if (r.eje !== 'x' && Y) {
        const y = Y(r.valor);
        el('line', { x1: M.l, x2: ctx.W - M.r, y1: y, y2: y, class: 'ref' + (r.guion === false ? '' : ' guion'),
                     style: `stroke:${r.color || 'var(--marino)'}` }, ctx.svg);
      }
    });
  }

  // ---------- Barras verticales (agrupadas) ----------
  function barras(ctx) {
    const { spec, svg, W, H } = ctx;
    const S = visibles(ctx), cats = spec.categorias, n = cats.length;
    const largas = spec.categorias.some((c) => ancho(c, 12) > (W - 72) / spec.categorias.length - 6);
    const M = { l: 58, r: 14, t: 14, b: (spec.sub ? 58 : 46) + (largas ? 18 : 0) };
    const vals = S.flatMap((s) => s.datos.map((v, i) => v + (s.error ? s.error[i] || 0 : 0))).filter((v) => v != null);
    const { lo, hi, paso } = rangoY(ctx, vals, (spec.refs || []).filter((r) => r.eje !== 'x').map((r) => r.valor));
    const Y = (v) => M.t + (H - M.t - M.b) * (1 - (v - lo) / (hi - lo));
    const banda = (W - M.l - M.r) / n, CX = (i) => M.l + banda * (i + 0.5);
    rejillaY(ctx, M, lo, hi, paso, Y);
    const gx = el('g', { class: 'xaxis' }, svg);
    // etiqueta larga: primero en dos renglones; solo si aún no cabe, se rota
    const partir = (c) => {
      const p = String(c).split(' ');
      if (p.length < 2) return [String(c)];
      let mejor = null;
      for (let k = 1; k < p.length; k++) {
        const l = [p.slice(0, k).join(' '), p.slice(k).join(' ')];
        if (!mejor || Math.max(...l.map((x) => x.length)) < Math.max(...mejor.map((x) => x.length))) mejor = l;
      }
      return mejor;
    };
    const lineasCat = cats.map((c) => (ancho(c, 12) > banda - 6 ? partir(c) : [String(c)]));
    const rotar = lineasCat.some((l) => l.some((x) => ancho(x, 12) > banda - 4));
    cats.forEach((c, i) => {
      const t = el('text', { x: CX(i), y: H - M.b + 18, class: 'xlab' + (rotar ? ' rot' : '') }, gx);
      if (rotar) {
        t.textContent = c;
        t.setAttribute('transform', `rotate(-28 ${CX(i)} ${H - M.b + 14})`); t.setAttribute('text-anchor', 'end');
      } else {
        lineasCat[i].forEach((x, k) => { el('tspan', { x: CX(i), dy: k ? 14 : 0 }, t).textContent = x; });
      }
      const dosLineas = !rotar && lineasCat.some((l) => l.length > 1);
      if (spec.sub && !rotar) el('text', { x: CX(i), y: H - M.b + (dosLineas ? 47 : 33), class: 'xsub' }, gx).textContent = spec.sub[i];
    });
    if (spec.eje_x && spec.eje_x.titulo) el('text', { x: (M.l + W - M.r) / 2, y: H - 4, class: 'xtitle' }, gx).textContent = spec.eje_x.titulo;
    const hl = el('rect', { class: 'hl', y: M.t, height: H - M.t - M.b, width: banda, x: -999 }, svg);
    const g = el('g', { class: 'data' }, svg);
    const base = Y(Math.max(lo, Math.min(0, hi)));
    const interior = banda * (S.length > 1 ? 0.8 : 0.62), bw = interior / S.length;
    S.forEach((s, si) => s.datos.forEach((v, i) => {
      if (v == null) return;
      const x = CX(i) - interior / 2 + si * bw + 1, y = Math.min(Y(v), base), h = Math.max(Math.abs(Y(v) - base), 1);
      const color = (s.colores && s.colores[i]) || s.color;
      const r = el('rect', { x, y, width: Math.max(bw - 2, 2), height: h, rx: 4, style: `fill:${color}` }, g);
      if (ctx.animar) ctx.g.from(r, { attr: { y: base, height: 0 }, duration: 0.7, ease: 'power3.out', delay: i * 0.04 + si * 0.08 });
      if (s.error && s.error[i]) {
        const cx = x + (bw - 2) / 2;
        el('line', { x1: cx, x2: cx, y1: Y(v - s.error[i]), y2: Y(v + s.error[i]), class: 'err' }, g);
      }
      if (spec.valores !== false && bw >= 14) {
        const lab = el('text', { x: x + (bw - 2) / 2, y: (v >= 0 ? y : y + h) + (v >= 0 ? -6 : 13), class: 'val' + (bw < 30 ? ' sm' : '') }, g);
        lab.textContent = (s.etiquetas && s.etiquetas[i]) || valor(spec, v, spec.dec_val);
        if (ctx.animar) ctx.g.from(lab, { opacity: 0, duration: 0.4, delay: 0.45 + i * 0.04 + si * 0.08 });
      }
    }));
    refsH(ctx, M, Y, (c) => CX(typeof c === 'number' ? c : cats.indexOf(c)));
    interaccionCategorias(ctx, n, (i) => {
      hl.setAttribute('x', CX(i) - banda / 2);
      const filas = S.map((s) => [(s.colores && s.colores[i]) || s.color, s.nombre, valor(spec, s.datos[i], spec.dec_tip)]);
      (spec.extra_tip || []).forEach((e) => filas.push(['transparent', e.nombre, e.datos[i]]));
      return [spec.titulos ? spec.titulos[i] : cats[i] + (spec.sub ? ' · ' + spec.sub[i] : ''), filas, CX(i)];
    }, (sx) => Math.floor((sx - M.l) / banda), () => hl.setAttribute('x', -999));
  }

  // ---------- Barras horizontales ----------
  function barrasH(ctx) {
    const { spec, svg, W, H } = ctx;
    const S = visibles(ctx), cats = spec.categorias, n = cats.length;
    const izq = Math.min(240, Math.max(...cats.map((c) => ancho(c, 12))) + 18);
    const M = { l: izq, r: 70, t: 8, b: spec.eje_x && spec.eje_x.titulo ? 42 : 28 };
    const vals = S.flatMap((s) => s.datos.map((v, i) => v + (s.error ? s.error[i] || 0 : 0))).filter((v) => v != null);
    const refsX = (spec.refs || []).filter((r) => r.eje === 'x').map((r) => r.valor);
    const e = spec.eje_x || {};
    let lo = e.min != null ? e.min : Math.min(0, ...vals);
    let hi = e.max != null ? e.max : Math.max(...vals, ...refsX);
    const { paso } = marcas(lo, hi);
    if (e.max == null) hi = Math.ceil(hi / paso - 1e-9) * paso;
    if (e.min == null) lo = Math.floor(lo / paso + 1e-9) * paso;
    const X = (v) => M.l + (W - M.l - M.r) * (v - lo) / (hi - lo);
    const banda = (H - M.t - M.b) / n, CY = (i) => M.t + banda * (i + 0.5);
    const gg = el('g', { class: 'grid' }, svg);
    marcasEnRango(lo, hi, paso).forEach((t) => {
      el('line', { x1: X(t), x2: X(t), y1: M.t, y2: H - M.b, class: Math.abs(t) < 1e-12 ? 'zero' : '' }, gg);
      el('text', { x: X(t), y: H - M.b + 16, class: 'xlab tenue' }, gg).textContent = eje(spec, t, paso);
    });
    if (e.titulo) el('text', { x: (M.l + W - M.r) / 2, y: H - 4, class: 'xtitle' }, svg).textContent = e.titulo;
    cats.forEach((c, i) => { el('text', { x: M.l - 10, y: CY(i) + 4, class: 'ycat' }, svg).textContent = c; });
    const hl = el('rect', { class: 'hl', x: M.l, width: W - M.l - M.r, height: banda, y: -999 }, svg);
    const g = el('g', { class: 'data' }, svg);
    const interior = banda * 0.7, bh = interior / Math.max(S.length, 1), base = X(Math.max(lo, 0));
    S.forEach((s, si) => s.datos.forEach((v, i) => {
      if (v == null) return;
      const y = CY(i) - interior / 2 + si * bh, x = Math.min(X(v), base), w = Math.max(Math.abs(X(v) - base), 1);
      const color = (s.colores && s.colores[i]) || s.color;
      const r = el('rect', { x, y, width: w, height: Math.max(bh - 2, 2), rx: 4, style: `fill:${color}` }, g);
      if (ctx.animar) ctx.g.from(r, { attr: { width: 0, x: base }, duration: 0.75, ease: 'power3.out', delay: i * 0.04 });
      if (s.error && s.error[i]) {
        el('line', { x1: X(v - s.error[i]), x2: X(v + s.error[i]), y1: y + (bh - 2) / 2, y2: y + (bh - 2) / 2, class: 'err' }, g);
      }
      if (spec.valores !== false) {
        const fin = Math.max(X(v), s.error ? X(v + (s.error[i] || 0)) : X(v));
        const lab = el('text', { x: fin + 6, y: y + (bh - 2) / 2 + 4, class: 'val izq' }, g);
        lab.textContent = (s.etiquetas && s.etiquetas[i]) || valor(spec, v, spec.dec_val);
        if (ctx.animar) ctx.g.from(lab, { opacity: 0, duration: 0.4, delay: 0.5 + i * 0.04 });
      }
    }));
    refsH(ctx, M, null, X);
    interaccionCategorias(ctx, n, (i) => {
      hl.setAttribute('y', CY(i) - banda / 2);
      const filas = S.map((s) => [(s.colores && s.colores[i]) || s.color, s.nombre, valor(spec, s.datos[i], spec.dec_tip)]);
      (spec.extra_tip || []).forEach((x) => filas.push(['transparent', x.nombre, x.datos[i]]));
      return [spec.titulos ? spec.titulos[i] : cats[i], filas, X(Math.max(...S.map((s) => s.datos[i] || 0))), CY(i)];
    }, null, () => hl.setAttribute('y', -999), (sx, sy) => Math.floor((sy - M.t) / banda));
  }

  // ---------- Líneas sobre categorías (años) ----------
  function lineas(ctx) {
    const { spec, svg, W, H } = ctx;
    const S = visibles(ctx), cats = spec.categorias, n = cats.length;
    const M = { l: 58, r: 18, t: 18, b: 42 };
    const vals = S.flatMap((s) => s.datos).filter((v) => v != null);
    const e = spec.eje_y || {};
    const pad = (Math.max(...vals) - Math.min(...vals)) * 0.25 || 0.05;
    const lo0 = e.min != null ? e.min : Math.min(...vals) - pad, hi0 = e.max != null ? e.max : Math.max(...vals) + pad;
    const { paso } = marcas(lo0, hi0);
    const lo = Math.floor(lo0 / paso) * paso, hi = Math.ceil(hi0 / paso) * paso;
    const Y = (v) => M.t + (H - M.t - M.b) * (1 - (v - lo) / (hi - lo));
    const banda = (W - M.l - M.r) / n, CX = (i) => M.l + banda * (i + 0.5);
    rejillaY(ctx, M, lo, hi, paso, Y);
    cats.forEach((c, i) => { el('text', { x: CX(i), y: H - M.b + 18, class: 'xlab' }, svg).textContent = c; });
    if (spec.eje_x && spec.eje_x.titulo) el('text', { x: (M.l + W - M.r) / 2, y: H - 4, class: 'xtitle' }, svg).textContent = spec.eje_x.titulo;
    const hl = el('rect', { class: 'hl', y: M.t, height: H - M.t - M.b, width: banda, x: -999 }, svg);
    const g = el('g', { class: 'data' }, svg);
    S.forEach((s, si) => {
      const pts = s.datos.map((v, i) => [CX(i), Y(v)]);
      const p = el('path', { d: 'M' + pts.map((q) => q.join(' ')).join('L'), class: 'ln', pathLength: 1, style: `stroke:${s.color}` }, g);
      if (ctx.animar) ctx.g.fromTo(p, { strokeDasharray: 1, strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 1.1, ease: 'power2.inOut', delay: si * 0.12 });
      pts.forEach(([x, y], i) => {
        const d = el('circle', { cx: x, cy: y, r: 4.5, class: 'pt', style: `fill:${s.color}` }, g);
        if (ctx.animar) ctx.g.from(d, { attr: { r: 0 }, duration: 0.35, ease: 'back.out(2)', delay: 0.35 + i * 0.06 + si * 0.12 });
        if (spec.valores !== false) {
          const otra = S.find((o) => o !== s && Math.abs(Y(o.datos[i]) - y) < 16);
          const arriba = !otra || s.datos[i] >= otra.datos[i];
          el('text', { x, y: arriba ? y - 10 : y + 18, class: 'val sm' }, g).textContent = valor(spec, s.datos[i], spec.dec_val);
        }
      });
    });
    interaccionCategorias(ctx, n, (i) => {
      hl.setAttribute('x', CX(i) - banda / 2);
      return [cats[i], S.map((s) => [s.color, s.nombre, valor(spec, s.datos[i], spec.dec_tip)]), CX(i)];
    }, (sx) => Math.floor((sx - M.l) / banda), () => hl.setAttribute('x', -999));
  }

  // ---------- Curvas x-y (ROC, costo, calibración, serie semanal) ----------
  function xy(ctx) {
    const { spec, svg, W, H } = ctx;
    const S = visibles(ctx);
    const M = { l: 60, r: 22, t: 16, b: 46 };
    const ex = spec.eje_x || {}, ey = spec.eje_y || {};
    const rango = spec.rangos ? spec.rangos[ctx.raiz._sg.rango] : null;
    const allX = S.flatMap((s) => s.x);
    let x0 = rango ? rango.x0 : (ex.min != null ? ex.min : Math.min(...allX));
    let x1 = rango ? rango.x1 : (ex.max != null ? ex.max : Math.max(...allX));
    const enRango = (s) => s.y.filter((v, i) => s.x[i] >= x0 && s.x[i] <= x1 && v != null);
    const vy = S.flatMap(enRango);
    let y0 = ey.min != null ? ey.min : Math.min(0, ...vy), y1 = ey.max != null ? ey.max : Math.max(...vy);
    if (ey.max == null) y1 += (y1 - y0) * 0.08;
    const my = marcas(y0, y1), mx = marcas(x0, x1, 6);
    if (ey.min == null) y0 = Math.floor(y0 / my.paso) * my.paso;
    if (ey.max == null) y1 = Math.ceil(y1 / my.paso) * my.paso;
    const X = (v) => M.l + (W - M.l - M.r) * (v - x0) / (x1 - x0);
    const Y = (v) => M.t + (H - M.t - M.b) * (1 - (v - y0) / (y1 - y0));
    (spec.bandas || []).forEach((b) => {
      const a = Math.max(x0, b.x0), z = Math.min(x1, b.x1);
      if (z <= a) return;
      el('rect', { x: X(a), y: M.t, width: X(z) - X(a), height: H - M.t - M.b, class: 'banda' }, svg);
      el('text', { x: X(a) + 6, y: M.t + 14, class: 'banda-lab' }, svg).textContent = b.etiqueta;
    });
    rejillaY(ctx, M, y0, y1, my.paso, Y);
    const gx = el('g', { class: 'grid' }, svg);
    if (spec.ticks_x) {
      spec.ticks_x.filter((t) => t.x >= x0 && t.x <= x1).forEach((t) => {
        el('line', { x1: X(t.x), x2: X(t.x), y1: M.t, y2: H - M.b, class: 'v' }, gx);
        el('text', { x: X(t.x) + 4, y: H - M.b + 16, class: 'xlab tenue izq' }, gx).textContent = t.etiqueta;
      });
    } else {
      marcasEnRango(x0, x1, mx.paso).forEach((t) => {
        el('text', { x: X(t), y: H - M.b + 16, class: 'xlab tenue' }, gx).textContent =
          spec.pct_x ? fmt(100 * t, 0) + ' %' : fmt(t, mx.paso < 1 ? Math.min(2, Math.ceil(-Math.log10(mx.paso))) : 0);
      });
    }
    if (ex.titulo) el('text', { x: (M.l + W - M.r) / 2, y: H - 4, class: 'xtitle' }, svg).textContent = ex.titulo;
    refsH(ctx, M, Y, X);
    const clip = 'c' + Math.random().toString(36).slice(2);
    const defs = el('defs', {}, svg);
    const cp = el('clipPath', { id: clip }, defs);
    el('rect', { x: M.l, y: M.t - 4, width: W - M.l - M.r, height: H - M.t - M.b + 8 }, cp);
    const g = el('g', { class: 'data', 'clip-path': `url(#${clip})` }, svg);
    S.forEach((s, si) => {
      const idx = s.x.map((_, i) => i).filter((i) => s.y[i] != null);
      if (s.relleno) {
        const area = 'M' + X(s.x[idx[0]]) + ' ' + Y(y0) + idx.map((i) => 'L' + X(s.x[i]) + ' ' + Y(s.y[i])).join('') + 'L' + X(s.x[idx[idx.length - 1]]) + ' ' + Y(y0) + 'Z';
        const a = el('path', { d: area, class: 'area', style: `fill:${s.color}` }, g);
        if (ctx.animar) ctx.g.from(a, { opacity: 0, duration: 0.9, delay: 0.4 });
      }
      const d = 'M' + idx.map((i) => X(s.x[i]) + ' ' + Y(s.y[i])).join('L');
      const p = el('path', { d, class: 'ln' + (s.guion ? ' guion' : ''), pathLength: s.guion ? null : 1,
                             style: `stroke:${s.color};stroke-width:${s.ancho || 2.5}px` }, g);
      if (ctx.animar && !s.guion) ctx.g.fromTo(p, { strokeDasharray: 1, strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 1.2, ease: 'power2.inOut', delay: si * 0.1 });
      else if (ctx.animar) ctx.g.from(p, { opacity: 0, duration: 0.6, delay: 0.3 + si * 0.1 });
      if (s.puntos) idx.forEach((i, k) => {
        const c = el('circle', { cx: X(s.x[i]), cy: Y(s.y[i]), r: 4.5, class: 'pt', style: `fill:${s.color}` }, g);
        if (ctx.animar) ctx.g.from(c, { attr: { r: 0 }, duration: 0.35, ease: 'back.out(2)', delay: 0.5 + k * 0.05 });
        if (s.etiquetas) el('text', { x: X(s.x[i]) - 8, y: Y(s.y[i]) - 9, class: 'val sm der' }, g).textContent = s.etiquetas[k];
      });
    });
    (spec.marcas_xy || []).forEach((m) => {
      const x = X(m.x), y = Y(m.y);
      const dm = el('path', { d: `M${x} ${y - 8}L${x + 8} ${y}L${x} ${y + 8}L${x - 8} ${y}Z`, class: 'mk', style: m.color ? `fill:${m.color}` : null }, svg);
      el('text', { x: x + 12, y: y - 10, class: 'mk-lab' }, svg).textContent = m.etiqueta;
      if (ctx.animar) ctx.g.from(dm, { scale: 0, transformOrigin: '50% 50%', duration: 0.45, ease: 'back.out(2)', delay: 0.9 });
    });
    const guia = el('line', { class: 'guia', y1: M.t, y2: H - M.b, x1: -9, x2: -9 }, svg);
    const gp = el('g', {}, svg);
    function cercano(s, xv) {
      let best = -1, dist = Infinity;
      for (let i = 0; i < s.x.length; i++) { const dd = Math.abs(s.x[i] - xv); if (dd < dist && s.y[i] != null) { dist = dd; best = i; } }
      return best;
    }
    const mostrarEn = (xv, ay) => {
      xv = Math.max(x0, Math.min(x1, xv));
      guia.setAttribute('x1', X(xv)); guia.setAttribute('x2', X(xv));
      gp.textContent = '';
      const filas = [];
      S.filter((s) => !s.sin_tip).forEach((s) => {
        const i = cercano(s, xv);
        if (i < 0) return;
        el('circle', { cx: X(s.x[i]), cy: Y(s.y[i]), r: 4.5, class: 'pt', style: `fill:${s.color}` }, gp);
        filas.push([s.color, s.nombre, valor(spec, s.y[i], spec.dec_tip)]);
      });
      const titulo = spec.etiquetas_x ? spec.etiquetas_x[Math.round(xv - (spec.etiquetas_x0 || 0))] || '' :
        (spec.titulo_x || '') + (spec.pct_x ? fmt(100 * xv, 1) + ' %' : fmt(xv, spec.dec_x != null ? spec.dec_x : 2));
      mostrar(ctx, titulo, filas, X(xv), ay);
    };
    const ocultar = () => { ctx.tip.hidden = true; guia.setAttribute('x1', -9); guia.setAttribute('x2', -9); gp.textContent = ''; };
    let cur = null;
    ctx.plot.onpointermove = (ev) => {
      const caja = ctx.plot.getBoundingClientRect(), k = W / caja.width;
      const sx = (ev.clientX - caja.left) * k;
      cur = x0 + (x1 - x0) * (sx - M.l) / (W - M.l - M.r);
      mostrarEn(cur, (ev.clientY - caja.top) * k);
    };
    ctx.plot.onpointerleave = ocultar;
    ctx.plot.onblur = ocultar;
    ctx.plot.onkeydown = (ev) => {
      if (!['ArrowLeft', 'ArrowRight', 'Escape'].includes(ev.key)) return;
      ev.preventDefault();
      if (ev.key === 'Escape') return ocultar();
      const paso = (x1 - x0) / 40;
      cur = cur == null ? x0 : cur + (ev.key === 'ArrowRight' ? paso : -paso);
      mostrarEn(cur);
    };
  }

  // ---------- Tiras: un modelo por fila, sus pliegues, la media y una desviación ----------
  function tiras(ctx) {
    const { spec, svg, W, H } = ctx;
    const F = spec.filas, n = F.length;
    const izq = Math.min(220, Math.max(...F.map((f) => ancho(f.nombre, 12.5))) + 22);
    const M = { l: izq, r: 64, t: 10, b: 42 };
    const vals = F.flatMap((f) => f.valores);
    const pad = (Math.max(...vals) - Math.min(...vals)) * 0.06;
    const { paso } = marcas(Math.min(...vals) - pad, Math.max(...vals) + pad);
    const lo = Math.floor((Math.min(...vals) - pad) / paso) * paso, hi = Math.ceil((Math.max(...vals) + pad) / paso) * paso;
    const X = (v) => M.l + (W - M.l - M.r) * (v - lo) / (hi - lo);
    const banda = (H - M.t - M.b) / n, CY = (i) => M.t + banda * (i + 0.5);
    const gg = el('g', { class: 'grid' }, svg);
    marcasEnRango(lo, hi, paso).forEach((t) => {
      el('line', { x1: X(t), x2: X(t), y1: M.t, y2: H - M.b }, gg);
      el('text', { x: X(t), y: H - M.b + 16, class: 'xlab tenue' }, gg).textContent = fmt(t, Math.min(3, Math.ceil(-Math.log10(paso))));
    });
    if (spec.eje_x && spec.eje_x.titulo) el('text', { x: (M.l + W - M.r) / 2, y: H - 4, class: 'xtitle' }, svg).textContent = spec.eje_x.titulo;
    const hl = el('rect', { class: 'hl', x: M.l, width: W - M.l - M.r, height: banda, y: -999 }, svg);
    const g = el('g', { class: 'data' }, svg);
    F.forEach((f, i) => {
      el('text', { x: M.l - 12, y: CY(i) + 4, class: 'ycat' + (f.elegido ? ' fuerte' : '') }, svg).textContent = f.nombre;
      const rango = el('line', { x1: X(f.media - f.de), x2: X(f.media + f.de), y1: CY(i), y2: CY(i), class: 'rango', style: `stroke:${f.color}` }, g);
      if (ctx.animar) ctx.g.from(rango, { attr: { x1: X(f.media), x2: X(f.media) }, duration: 0.7, ease: 'power3.out', delay: i * 0.06 });
      f.valores.forEach((v, j) => {
        const c = el('circle', { cx: X(v), cy: CY(i), r: 5, class: 'pt suave', style: `fill:${f.color}` }, g);
        if (ctx.animar) ctx.g.from(c, { attr: { cx: X(f.media) }, opacity: 0, duration: 0.6, ease: 'power3.out', delay: 0.2 + i * 0.06 + j * 0.03 });
      });
      const x = X(f.media), y = CY(i), r = f.elegido ? 9 : 7;
      const dm = el('path', { d: `M${x} ${y - r}L${x + r} ${y}L${x} ${y + r}L${x - r} ${y}Z`, class: 'mk' + (f.elegido ? ' elegido' : ''), style: `fill:${f.color}` }, g);
      if (ctx.animar) ctx.g.from(dm, { scale: 0, transformOrigin: '50% 50%', duration: 0.4, ease: 'back.out(2)', delay: 0.6 + i * 0.06 });
      el('text', { x: Math.max(...f.valores, f.media + f.de) > hi - (hi - lo) * 0.1 ? X(f.media) : X(Math.max(...f.valores, f.media + f.de)) + 10,
                   y: Math.max(...f.valores, f.media + f.de) > hi - (hi - lo) * 0.1 ? y - 11 : y + 4,
                   class: 'val' + (Math.max(...f.valores, f.media + f.de) > hi - (hi - lo) * 0.1 ? '' : ' izq') }, g).textContent = fmt(f.media, 3);
    });
    interaccionCategorias(ctx, n, (i) => {
      const f = F[i];
      hl.setAttribute('y', CY(i) - banda / 2);
      const filas = f.valores.map((v, j) => [f.color, 'Pliegue ' + (j + 1), fmt(v, 4)]);
      filas.push(['transparent', 'Media', fmt(f.media, 4)], ['transparent', 'Desviación típica', fmt(f.de, 4)]);
      return [f.nombre + (f.elegido ? ' (elegido)' : ''), filas, X(f.media + f.de), CY(i)];
    }, null, () => hl.setAttribute('y', -999), (sx, sy) => Math.floor((sy - M.t) / banda));
  }

  // ---------- Dispersión (mapa del ACP) ----------
  function dispersion(ctx) {
    const { spec, svg, W, H } = ctx;
    const S = visibles(ctx);
    const M = { l: 56, r: 16, t: 12, b: 44 };
    const xs = S.flatMap((s) => s.x), ys = S.flatMap((s) => s.y);
    const mx = marcas(Math.min(...xs), Math.max(...xs), 6), my = marcas(Math.min(...ys), Math.max(...ys));
    const x0 = mx.ticks[0], x1 = mx.ticks[mx.ticks.length - 1], y0 = my.ticks[0], y1 = my.ticks[my.ticks.length - 1];
    const X = (v) => M.l + (W - M.l - M.r) * (v - x0) / (x1 - x0);
    const Y = (v) => M.t + (H - M.t - M.b) * (1 - (v - y0) / (y1 - y0));
    rejillaY(ctx, M, y0, y1, my.paso, Y);
    mx.ticks.forEach((t) => { el('text', { x: X(t), y: H - M.b + 16, class: 'xlab tenue' }, svg).textContent = fmt(t, mx.paso < 1 ? 1 : 0); });
    if (spec.eje_x && spec.eje_x.titulo) el('text', { x: (M.l + W - M.r) / 2, y: H - 4, class: 'xtitle' }, svg).textContent = spec.eje_x.titulo;
    const g = el('g', { class: 'data' }, svg);
    const todos = [];
    S.forEach((s, si) => s.x.forEach((x, i) => {
      const c = el('circle', { cx: X(x), cy: Y(s.y[i]), r: 3.4, class: 'disp', style: `fill:${s.color}` }, g);
      todos.push([X(x), Y(s.y[i]), s, i]);
      if (ctx.animar && i % 3 === 0) ctx.g.from(c, { attr: { r: 0 }, duration: 0.4, delay: 0.002 * i + si * 0.15 });
    }));
    const marca = el('circle', { r: 7, class: 'disp-hl', cx: -20, cy: -20 }, svg);
    ctx.plot.onpointermove = (ev) => {
      const caja = ctx.plot.getBoundingClientRect(), k = W / caja.width;
      const sx = (ev.clientX - caja.left) * k, sy = (ev.clientY - caja.top) * k;
      let best = null, d = 196;
      todos.forEach((p) => { const dd = (p[0] - sx) ** 2 + (p[1] - sy) ** 2; if (dd < d) { d = dd; best = p; } });
      if (!best) { ctx.tip.hidden = true; marca.setAttribute('cx', -20); return; }
      marca.setAttribute('cx', best[0]); marca.setAttribute('cy', best[1]);
      mostrar(ctx, best[2].nombre, [[best[2].color, 'Componente 1', fmt(best[2].x[best[3]], 2)],
                                     [best[2].color, 'Componente 2', fmt(best[2].y[best[3]], 2)]], best[0], best[1]);
    };
    ctx.plot.onpointerleave = () => { ctx.tip.hidden = true; marca.setAttribute('cx', -20); };
  }

  // ---------- Mapa de calor (PSI, matriz de la prueba) ----------
  function calor(ctx) {
    const { spec, svg, W } = ctx;
    const filas = spec.filas, cols = spec.columnas;
    const izq = Math.min(240, Math.max(...filas.map((f) => ancho(f, 12))) + 18);
    const M = { l: izq, r: 12, t: 30, b: 10 };
    const H = ctx.H, cw = (W - M.l - M.r) / cols.length, ch = (H - M.t - M.b) / filas.length;
    const zmin = spec.zmin != null ? spec.zmin : Math.min(...spec.z.flat()), zmax = spec.zmax != null ? spec.zmax : Math.max(...spec.z.flat());
    const [c0, c1] = spec.escala;
    const mezcla = (t) => {
      const a = parseInt(c0.slice(1), 16), b = parseInt(c1.slice(1), 16);
      const ch_ = (s) => Math.round(((a >> s) & 255) + (((b >> s) & 255) - ((a >> s) & 255)) * t);
      return `rgb(${ch_(16)},${ch_(8)},${ch_(0)})`;
    };
    cols.forEach((c, j) => { el('text', { x: M.l + cw * (j + 0.5), y: M.t - 10, class: 'xlab' }, svg).textContent = c; });
    const hlr = el('rect', { class: 'calor-hl', width: cw - 4, height: ch - 4, x: -999, y: 0, rx: 8 }, svg);
    filas.forEach((f, i) => {
      el('text', { x: M.l - 10, y: M.t + ch * (i + 0.5) + 4, class: 'ycat' }, svg).textContent = f;
      cols.forEach((c, j) => {
        const z = spec.z[i][j], t = Math.max(0, Math.min(1, (z - zmin) / ((zmax - zmin) || 1)));
        const r = el('rect', { x: M.l + cw * j + 2, y: M.t + ch * i + 2, width: cw - 4, height: ch - 4, rx: 8, style: `fill:${mezcla(t)}` }, svg);
        if (ctx.animar) ctx.g.from(r, { opacity: 0, scale: 0.85, transformOrigin: '50% 50%', duration: 0.5, ease: 'power3.out', delay: (i + j) * 0.04 });
        const lineas_ = String(spec.texto[i][j]).split('\n');
        lineas_.forEach((txt, k) => {
          const tt = el('text', { x: M.l + cw * (j + 0.5), y: M.t + ch * (i + 0.5) + 4 + (k - (lineas_.length - 1) / 2) * 15,
                                  class: 'celda' + (k === 1 && lineas_.length === 3 ? ' fuerte' : '') }, svg);
          tt.textContent = txt;
          if (ctx.animar) ctx.g.from(tt, { opacity: 0, duration: 0.4, delay: 0.3 + (i + j) * 0.04 });
        });
      });
    });
    ctx.plot.onpointermove = (ev) => {
      const caja = ctx.plot.getBoundingClientRect(), k = W / caja.width;
      const sx = (ev.clientX - caja.left) * k, sy = (ev.clientY - caja.top) * k;
      const j = Math.floor((sx - M.l) / cw), i = Math.floor((sy - M.t) / ch);
      if (i < 0 || j < 0 || i >= filas.length || j >= cols.length) { ctx.tip.hidden = true; hlr.setAttribute('x', -999); return; }
      hlr.setAttribute('x', M.l + cw * j + 2); hlr.setAttribute('y', M.t + ch * i + 2);
      mostrar(ctx, `${filas[i]} · ${cols[j]}`, [['transparent', spec.nombre_z || 'Valor', String(spec.tip ? spec.tip[i][j] : spec.texto[i][j]).replace(/\n/g, ' · ')]],
              M.l + cw * (j + 1), M.t + ch * i);
    };
    ctx.plot.onpointerleave = () => { ctx.tip.hidden = true; hlr.setAttribute('x', -999); };
  }

  // Ratón y teclado para gráficas por categorías: resalta la columna (o fila) y muestra el tooltip
  function interaccionCategorias(ctx, n, datos, indiceX, ocultarExtra, indiceXY) {
    let cur = -1;
    const ver = (i, ay) => {
      cur = i;
      const [titulo, filas, ax, ay2] = datos(i);
      mostrar(ctx, titulo, filas, ax, ay != null ? ay : ay2);
    };
    const ocultar = () => { ctx.tip.hidden = true; cur = -1; ocultarExtra && ocultarExtra(); };
    ctx.plot.onpointermove = (ev) => {
      const caja = ctx.plot.getBoundingClientRect(), k = ctx.W / caja.width;
      const sx = (ev.clientX - caja.left) * k, sy = (ev.clientY - caja.top) * k;
      const i = indiceXY ? indiceXY(sx, sy) : indiceX(sx);
      if (i < 0 || i >= n) return ocultar();
      ver(i, indiceXY ? null : sy);
    };
    ctx.plot.onpointerleave = ocultar;
    ctx.plot.onblur = ocultar;
    ctx.plot.onkeydown = (ev) => {
      const sig = indiceXY ? ['ArrowDown', 'ArrowRight'] : ['ArrowRight', 'ArrowDown'];
      const ant = indiceXY ? ['ArrowUp', 'ArrowLeft'] : ['ArrowLeft', 'ArrowUp'];
      if (![...sig, ...ant, 'Home', 'End', 'Escape'].includes(ev.key)) return;
      ev.preventDefault();
      if (ev.key === 'Escape') return ocultar();
      const i = ev.key === 'Home' ? 0 : ev.key === 'End' ? n - 1 : Math.max(0, Math.min(n - 1, cur + (sig.includes(ev.key) ? 1 : -1)));
      ver(i);
    };
  }

  // Tabla accesible con los mismos datos (dentro de un div .sr-only para que no ensanche la página)
  function tablaAccesible(ctx) {
    const { spec } = ctx;
    const t = document.createElement('table');
    let cab = [], filas = [];
    if (spec.categorias) {
      const S = series(spec);
      cab = ['', ...S.map((s) => s.nombre)];
      filas = spec.categorias.map((c, i) => [c, ...S.map((s) => valor(spec, s.datos[i]))]);
    } else if (spec.tipo === 'tiras') {
      cab = ['Modelo', 'Media', 'Desviación típica'];
      filas = spec.filas.map((f) => [f.nombre, fmt(f.media, 4), fmt(f.de, 4)]);
    } else if (spec.tipo === 'calor') {
      cab = ['', ...spec.columnas];
      filas = spec.filas.map((f, i) => [f, ...spec.texto[i].map((x) => String(x).replace(/\n/g, ' '))]);
    } else {
      cab = ['Serie', 'Puntos'];
      filas = series(spec).map((s) => [s.nombre, String(s.x.length)]);
    }
    const tr = (cs, tag) => '<tr>' + cs.map((x) => `<${tag}>${x}</${tag}>`).join('') + '</tr>';
    t.innerHTML = `<caption>${spec.titulo || ''}</caption><thead>${tr(cab, 'th')}</thead><tbody>${filas.map((f) => tr(f, 'td')).join('')}</tbody>`;
    const envoltura = document.createElement('div');
    envoltura.className = 'sr-only';
    envoltura.append(t);
    ctx.plot.append(envoltura);
  }

  // ------------------------------------------------------------------------
  // Arranque: monta cada .sg que aparezca (Dash monta pestañas y callbacks después de cargar)
  // ------------------------------------------------------------------------
  function buscar(raiz) {
    if (raiz.matches && raiz.matches('.sg[data-spec]')) montar(raiz);
    if (raiz.querySelectorAll) raiz.querySelectorAll('.sg[data-spec]').forEach(montar);
  }
  function arrancar() {
    new MutationObserver((cambios) => cambios.forEach((c) => {
      c.addedNodes.forEach((n) => { if (n.nodeType === 1) buscar(n); });
      if (c.type === 'attributes' && c.target._sg) { c.target._sg = null; montar(c.target); }
    })).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['data-spec'] });
    buscar(document.body);
    let ultimo = window.innerWidth, espera = 0;
    window.addEventListener('resize', () => {
      cancelAnimationFrame(espera);
      espera = requestAnimationFrame(() => {
        if (Math.abs(window.innerWidth - ultimo) < 4) return;
        ultimo = window.innerWidth;
        document.querySelectorAll('.sg[data-spec]').forEach((r) => r._sg && dibujar(r, false));
      });
    });
    // al cambiar de pestaña el contenedor puede montarse con ancho cero: se redibuja cuando ya tiene ancho
    if ('ResizeObserver' in window) {
      const ro = new ResizeObserver((entradas) => entradas.forEach((e) => {
        const r = e.target;
        if (r._sg && e.contentRect.width > 0 && Math.abs(e.contentRect.width - (r._sg.w || 0)) > 4) {
          r._sg.w = e.contentRect.width;
          dibujar(r, false);
        }
      }));
      new MutationObserver(() => document.querySelectorAll('.sg[data-spec]').forEach((r) => { if (!r._ro) { r._ro = 1; ro.observe(r); } }))
        .observe(document.body, { childList: true, subtree: true });
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', arrancar);
  else arrancar();
})();
