(function () {
  'use strict';
  var MOCK = new URLSearchParams(location.search).get('mock') === '1';
  var TIPI = [['Carico', 'Carico'], ['Scarico', 'Scarico'], ['Sposta', 'Move'], ['Rettifica', 'Cng']]; // [etichetta, valore inviato]
  var LUOGHI = ['Casa', 'Cantina'];
  var ICON = {
    mov: '<path d="M5 12h14M12 5v14"/>',
    stock: '<path d="M4 7l8-4 8 4v10l-8 4-8-4z"/><path d="M4 7l8 4 8-4M12 11v10"/>',
    spesa: '<circle cx="9" cy="20" r="1.5"/><circle cx="18" cy="20" r="1.5"/><path d="M3 4h3l2.5 11h10L21 7H7"/>',
    bozze: '<path d="M4 13h4l2 3h4l2-3h4"/><path d="M5 13l2-8h10l2 8v6H5z"/>',
    appr: '<path d="M5 13l4 4L19 7"/>'
  };
  var TABS = [['mov', '+/-', 'Movimento +/-'], ['stock', 'Stock', 'Stock'], ['spesa', 'Spesa', 'Spesa'], ['bozze', 'Da inserire', 'Da inserire'], ['appr', 'Approvazioni', 'Approvazioni AI']];
  var $ = function (id) { return document.getElementById(id); };
  var st = { tipo: 'Carico', luogo: 'Casa', qta: 1, known: null, fotoBlob: null, stock: [], filtro: 'Tutti', tab: 'mov' };

  /* ---------- API (con mock) ---------- */
  var MOCKDB = {
    prod: { '8002795002995': { prodotto: 'Latte UHT intero', categoria: 'Dispensa', sottocategoria: 'Bevande' }, '8000500310427': { prodotto: 'Nutella 450 g', categoria: 'Dispensa', sottocategoria: 'Snack e Dolci' } },
    stock: [
      { nome: 'Latte fresco intero', categoria: 'Frigorifero', sotto: 'Latticini', tipo: 'Latte', luogo: 'Casa', qta: 3, minima: 1 },
      { nome: 'Burro', categoria: 'Frigorifero', sotto: 'Latticini', tipo: 'Burro', luogo: 'Casa', qta: 1, minima: 2 },
      { nome: 'Latte UHT intero', categoria: 'Dispensa', sotto: 'Bevande', tipo: 'Latte', luogo: 'Casa', qta: 6, minima: 2 },
      { nome: 'Pasta di semola', categoria: 'Dispensa', sotto: 'Pasta e riso', luogo: 'Casa', qta: 9, minima: 3 },
      { nome: 'Sale fino', categoria: 'Dispensa', sotto: 'Condimenti e Sale', luogo: 'Casa', qta: 2, minima: 1 },
      { nome: 'Acqua naturale', categoria: 'Cantina', sotto: 'Bevande', luogo: 'Cantina', qta: 12, minima: 6 },
      { nome: 'Birra', categoria: 'Cantina', sotto: 'Bevande', luogo: 'Cantina', qta: 8, minima: 0 }
    ],
    appr: [
      { id: 'P_1', titolo: 'Si & No Mais · sicura al 100%', prima: 'Dispensa › Snack e Dolci', dopo: 'Dispensa › Snack e Dolci · tipo Galletta', motivo: 'Snack a base di mais soffiato, classificabile come galletta.' },
      { id: 'P_2', titolo: "Latte UHT · sicura all'82%", prima: 'Dispensa › Bevande', dopo: 'Frigorifero › Latticini', motivo: 'Attenzione: il latte UHT chiuso resta in dispensa.' }
    ]
  };
  function mockApi(method, path, body) {
    var m;
    if (path === 'api/stock') return MOCKDB.stock;
    if ((m = /^api\/prodotto\/(.+)$/.exec(path))) { var p = MOCKDB.prod[decodeURIComponent(m[1])]; return p ? Object.assign({ found: true }, p) : { found: false }; }
    if (path === 'api/movimento') return { ok: true, nuovo: !!(body && body.foto) };
    if (path === 'api/foto') return { ok: true, id: 'mock-foto' };
    if (path === 'api/approvazioni') return MOCKDB.appr.slice();
    if ((m = /^api\/approvazioni\/(.+)$/.exec(path))) { MOCKDB.appr = MOCKDB.appr.filter(function (x) { return x.id !== decodeURIComponent(m[1]); }); return { ok: true }; }
    throw new Error('Percorso sconosciuto: ' + path);
  }
  function api(method, path, body, raw) {
    if (MOCK) return new Promise(function (res, rej) { setTimeout(function () { try { res(mockApi(method, path, raw ? null : body)); } catch (e) { rej(e); } }, 120); });
    var opt = { method: method, headers: {} };
    if (raw) { opt.body = raw; opt.headers['Content-Type'] = raw.type || 'application/octet-stream'; }
    else if (body !== undefined) { opt.body = JSON.stringify(body); opt.headers['Content-Type'] = 'application/json'; }
    return fetch('./' + path, opt).then(function (r) {
      if (!r.ok) throw new Error('Errore ' + r.status);
      return r.json();
    });
  }

  /* ---------- utilità UI ---------- */
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; }
  var tt;
  function toast(msg, err) { var t = $('toast'); t.textContent = msg; t.className = 'on' + (err ? ' err' : ''); clearTimeout(tt); tt = setTimeout(function () { t.className = ''; }, 2800); }
  function note(node, msg, cls) { node.textContent = msg || ''; node.className = 'note' + (cls ? ' ' + cls : ''); }

  /* ---------- navigazione ---------- */
  function buildNav() {
    var nav = $('nav');
    TABS.forEach(function (t) {
      var b = el('button'); b.type = 'button'; b.dataset.tab = t[0];
      b.innerHTML = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICON[t[0]] + '</svg>';
      b.appendChild(document.createTextNode(t[1]));
      b.addEventListener('click', function () { show(t[0]); });
      nav.appendChild(b);
    });
  }
  function show(tab) {
    st.tab = tab;
    TABS.forEach(function (t) {
      $('v-' + t[0]).hidden = t[0] !== tab;
      if (t[0] === tab) $('title').textContent = t[2];
    });
    Array.prototype.forEach.call($('nav').children, function (b) { if (b.dataset.tab === tab) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current'); });
    if (tab !== 'mov') stopScan();
    if (tab === 'stock') loadStock();
    if (tab === 'appr') loadAppr();
    if (tab === 'mov') $('bc').focus();
  }

  /* ---------- form +/- ---------- */
  function buildSeg(id, items, key) {
    var box = $(id); box.textContent = '';
    items.forEach(function (it) {
      var lab = Array.isArray(it) ? it[0] : it;
      var b = el('button', '', lab); b.type = 'button';
      b.setAttribute('aria-pressed', String(st[key] === lab));
      b.addEventListener('click', function () { st[key] = lab; buildSeg(id, items, key); });
      box.appendChild(b);
    });
  }
  function setQta(n) { st.qta = Math.max(1, n); $('qv').value = st.qta; $('qv').textContent = st.qta; }
  function setKnown(k) {
    st.known = k;
    $('foto').hidden = k !== false;
    $('pr').readOnly = k === true;
    if (k !== false) { st.fotoBlob = null; $('prev').hidden = true; $('file').value = ''; }
  }
  var lookupSeq = 0;
  function lookup() {
    var bc = $('bc').value.trim();
    if (!/^\d{6,14}$/.test(bc)) { setKnown(null); note($('hint'), bc ? 'Il codice deve avere solo cifre (6-14).' : '', bc ? 'warn' : ''); return Promise.resolve(); }
    var my = ++lookupSeq;
    note($('hint'), 'Cerco il prodotto…');
    return api('GET', 'api/prodotto/' + encodeURIComponent(bc)).then(function (r) {
      if (my !== lookupSeq) return;
      if (r && r.found) {
        setKnown(true); $('pr').value = r.prodotto || '';
        note($('cat'), [r.categoria, r.sottocategoria].filter(Boolean).join(' › '));
        note($('hint'), 'Prodotto noto: il movimento viene salvato subito.', 'ok');
      } else {
        setKnown(false); note($('cat'), '');
        note($('hint'), 'Codice nuovo: scatta una foto, il prodotto va in "Da inserire" e lo compila l\'AI.', 'warn');
      }
    }).catch(function (e) { if (my === lookupSeq) { setKnown(null); note($('hint'), 'Ricerca non riuscita: ' + e.message, 'warn'); } });
  }
  function resetForm() {
    $('bc').value = ''; $('pr').value = ''; setKnown(null); setQta(1);
    note($('hint'), ''); note($('cat'), ''); $('bc').focus();
  }
  function resizeImage(file) {
    return new Promise(function (res) {
      try {
        var url = URL.createObjectURL(file), img = new Image();
        img.onload = function () {
          var s = Math.min(1, 1280 / Math.max(img.width, img.height)), c = document.createElement('canvas');
          c.width = Math.round(img.width * s); c.height = Math.round(img.height * s);
          c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
          c.toBlob(function (b) { URL.revokeObjectURL(url); res(b || file); }, 'image/jpeg', 0.82);
        };
        img.onerror = function () { URL.revokeObjectURL(url); res(file); };
        img.src = url;
      } catch (e) { res(file); }
    });
  }
  function save(ev) {
    ev.preventDefault();
    var bc = $('bc').value.trim();
    if (!/^\d{6,14}$/.test(bc)) { toast('Inserisci un barcode valido.', true); $('bc').focus(); return; }
    var btn = $('save'); btn.disabled = true;
    var go = st.known === null ? lookup() : Promise.resolve();
    go.then(function () {
      if (st.known === false && !st.fotoBlob) { toast('Per un codice nuovo serve la foto.', true); throw new Error('stop'); }
      return st.known === false ? api('POST', 'api/foto', undefined, st.fotoBlob).then(function (r) { return r.id || r.url || ''; }) : '';
    }).then(function (foto) {
      var tipoVal = TIPI.filter(function (t) { return t[0] === st.tipo; })[0][1];
      return api('POST', 'api/movimento', { barcode: bc, tipo: tipoVal, luogo: st.luogo, quantita: st.qta, prodotto: $('pr').value.trim(), foto: foto || undefined });
    }).then(function () { toast('Movimento salvato.'); resetForm(); })
      .catch(function (e) { if (e.message !== 'stop') toast('Non salvato: ' + e.message, true); })
      .then(function () { btn.disabled = false; });
  }

  /* ---------- scanner ---------- */
  var stream = null, scanTimer = null, detector = null, zx = null;
  var ZX_URL = 'https://cdn.jsdelivr.net/npm/@zxing/library@0.21.3/umd/index.min.js';
  var ZX_SRI = 'sha384-BzBxP10ZE72aitqj5UMmUsbKFliP/DZqA8Wq+BNNhlIJDGoEd1tpkMYXOg9+n6sB';
  function loadZX() { // libreria di lettura codici: caricata solo quando serve (iPhone, app Home Assistant, foto)
    if (window.ZXing) return Promise.resolve(window.ZXing);
    if (zx) return zx;
    zx = new Promise(function (ok, ko) {
      var sc = document.createElement('script'); sc.src = ZX_URL; sc.integrity = ZX_SRI; sc.crossOrigin = 'anonymous';
      sc.onload = function () { window.ZXing ? ok(window.ZXing) : ko(new Error('lib')); };
      sc.onerror = function () { zx = null; ko(new Error('rete')); };
      document.head.appendChild(sc);
    });
    return zx;
  }
  function zxReader(Z) {
    var hints = new Map();
    hints.set(Z.DecodeHintType.POSSIBLE_FORMATS, [Z.BarcodeFormat.EAN_13, Z.BarcodeFormat.EAN_8, Z.BarcodeFormat.UPC_A, Z.BarcodeFormat.UPC_E, Z.BarcodeFormat.CODE_128, Z.BarcodeFormat.QR_CODE]);
    hints.set(Z.DecodeHintType.TRY_HARDER, true);
    var r = new Z.MultiFormatReader(); r.setHints(hints); return r;
  }
  function zxDecode(Z, reader, canvas) {
    var lum = new Z.HTMLCanvasElementLuminanceSource(canvas);
    return reader.decode(new Z.BinaryBitmap(new Z.HybridBinarizer(lum))).getText();
  }
  function stopScan() {
    clearInterval(scanTimer); scanTimer = null;
    if (stream) { stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; }
    $('vid').srcObject = null; $('scanbox').hidden = true;
  }
  function gotCode(txt) { $('bc').value = String(txt).replace(/\D/g, '') || txt; stopScan(); lookup(); }
  function startLive() {
    var useNative = 'BarcodeDetector' in window;
    var prep = useNative ? Promise.resolve(null) : loadZX();
    prep.then(function (Z) {
      var reader = Z ? zxReader(Z) : null, cv = document.createElement('canvas');
      if (useNative) detector = detector || new window.BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128', 'qr_code'] });
      return navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false }).then(function (s) {
        stream = s; var v = $('vid'); v.srcObject = s; $('scanbox').hidden = false; v.play();
        scanTimer = setInterval(function () {
          if (useNative) { detector.detect(v).then(function (c) { if (c && c.length) gotCode(c[0].rawValue); }).catch(function () {}); return; }
          if (!v.videoWidth) return;
          cv.width = v.videoWidth; cv.height = v.videoHeight; cv.getContext('2d').drawImage(v, 0, 0);
          try { gotCode(zxDecode(Z, reader, cv)); } catch (e) { /* nessun codice in questo fotogramma */ }
        }, 250);
      });
    }).catch(function (e) {
      note($('hint'), e && e.message === 'rete' ? 'Non riesco a caricare il lettore: serve la connessione. Scatta una foto al codice.' : 'Fotocamera non disponibile o permesso negato: scatta una foto al codice.', 'warn');
      $('scanfile').click();
    });
  }
  function startScan() {
    var live = window.isSecureContext && navigator.mediaDevices && navigator.mediaDevices.getUserMedia;
    if (live) { startLive(); return; }
    note($('hint'), 'Fotocamera dal vivo solo con l\'indirizzo sicuro (https). Intanto scatta una foto al codice a barre.', 'warn');
    api('GET', 'api/config').then(function (c) {
      if (c && c.url_sicuro) { var a = el('a', 'btn ghost', 'Apri con l\'indirizzo sicuro'); a.href = c.url_sicuro; a.target = '_top'; $('hint').appendChild(document.createElement('br')); $('hint').appendChild(a); }
    }).catch(function () {});
    $('scanfile').click();
  }
  function scanPhoto(file) { // legge il codice da una foto, senza bisogno di https
    if (!file) return;
    note($('hint'), 'Leggo il codice…', '');
    var url = URL.createObjectURL(file), img = new Image();
    img.onload = function () {
      loadZX().then(function (Z) {
        var reader = zxReader(Z), cv = document.createElement('canvas'), done = false;
        [1600, 1000, 640].forEach(function (max) {
          if (done) return;
          var k = Math.min(1, max / Math.max(img.width, img.height));
          cv.width = Math.round(img.width * k); cv.height = Math.round(img.height * k);
          cv.getContext('2d').drawImage(img, 0, 0, cv.width, cv.height);
          try { var t = zxDecode(Z, reader, cv); done = true; note($('hint'), '', ''); gotCode(t); } catch (e) { /* riprova con un'altra dimensione */ }
        });
        if (!done) note($('hint'), 'Codice non riconosciuto: avvicinati, tieni il codice dritto e ben illuminato, poi riprova.', 'warn');
      }).catch(function () { note($('hint'), 'Non riesco a caricare il lettore: serve la connessione. Digita il codice.', 'warn'); })
        .then(function () { URL.revokeObjectURL(url); $('scanfile').value = ''; });
    };
    img.onerror = function () { note($('hint'), 'Foto non leggibile.', 'warn'); URL.revokeObjectURL(url); };
    img.src = url;
  }

  /* ---------- stock ---------- */
  function loadStock() {
    api('GET', 'api/stock').then(function (r) { st.stock = r || []; renderStock(); $('sub').textContent = st.stock.length + ' prodotti'; })
      .catch(function (e) { toast('Stock non caricato: ' + e.message, true); });
  }
  function buildChips() {
    var box = $('chips'); box.textContent = '';
    ['Tutti', 'Casa', 'Cantina', 'Sotto scorta'].forEach(function (f) {
      var b = el('button', 'chip', f); b.type = 'button'; b.setAttribute('aria-pressed', String(st.filtro === f));
      b.addEventListener('click', function () { st.filtro = f; buildChips(); renderStock(); });
      box.appendChild(b);
    });
  }
  function isLow(r) { return r.minima > 0 && r.qta <= r.minima; }
  function renderStock() {
    var q = $('q').value.trim().toLowerCase(), box = $('stock'), groups = {}, order = [];
    box.textContent = '';
    st.stock.filter(function (r) {
      if (st.filtro === 'Casa' || st.filtro === 'Cantina') { if (r.luogo !== st.filtro) return false; }
      if (st.filtro === 'Sotto scorta' && !isLow(r)) return false;
      return !q || [r.nome, r.marca, r.categoria, r.sotto, r.tipo].join(' ').toLowerCase().indexOf(q) >= 0;
    }).forEach(function (r) { var g = r.categoria || 'Altro'; if (!groups[g]) { groups[g] = []; order.push(g); } groups[g].push(r); });
    if (!order.length) { box.appendChild(el('p', 'empty', 'Nessun prodotto trovato.')); return; }
    order.forEach(function (g) {
      var d = el('details', 'g'); d.open = true; d.appendChild(el('summary', '', g + ' (' + groups[g].length + ')'));
      groups[g].forEach(function (r) {
        var it = el('div', 'item'), n = el('div', 'n'), th = el('div', 'th');
        if (r.img) { var im = document.createElement('img'); im.src = r.img; im.alt = ''; im.loading = 'lazy'; im.referrerPolicy = 'no-referrer'; im.addEventListener('error', function () { im.remove(); }); th.appendChild(im); }
        it.appendChild(th);
        n.appendChild(el('b', '', r.nome));
        var sub = [r.marca, r.conf].filter(Boolean).join(' · '); if (sub) n.appendChild(el('span', 'sub2', sub));
        if (r.tipo) n.appendChild(el('span', 'tipo', r.tipo)); n.appendChild(el('span', '', [r.sotto, r.luogo].filter(Boolean).join(' · ')));
        it.appendChild(n); it.appendChild(el('span', 'badge' + (isLow(r) ? ' low' : ''), isLow(r) ? 'Sotto scorta' : 'Ok'));
        it.appendChild(el('div', 'qta', String(r.qta))); d.appendChild(it);
      });
      box.appendChild(d);
    });
  }

  /* ---------- approvazioni ---------- */
  function loadAppr() {
    api('GET', 'api/approvazioni').then(function (list) { renderAppr(list || []); })
      .catch(function (e) { toast('Approvazioni non caricate: ' + e.message, true); });
  }
  function renderAppr(list) {
    var box = $('appr'); box.textContent = '';
    $('sub').textContent = list.length ? list.length + (list.length === 1 ? ' proposta in attesa' : ' proposte in attesa') : 'Nessuna proposta in attesa';
    if (!list.length) { box.appendChild(el('p', 'empty', 'Tutto approvato.')); return; }
    list.forEach(function (a) {
      var c = el('article', 'card'), pd = function (cls, k, v) { var r = el('div', 'pd ' + cls); r.appendChild(el('div', 'k', k)); r.appendChild(el('div', 'v', v)); return r; };
      c.appendChild(el('h2', '', a.titolo)); c.appendChild(pd('prima', 'PRIMA', a.prima)); c.appendChild(pd('dopo', 'DOPO', a.dopo));
      if (a.motivo) c.appendChild(el('div', 'why', a.motivo));
      var bt = el('div', 'btns'), ok = el('button', 'btn ok', 'Approva'), no = el('button', 'btn bad', 'Scarta');
      ok.type = no.type = 'button';
      function act(azione) {
        ok.disabled = no.disabled = true;
        api('POST', 'api/approvazioni/' + encodeURIComponent(a.id), { azione: azione }).then(function () {
          toast(azione === 'approva' ? 'Approvata.' : 'Scartata.'); loadAppr();
        }).catch(function (e) { ok.disabled = no.disabled = false; toast('Non riuscito: ' + e.message, true); });
      }
      ok.addEventListener('click', function () { act('approva'); }); no.addEventListener('click', function () { act('scarta'); });
      bt.appendChild(ok); bt.appendChild(no); c.appendChild(bt); box.appendChild(c);
    });
  }

  /* ---------- avvio ---------- */
  function init() {
    buildNav(); buildSeg('tipo', TIPI, 'tipo'); buildSeg('luogo', LUOGHI, 'luogo'); buildChips(); setQta(1);
    $('qm').addEventListener('click', function () { setQta(st.qta - 1); });
    $('qp').addEventListener('click', function () { setQta(st.qta + 1); });
    $('scan').addEventListener('click', startScan); $('scanfile').addEventListener('change', function (e) { scanPhoto(e.target.files[0]); }); $('scanstop').addEventListener('click', stopScan);
    $('cancel').addEventListener('click', function () { stopScan(); resetForm(); });
    $('f').addEventListener('submit', save);
    var dbt;
    $('bc').addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); lookup().then(function () { (st.known === false ? $('pr') : $('save')).focus(); }); } });
    $('bc').addEventListener('input', function () { clearTimeout(dbt); setKnown(null); if (/^\d{8,14}$/.test($('bc').value.trim())) dbt = setTimeout(lookup, 450); });
    $('bc').addEventListener('change', lookup);
    $('file').addEventListener('change', function () {
      var f = $('file').files[0]; if (!f) return;
      resizeImage(f).then(function (b) { st.fotoBlob = b; var p = $('prev'); p.src = URL.createObjectURL(b); p.hidden = false; });
    });
    $('q').addEventListener('input', renderStock);
    show('mov');
    if ('serviceWorker' in navigator && location.protocol !== 'file:') navigator.serviceWorker.register('sw.js').catch(function () {});
  }
  init();
})();
