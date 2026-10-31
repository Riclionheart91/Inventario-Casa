(function () {
  'use strict';
  var MOCK = new URLSearchParams(location.search).get('mock') === '1';
  var TIPI = [['Carico', 'Carico'], ['Scarico', 'Scarico'], ['Sposta', 'Move'], ['Cambia categoria', 'Cng']]; // [etichetta, valore inviato]
  var LUOGHI = ['Casa', 'Cantina'];
  var ICON = {
    mov: '<path d="M5 12h14M12 5v14"/>',
    stock: '<path d="M4 7l8-4 8 4v10l-8 4-8-4z"/><path d="M4 7l8 4 8-4M12 11v10"/>',
    spesa: '<circle cx="9" cy="20" r="1.5"/><circle cx="18" cy="20" r="1.5"/><path d="M3 4h3l2.5 11h10L21 7H7"/>',
    bozze: '<path d="M4 13h4l2 3h4l2-3h4"/><path d="M5 13l2-8h10l2 8v6H5z"/>',
    prod: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
    appr: '<path d="M5 13l4 4L19 7"/>'
  };
  var TABS = [['mov', '+/-', 'Movimento +/-'], ['stock', 'Stock', 'Stock'], ['prod', 'Prodotti', 'Tutti i prodotti'], ['spesa', 'Spesa', 'Spesa'], ['bozze', 'Da inserire', 'Da inserire'], ['appr', 'Approvazioni', 'Approvazioni AI']];
  var $ = function (id) { return document.getElementById(id); };
  var st = { tipo: 'Carico', luogo: 'Casa', qta: 1, known: null, giac: [], riga: 0, cats: null, ro: true, fotoBlob: null, stock: [], filtro: 'Tutti', tab: 'mov' };

  /* ---------- API (con mock) ---------- */
  var MOCKDB = {
    prod: { '8002795002995': { prodotto: 'Latte UHT intero', categoria: 'Dispensa', sottocategoria: 'Bevande' }, '8000500310427': { prodotto: 'Nutella 450 g', categoria: 'Dispensa', sottocategoria: 'Snack e Dolci' } },
    stock: [
      { barcode: 8002795002995, nome: 'Latte fresco intero', marca: 'Granarolo', conf: '1 l', img: "data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Crect width='200' height='200' fill='white'/%3E%3Crect x='60' y='30' width='80' height='140' rx='12' fill='%23c0392b'/%3E%3Crect x='72' y='70' width='56' height='50' fill='white'/%3E%3C/svg%3E", categoria: 'Frigorifero', sotto: 'Latticini', tipo: 'Latte', luogo: 'Casa', qta: 3, minima: 1 },
      { nome: 'Burro', categoria: 'Frigorifero', sotto: 'Latticini', tipo: 'Burro', luogo: 'Casa', qta: 1, minima: 2 },
      { nome: 'Latte UHT intero', categoria: 'Dispensa', sotto: 'Bevande', tipo: 'Latte', luogo: 'Casa', qta: 6, minima: 2 },
      { nome: 'Pasta di semola', categoria: 'Dispensa', sotto: 'Pasta e riso', luogo: 'Casa', qta: 9, minima: 3 },
      { nome: 'Sale fino', categoria: 'Dispensa', sotto: 'Condimenti e Sale', luogo: 'Casa', qta: 2, minima: 1 },
      { nome: 'Acqua naturale', categoria: 'Cantina', sotto: 'Bevande', luogo: 'Cantina', qta: 12, minima: 6 },
      { nome: 'Birra', categoria: 'Cantina', sotto: 'Bevande', luogo: 'Cantina', qta: 8, minima: 0 }
    ],
    appr: [
      { id: 'P_1', genere: 'P', gruppo: 'Prodotti da correggere', titolo: 'Si & No Mais', prima: 'Si & No Mais · Dispensa › Snack e Dolci', dopo: 'Gallette di mais · Dispensa › Snack e Dolci · tipo Galletta', sicurezza: 100, motivo: 'Snack a base di mais soffiato, classificabile come galletta.', campi: { nome: 'Gallette di mais', categoria: 'Dispensa', sottocategoria: 'Snack e Dolci', tipo: 'Galletta' } },
      { id: 'P_2', genere: 'P', gruppo: 'Prodotti da correggere', titolo: 'Latte UHT', prima: 'Latte UHT · Dispensa › Bevande', dopo: 'Latte UHT · Frigorifero › Latticini', sicurezza: 82, motivo: 'Attenzione: il latte UHT chiuso resta in dispensa.', campi: { nome: 'Latte UHT', categoria: 'Frigorifero', sottocategoria: 'Latticini', tipo: 'Latte' } },
      { id: 'T_Uova', genere: 'T', gruppo: 'Nuovi tipi', titolo: 'Nuovo tipo: Uova', prima: '', dopo: 'Tipo Uova', sicurezza: null, motivo: "L'AI vuole creare questo tipo di prodotto.", campi: { tipo: 'Uova', scorta_min: 0 } }
    ],
    spesa: { finiti: 1, in_esaurimento: 1, voci: [
      { tipo: 'Burro', categoria: 'Frigorifero', sottocategoria: 'Latticini', giacenza: 0, minima: 2, stato: 'FINITO', dettaglio: 'Casa 0 (1 codice)', barcode: 8002795002995, prodotto: 'Burro', immagine: '' },
      { tipo: 'Latte', categoria: 'Dispensa', sottocategoria: 'Bevande', giacenza: 2, minima: 2, stato: 'STA_FINENDO', dettaglio: 'Casa 2 (2 codici)', barcode: 8002795002995, prodotto: 'Latte UHT intero', immagine: '' }
    ] },
    bozze: [
      { id: 'b1', barcode: '8004444444444', foto: 'https://drive.example/foto', nome: 'Biscotti frollini', marca: 'Mulino', confezione: '300 g', categoria: 'Dispensa', sottocategoria: 'Snack e Dolci', tipo: 'Biscotti', immagine: '', stato: 'PRONTA', fonte: 'Foto (AI)', nota: '', location: 'Casa', movimento: 'Carico', quantita: 2 },
      { id: 'b2', barcode: '8005555555555', foto: '', nome: '', marca: '', confezione: '', categoria: '', sottocategoria: '', tipo: '', immagine: '', stato: 'NON_TROVATO', fonte: '', nota: 'Codice non trovato. Aggiungi una foto o scrivi a mano.', location: 'Cantina', movimento: 'Carico', quantita: 1 }
    ]
  };
  if (MOCK && /[?&]vuoto=1/.test(location.search)) { MOCKDB.bozze = []; MOCKDB.appr = []; }   // prova: niente da inserire ne da approvare
  function mockApi(method, path, body) {
    var m;
    var m;
    if (path === 'api/stock') return MOCKDB.stock;
    if (path === 'api/prodotti') return MOCKDB.stock.map(function (e) { return Object.assign({}, e, { qta: e.qta, posti: [{ luogo: e.luogo, qta: e.qta }].concat(e.nome.length % 2 ? [{ luogo: 'Cantina', qta: 1 }] : []) }); }).concat([{ barcode: 1, nome: 'Aceto balsamico', marca: 'Ponti', conf: '500 ml', tipo: 'Aceto', categoria: 'Dispensa', sotto: 'Condimenti e Sale', img: '', qta: 0, minima: 1 }]).sort(function (a, b) { return a.nome.localeCompare(b.nome); });
    if (/^api\/scheda\//.test(path)) return { barcode: 8002795002995, nome: 'Latte fresco intero', marca: 'Granarolo', confezione: '1 l', categoria: 'Frigorifero', sottocategoria: 'Latticini', tipo: 'Latte', immagine: MOCKDB.stock[0].img, dettagli: '🌍 Italia', punteggi: 'Nutri 🟢 B  |  NOVA 🏭 1  |  Eco 🌿 A', composizione: '🧪 Ingredienti: Latte fresco pastorizzato intero.', free_from: '🥗 Vegetariano', nutrizione: '🔥 64 kcal  |  🫙 3.6 g grassi  |  🍬 4.9 g zuccheri  |  🧂 0.1 g sale', smaltimento: '📦 Carta  🧴 Plastica PP', aggiornato: '21/03/2026', scorta_minima: 1, totale: 3, giacenze: [{ luogo: 'Casa', categoria: 'Frigorifero', qta: 3, minima: 1 }, { luogo: 'Cantina', categoria: 'Bevande', qta: 2, minima: 0 }] };
    if ((m = /^api\/prodotto\/(.+)$/.exec(path))) { var p = MOCKDB.prod[decodeURIComponent(m[1])]; return p ? Object.assign({ found: true }, p) : { found: false }; }
    if (/^api\/cerca\//.test(path)) return decodeURIComponent(path.slice(10)) === '9999999999999' ? { found: false } : { found: true, nome: 'Crema Spalmabile Alle Nocciole', marca: 'Ferrero', confezione: '450 g', immagine: MOCKDB.stock[0].img, fonte: 'Open Food Facts', composizione: '', nutrizione: '', punteggi: '' };
    if (path === 'api/tipi') return ['Crema spalmabile', 'Latte', 'Pasta'];
    if (method === 'POST' && path === 'api/prodotto') return { ok: true };
    if (path === 'api/config') return { url_sicuro: '', sola_lettura: false, ai: true, shortcut_spesa: 'Spesa AppSheet' };
    if (path === 'api/suggerisci') return { ai: true, categoria: 'Dispensa', sottocategoria: 'Snack e Dolci', tipo: 'Crema spalmabile', tipo_nuovo: false };
    if (path === 'api/categorie') return [{ categoria: 'Dispensa', sottocategorie: ['Pasta e Riso', 'Bevande', 'Snack e Dolci'] }, { categoria: 'Frigorifero', sottocategorie: ['Latticini'] }, { categoria: 'Cantina', sottocategorie: ['Bevande'] }];
    if (method === 'PATCH') return { ok: true, movimenti_aggiornati: 3 };
    if (method === 'POST' && path === 'api/tipi/scorta') return { ok: true, tipo: body.tipo, scorta_minima: body.scorta };
    if (path === 'api/movimento') return { ok: true, nuovo: !!(body && body.foto) };
    if (path === 'api/foto') return { ok: true, id: 'mock-foto' };
    if (path === 'api/approvazioni') return MOCKDB.appr.slice();
    if ((m = /^api\/approvazioni\/(.+)$/.exec(path))) { MOCKDB.appr = MOCKDB.appr.filter(function (x) { return x.id !== decodeURIComponent(m[1]); }); return { ok: true }; }
    if (path === 'api/spesa') return MOCKDB.spesa;
    if (path === 'api/bozze') return MOCKDB.bozze.slice();
    if ((m = /^api\/bozze\/([^/]+)\/(salva|conferma|scarta)$/.exec(path))) { if (m[2] !== 'salva') MOCKDB.bozze = MOCKDB.bozze.filter(function (x) { return x.id !== m[1]; }); return { ok: true }; }
    throw new Error('Percorso sconosciuto: ' + path);
  }
  function errTesto(j, st) {   // il server manda un testo, oppure (errori di formato) un elenco di oggetti
    var d = j && (j.errore || j.detail || j.error);
    if (Array.isArray(d)) d = d.map(function (x) { return x && x.msg ? ((x.loc || []).slice(1).join('.') + ' ' + x.msg).trim() : String(x); }).join('; ');
    return (d && typeof d === 'object') ? JSON.stringify(d) : (d || ('Errore ' + st));
  }
  function api(method, path, body, raw, form) {
    if (MOCK && method !== 'GET') (window.__log = window.__log || []).push([method, path, body]);
    if (MOCK) return new Promise(function (res, rej) { setTimeout(function () { try { res(mockApi(method, path, raw ? null : body)); } catch (e) { rej(e); } }, 120); });
    var opt = { method: method, headers: {} };
    if (form) opt.body = form;
    if (raw) { opt.body = raw; opt.headers['Content-Type'] = raw.type || 'application/octet-stream'; }
    else if (body !== undefined) { opt.body = JSON.stringify(body); opt.headers['Content-Type'] = 'application/json'; }
    return fetch('./' + path, opt).then(function (r) {
      if (!r.ok) return r.json().catch(function () { return {}; }).then(function (j) { throw new Error(errTesto(j, r.status)); });
      return r.json();
    });
  }

  /* ---------- utilità UI ---------- */
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; }
  var tt;
  function toast(msg, err) { var t = $('toast'); t.textContent = msg; t.className = 'on' + (err ? ' err' : ''); clearTimeout(tt); tt = setTimeout(function () { t.className = ''; }, 2800); }
  function note(node, msg, cls) { node.textContent = msg || ''; node.className = 'note' + (cls ? ' ' + cls : ''); }

  /* ---------- navigazione ---------- */
  /* Da inserire e Approvazioni compaiono nella barra solo quando c'e qualcosa da fare (o se ci si e gia dentro) */
  var NASCONDIBILI = { bozze: 'api/bozze', appr: 'api/approvazioni' };
  function tabVisibile(id) { return !(id in NASCONDIBILI) || st.tab === id || (st.n && st.n[id] > 0); }
  function idVisibili() { return TABS.map(function (t) { return t[0]; }).filter(tabVisibile); }
  function applicaNav() {
    var nav = $('nav'), n = 0;
    Array.prototype.forEach.call(nav.querySelectorAll('button'), function (b) { var v = tabVisibile(b.dataset.tab); b.hidden = !v; if (v) n++; });
    nav.style.gridTemplateColumns = 'repeat(' + n + ',minmax(0,1fr))'; navInd(0, false);
  }
  function aggiornaConteggi() {
    st.n = st.n || {};
    Object.keys(NASCONDIBILI).forEach(function (id) {
      api('GET', NASCONDIBILI[id]).then(function (l) { st.n[id] = (l || []).length; applicaNav(); }).catch(function () { /* resta com'e */ });
    });
  }
  function buildNav() {
    var nav = $('nav');
    TABS.forEach(function (t) {
      var b = el('button'); b.type = 'button'; b.dataset.tab = t[0];
      b.innerHTML = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICON[t[0]] + '</svg>';
      b.appendChild(document.createTextNode(t[1]));
      b.addEventListener('click', function () { show(t[0]); });
      nav.appendChild(b);
    });
    var ind = el('div', ''); ind.id = 'nav-ind'; ind.setAttribute('aria-hidden', 'true'); nav.appendChild(ind);
    applicaNav(); aggiornaConteggi();
  }
  function setStk() {   // altezza della barra fissa della pagina visibile: da li partono le categorie fisse
    var v = document.querySelector('.view:not([hidden]) .stk');
    document.documentElement.style.setProperty('--stk', (v ? v.offsetHeight : 0) + 'px');
  }
  function show(tab) {
    st.tab = tab;
    TABS.forEach(function (t) {
      $('v-' + t[0]).hidden = t[0] !== tab;
      if (t[0] === tab) $('title').textContent = t[2];
    });
    Array.prototype.forEach.call($('nav').children, function (b) { if (b.dataset.tab === tab) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current'); });
    applicaNav(); aggiornaConteggi();
    navInd(0, true);
    if (tab === 'stock' || tab === 'prod') hintSwipe('v-' + tab);
    if (tab !== 'mov') stopScan();
    if (tab === 'stock') loadStock();
    if (tab === 'prod') loadProd();
    if (tab === 'appr') loadAppr();
    if (tab === 'spesa') loadSpesa();
    if (tab === 'bozze') loadBozze();
    if (tab === 'mov') $('bc').focus();
    setStk();
  }

  /* ---------- form +/- ---------- */
  function buildSeg(id, items, key) {
    var box = $(id); box.textContent = '';
    items.forEach(function (it) {
      var lab = Array.isArray(it) ? it[0] : it;
      var b = el('button', '', lab); b.type = 'button';
      b.setAttribute('aria-pressed', String(st[key] === lab));
      b.addEventListener('click', function () { st[key] = lab; buildSeg(id, items, key); if (key === 'tipo') renderRiga(); });
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
    if (!/^\d{6,24}$/.test(bc)) { hideProp(); setKnown(null); note($('hint'), bc ? 'Il codice deve avere solo cifre (6-24).' : '', bc ? 'warn' : ''); return Promise.resolve(); }
    var my = ++lookupSeq; hideProp();
    note($('hint'), 'Cerco il prodotto…');
    return api('GET', 'api/prodotto/' + encodeURIComponent(bc)).then(function (r) {
      if (my !== lookupSeq) return;
      if (r && r.found) {
        setKnown(true); $('pr').value = r.prodotto || '';
        note($('cat'), [r.categoria, r.sottocategoria].filter(Boolean).join(' › '));
        note($('hint'), 'Prodotto noto: il movimento viene salvato subito.', 'ok');
        loadGiac(bc);
      } else {
        setKnown(false); note($('cat'), ''); st.giac = []; renderRiga(); hideProp();
        note($('hint'), 'Codice nuovo: cerco nei database…', '');
        cercaNuovo(bc, my);
      }
    }).catch(function (e) { if (my === lookupSeq) { setKnown(null); note($('hint'), 'Ricerca non riuscita: ' + e.message, 'warn'); } });
  }
  /* ---------- codice nuovo: proposta dai database ---------- */
  var NOTA_NUOVO = 'Codice nuovo: scatta una foto, l\'AI la legge (la foto non si salva) e il prodotto va in "Da inserire" già compilato.';
  function hideProp() { $('prop').hidden = true; $('prop').textContent = ''; st.prop = null; $('save').hidden = false; }
  function cercaNuovo(bc, my) {
    var cats = st.cats ? Promise.resolve() : api('GET', 'api/categorie').then(function (c) { st.cats = c || []; }).catch(function () { st.cats = []; });
    var tipi = st.tipi ? Promise.resolve() : api('GET', 'api/tipi').then(function (t) { st.tipi = t || []; }).catch(function () { st.tipi = []; });
    Promise.all([cats, tipi]).then(function () { return api('GET', 'api/cerca/' + bc); }).then(function (r) {
      if (my !== lookupSeq) return;
      if (r && r.found) { st.prop = r; showProp(bc, r); note($('hint'), 'Trovato su ' + r.fonte + ': controlla e conferma.', 'ok'); }
      else note($('hint'), 'Non trovato nei database' + (r && r.errori && r.errori.length ? ' (alcuni non hanno risposto: ' + r.errori.join(', ') + ')' : '') + '. ' + NOTA_NUOVO, 'warn');
    }).catch(function () { if (my === lookupSeq) note($('hint'), 'Ricerca nei database non riuscita. ' + NOTA_NUOVO, 'warn'); });
  }
  function showProp(bc, r) {
    var box = $('prop'); box.textContent = ''; box.hidden = false; $('foto').hidden = true; $('save').hidden = true;
    box.appendChild(el('h3', '', 'Proposta dai database'));
    var ph = el('div', 'ph'), th = el('div', 'th'), tt = el('div', '');
    if (r.immagine) thumb(th, r.immagine);
    ph.appendChild(th); tt.appendChild(el('div', 'm', [r.marca, r.confezione].filter(Boolean).join(' · ') || 'Marca e confezione non indicate')); ph.appendChild(tt); box.appendChild(ph);
    var nome = el('input'); nome.type = 'text'; nome.value = r.nome || ''; nome.setAttribute('aria-label', 'Nome del prodotto'); box.appendChild(nome);
    var cat = el('select'); cat.setAttribute('aria-label', 'Categoria'); var sot = el('select'); sot.setAttribute('aria-label', 'Sottocategoria');
    var ainote = el('div', 'note', ''); box.appendChild(ainote);
    var o0 = el('option', '', 'Scegli la categoria'); o0.value = ''; cat.appendChild(o0);
    (st.cats || []).forEach(function (c) { var o = el('option', '', c.categoria); o.value = c.categoria; cat.appendChild(o); });
    function fillSot() { sot.textContent = ''; var c = (st.cats || []).filter(function (x) { return x.categoria === cat.value; })[0]; var o = el('option', '', cat.value ? 'Scegli la sottocategoria' : 'Scegli prima la categoria'); o.value = ''; sot.appendChild(o); ((c && c.sottocategorie) || []).forEach(function (s) { var p = el('option', '', s); p.value = s; sot.appendChild(p); }); }
    cat.addEventListener('change', fillSot); fillSot(); box.appendChild(cat); box.appendChild(sot);
    var tipo = el('input'); tipo.type = 'text'; tipo.placeholder = 'Tipo (facoltativo)'; tipo.setAttribute('list', 'tipi-dl'); tipo.setAttribute('aria-label', 'Tipo');
    var dl = $('tipi-dl') || el('datalist'); dl.id = 'tipi-dl'; dl.textContent = ''; (st.tipi || []).forEach(function (x) { var o = el('option'); o.value = x; dl.appendChild(o); }); box.appendChild(dl); box.appendChild(tipo);
    var toccato = false; [cat, sot, tipo].forEach(function (x) { x.addEventListener('input', function () { toccato = true; }); x.addEventListener('change', function () { toccato = true; }); });
    {   // suggerimento AI: riempie i menu, l'utente rivede e corregge prima di salvare
      note(ainote, 'L\'AI sta suggerendo categoria e tipo…');
      api('POST', 'api/suggerisci', { nome: r.nome || '', marca: r.marca || '', confezione: r.confezione || '' }).then(function (a) {
        if ($('bc').value.trim() !== bc || box.hidden) return;
        if (!a || !a.ai) { note(ainote, a && a.motivo === 'chiave' ? 'Suggerimento AI spento: manca la chiave Gemini nelle opzioni dell\'app. Scegli tu categoria e tipo.' : 'L\'AI non ha risposto' + (a && a.dettaglio ? ' (' + a.dettaglio + ')' : '') + ': scegli tu categoria e tipo.', 'warn'); return; }
        if (toccato) { note(ainote, ''); return; }   // l'utente ha gia scelto qualcosa: non si sovrascrive
        if (a.categoria) { cat.value = a.categoria; fillSot(); if (a.sottocategoria) sot.value = a.sottocategoria; }
        if (a.tipo) tipo.value = a.tipo;
        note(ainote, 'Suggerito dall\'AI: controlla e correggi se serve.' + (a.tipo_nuovo ? ' Il tipo «' + a.tipo + '» è nuovo: finirà in Approvazioni per la scorta minima.' : ''), 'ok');
      }).catch(function (e) { note(ainote, 'Suggerimento AI non disponibile (' + e.message + '): scegli tu categoria e tipo.', 'warn'); });
    }
    box.appendChild(el('div', 'm', 'Il prodotto viene creato e caricato con la quantità e la posizione scelte qui sotto.'));
    var ok = el('button', 'btn primary', 'Conferma e salva'); ok.type = 'button'; box.appendChild(ok);
    var alt = el('button', 'alt', 'Non è questo prodotto: usa la foto'); alt.type = 'button'; box.appendChild(alt);
    if (st.ro) box.appendChild(el('div', 'note warn', 'L\'app è in sola lettura: il salvataggio è disattivato.'));
    alt.addEventListener('click', function () { hideProp(); setKnown(false); note($('hint'), NOTA_NUOVO, 'warn'); });
    ok.addEventListener('click', function () {
      if (!nome.value.trim()) { toast('Il nome è obbligatorio.', true); nome.focus(); return; }
      if (!cat.value || !sot.value) { toast('Scegli categoria e sottocategoria.', true); return; }
      ok.disabled = true;
      api('POST', 'api/prodotto', { barcode: bc, nome: nome.value.trim(), marca: r.marca, confezione: r.confezione, immagine: r.immagine, categoria: cat.value, sottocategoria: sot.value, tipo: tipo.value.trim(), composizione: r.composizione, nutrizione: r.nutrizione, punteggi: r.punteggi, fonte: r.fonte, location: st.luogo, quantita: st.qta })
        .then(function () { toast('Prodotto creato e movimento salvato.'); st.prod = null; st.stock = []; try { localStorage.removeItem('prodCache'); localStorage.removeItem('stockCache'); } catch (e) { /* ok */ } hideProp(); resetForm(); })
        .catch(function (e) { toast('Non salvato: ' + e.message, true); ok.disabled = false; });
    });
  }
  function altroLuogo(l) { return LUOGHI.filter(function (x) { return x !== l; })[0]; }
  function loadGiac(bc) {   // giacenze del prodotto: servono per Scarico, Sposta e Cambia categoria
    var fine = function (g, err) {
      if ($('bc').value.trim() !== bc) return;
      st.giac = g.filter(function (x) { return x.qta > 0; }); st.riga = 0;
      if (st.pre) { st.giac.forEach(function (x, i) { if (x.luogo === st.pre.luogo && (x.categoria || '') === st.pre.categoria) st.riga = i; }); st.pre = null; }
      st.errGiac = err || ''; renderRiga();
    };
    var daStock = function (err) {   // rete di sicurezza: se la scheda non risponde, la giacenza si legge dall'elenco Stock
      return api('GET', 'api/stock').then(function (r) {
        var righe = (r && r.items) || r || [];
        fine(righe.filter(function (x) { return String(x.barcode) === String(bc.replace(/^0+/, "")); }), err);
      }).catch(function (e2) { fine([], (err || '') + ' ' + e2.message); });
    };
    api('GET', 'api/scheda/' + bc).then(function (p) {
      if (p.giacenze && p.giacenze.length) fine(p.giacenze); else return daStock('');
    }).catch(function (e) { return daStock(e.message); });
    if (!st.cats) api('GET', 'api/categorie').then(function (c) { st.cats = c || []; renderRiga(); }).catch(function () { st.cats = []; });
  }
  function renderRiga() {
    var need = st.tipo !== 'Carico', box = $('riga'), g = st.giac[st.riga];
    $('f-luogo').hidden = need; $('f-riga').hidden = !need || st.known !== true; $('f-catnew').hidden = !(need && st.known === true && st.tipo === 'Cambia categoria' && g);
    if (!need || st.known !== true) return;
    box.textContent = '';
    st.giac.forEach(function (x, i) {
      var b = el('button', '', ''); b.type = 'button'; b.setAttribute('aria-pressed', String(i === st.riga));
      b.appendChild(el('span', '', [x.luogo, x.categoria].filter(Boolean).join(' · '))); b.appendChild(el('b', '', x.qta + ' pz'));
      b.addEventListener('click', function () { st.riga = i; renderRiga(); }); box.appendChild(b);
    });
    var n = $('rnote');
    if (!g) { note(n, st.errGiac ? 'Non riesco a leggere la giacenza (' + st.errGiac.trim() + ').' : 'Nessuna giacenza da movimentare per questo prodotto.', 'warn'); return; }
    if (st.tipo === 'Sposta') note(n, 'Sposto da ' + g.luogo + ' a ' + altroLuogo(g.luogo) + '.', '');
    else if (st.tipo === 'Cambia categoria') note(n, '', '');
    else note(n, '', '');
    if (st.tipo === 'Cambia categoria') {
      var sel = $('catnew'), prima = sel.value; sel.textContent = '';
      (st.cats || []).map(function (c) { return c.categoria; }).filter(function (c) { return c !== g.categoria; }).forEach(function (c) { var o = el('option', '', c); o.value = c; sel.appendChild(o); });
      if (prima) sel.value = prima;
    }
  }
  function resetForm() {
    hideProp(); st.giac = []; st.riga = 0; renderRiga();
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
    if (!/^\d{6,24}$/.test(bc)) { toast('Inserisci un barcode valido.', true); $('bc').focus(); return; }
    var btn = $('save'); btn.disabled = true;
    var go = st.known === null ? lookup() : Promise.resolve();
    go.then(function () {
      if (st.known === false && !st.fotoBlob) { toast('Per un codice nuovo serve la foto.', true); throw new Error('stop'); }
      return st.known === false ? api('POST', 'api/foto', undefined, undefined, (function () { var fd = new FormData(); fd.append('barcode', bc); fd.append('file', st.fotoBlob, 'foto.jpg'); return fd; })()).then(function (r) { return String(r.url || 'AI'); }) : '';
    }).then(function (foto) {
      var tipoVal = TIPI.filter(function (t) { return t[0] === st.tipo; })[0][1];
      var body = { barcode: bc, tipo: tipoVal, location: st.luogo, quantita: st.qta, prodotto: $('pr').value.trim(), foto: foto || undefined };
      if (st.tipo !== 'Carico') {
        var g = st.giac[st.riga];
        if (st.known !== true || !g) { toast('Serve un prodotto noto con giacenza.', true); throw new Error('stop'); }
        body.location = g.luogo; body.categoria = g.categoria;
        if (st.tipo === 'Sposta') body.destinazione = altroLuogo(g.luogo);
        if (st.tipo === 'Cambia categoria') { body.categoria_new = $('catnew').value; if (!body.categoria_new) { toast('Scegli la nuova categoria.', true); throw new Error('stop'); } }
      }
      return api('POST', 'api/movimento', body);
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
  function disegna(cv, src, sx, sy, sw, sh, k, ruota) {   // copia una parte dell'immagine, anche ruotata di 90 gradi (codici verticali)
    var w = Math.round(sw * k), h = Math.round(sh * k), c = cv.getContext('2d');
    if (!ruota) { cv.width = w; cv.height = h; c.drawImage(src, sx, sy, sw, sh, 0, 0, w, h); return; }
    cv.width = h; cv.height = w; c.setTransform(1, 0, 0, 1, 0, 0); c.translate(h, 0); c.rotate(Math.PI / 2); c.drawImage(src, sx, sy, sw, sh, 0, 0, w, h);
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
      var reader = Z ? zxReader(Z) : null, cv = document.createElement('canvas'), busy = false, fr = 0;
      if (useNative) detector = detector || new window.BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128', 'qr_code'] });
      return navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false }).then(function (s) {
        stream = s; var v = $('vid'); v.srcObject = s; $('scanbox').hidden = false; v.play();
        try { var tr = s.getVideoTracks()[0]; if (tr && tr.applyConstraints) tr.applyConstraints({ advanced: [{ focusMode: 'continuous' }] }).catch(function () {}); } catch (e) { /* ok */ }
        note($('hint'), 'Inquadra il codice a barre, tenendolo fermo e ben illuminato.', '');
        scanTimer = setInterval(function () {
          if (useNative) { detector.detect(v).then(function (c) { if (c && c.length) gotCode(c[0].rawValue); }).catch(function () {}); return; }
          if (!v.videoWidth || busy) return;
          busy = true; fr++;
          try {   // fotogrammi alterni: inquadratura intera e fascia centrale, per ciascuna anche ruotata di 90 gradi (codici in verticale)
            var W = v.videoWidth, H = v.videoHeight, sx = 0, sy = 0, sw = W, sh = H, f = fr % 4, rot = f >= 2;
            if (f === 1) { sx = Math.round(W * 0.05); sw = Math.round(W * 0.9); sy = Math.round(H * 0.25); sh = Math.round(H * 0.5); }   // fascia orizzontale
            if (f === 3) { sx = Math.round(W * 0.25); sw = Math.round(W * 0.5); sy = Math.round(H * 0.05); sh = Math.round(H * 0.9); }   // fascia verticale (ruotata)
            disegna(cv, v, sx, sy, sw, sh, Math.min(1, 1280 / Math.max(sw, sh)), rot);
            gotCode(zxDecode(Z, reader, cv));
          } catch (e) { /* nessun codice in questo fotogramma */ }
          busy = false;
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
          [false, true].forEach(function (ruota) {
            if (done) return;
            disegna(cv, img, 0, 0, img.width, img.height, k, ruota);
            try { var t = zxDecode(Z, reader, cv); done = true; note($('hint'), '', ''); gotCode(t); } catch (e) { /* riprova ruotando o con un'altra dimensione */ }
          });
        });
        if (!done) note($('hint'), 'Codice non riconosciuto: avvicinati, tieni il codice dritto e ben illuminato, poi riprova.', 'warn');
      }).catch(function () { note($('hint'), 'Non riesco a caricare il lettore: serve la connessione. Digita il codice.', 'warn'); })
        .then(function () { URL.revokeObjectURL(url); $('scanfile').value = ''; });
    };
    img.onerror = function () { note($('hint'), 'Foto non leggibile.', 'warn'); URL.revokeObjectURL(url); };
    img.src = url;
  }


  /* ---------- immagini senza sfondo bianco ---------- */
  var imgCache = {};
  var idbP = null;   // archivio persistente delle miniature gia elaborate (resta tra una apertura e l'altra)
  function idb() {
    if (!idbP) idbP = new Promise(function (ok) {
      try { var rq = indexedDB.open('miniature', 1); rq.onupgradeneeded = function () { rq.result.createObjectStore('i'); }; rq.onsuccess = function () { ok(rq.result); }; rq.onerror = function () { ok(null); }; } catch (e) { ok(null); }
    });
    return idbP;
  }
  function idbGet(k, cb) { idb().then(function (db) { if (!db) return cb(null); try { var r = db.transaction('i').objectStore('i').get(k); r.onsuccess = function () { cb(r.result || null); }; r.onerror = function () { cb(null); }; } catch (e) { cb(null); } }); }
  function idbPut(k, v) { idb().then(function (db) { try { if (db) db.transaction('i', 'readwrite').objectStore('i').put(v, k); } catch (e) { /* non salva: pazienza */ } }); }
  function cleanImg(url, cb) {
    if (imgCache[url]) { cb(imgCache[url]); return; }
    idbGet('v1|' + url, function (hit) { if (hit) { imgCache[url] = hit; cb(hit); } else cleanImg2(url, cb); });
  }
  function cleanImg2(url, cb) { // toglie il bianco collegato ai bordi; se l'immagine non e leggibile, usa l'originale
    var im = new Image(); im.crossOrigin = 'anonymous'; im.referrerPolicy = 'no-referrer';
    im.onload = function () {
      try {
        var k = Math.min(1, 120 / Math.max(im.width, im.height)), w = Math.max(1, Math.round(im.width * k)), h = Math.max(1, Math.round(im.height * k));
        var cv = document.createElement('canvas'); cv.width = w; cv.height = h;
        var cx = cv.getContext('2d'); cx.drawImage(im, 0, 0, w, h);
        var d = cx.getImageData(0, 0, w, h), px = d.data, seen = new Uint8Array(w * h), stack = [], i;
        function bianco(p) { var o = p * 4; return px[o + 3] < 20 || (px[o] > 232 && px[o + 1] > 232 && px[o + 2] > 232 && Math.max(px[o], px[o + 1], px[o + 2]) - Math.min(px[o], px[o + 1], px[o + 2]) < 18); }
        for (i = 0; i < w; i++) { stack.push(i, (h - 1) * w + i); }
        for (i = 0; i < h; i++) { stack.push(i * w, i * w + w - 1); }
        while (stack.length) {
          var p = stack.pop(); if (seen[p] || !bianco(p)) continue; seen[p] = 1; px[p * 4 + 3] = 0;
          var x = p % w; if (x > 0) stack.push(p - 1); if (x < w - 1) stack.push(p + 1); if (p >= w) stack.push(p - w); if (p < w * (h - 1)) stack.push(p + w);
        }
        cx.putImageData(d, 0, 0); imgCache[url] = cv.toDataURL('image/png'); idbPut('v1|' + url, imgCache[url]); cb(imgCache[url]);
      } catch (e) { imgCache[url] = url; cb(url); }
    };
    im.onerror = function () { cb(''); };
    im.src = url;
  }
  var lazyIO = ('IntersectionObserver' in window) ? new IntersectionObserver(function (es) {
    es.forEach(function (e) { if (e.isIntersecting) { lazyIO.unobserve(e.target); var u = e.target._u; e.target._u = null; if (u) thumb(e.target, u, true); } });
  }, { rootMargin: '300px' }) : null;
  function thumbLazy(box, url) { if (!lazyIO) { thumb(box, url, true); return; } box._u = url; lazyIO.observe(box); }
  function thumb(box, url, now) {
    cleanImg(url, function (u) { if (!u) return; var im = document.createElement('img'); im.src = u; im.alt = ''; box.appendChild(im); });
  }

  /* ---------- scheda prodotto ---------- */
  function secTxt(titolo, testo) { if (!testo) return null; var s = el('div', 'sc-sec'); s.appendChild(el('h3', '', titolo)); s.appendChild(el('p', '', testo)); return s; }
  function openScheda(barcode) {
    st.schedaBc = barcode; var box = $('sc-body'); box.textContent = 'Carico…'; $('scheda').hidden = false; $('sc-close').focus();
    api('GET', 'api/scheda/' + barcode).then(function (p) {
      box.textContent = '';
      var head = el('div', 'sc-head'), im = el('div', 'sc-img'), t = el('div', '');
      if (p.immagine) thumb(im, p.immagine);
      var h2 = el('h2', '', p.nome || 'Prodotto'); h2.id = 'sc-nome'; t.appendChild(h2);
      var m = [p.marca, p.confezione].filter(Boolean).join(' · '); if (m) t.appendChild(el('div', 'm', m));
      t.appendChild(el('div', 'm', 'Codice ' + p.barcode));
      head.appendChild(im); head.appendChild(t); box.appendChild(head);
      var pills = el('div', 'pills'); [p.tipo, p.categoria, p.sottocategoria].filter(Boolean).forEach(function (x) { pills.appendChild(el('span', '', x)); }); box.appendChild(pills);
      var g = el('div', 'sc-sec'); g.appendChild(el('h3', '', 'Giacenza'));
      (p.giacenze || []).forEach(function (x) { var r = el('div', 'sc-giac'); r.appendChild(el('span', '', [x.luogo, x.categoria].filter(Boolean).join(' · '))); r.appendChild(el('b', '', String(x.qta))); g.appendChild(r); });
      if (!(p.giacenze || []).length) g.appendChild(el('p', '', 'Nessuna giacenza.'));
      else { var tt = el('div', 'sc-giac tot'); tt.appendChild(el('span', '', 'Totale')); tt.appendChild(el('b', '', String(p.totale))); g.appendChild(tt); }
      if (p.scorta_minima > 0) g.appendChild(el('div', p.totale <= p.scorta_minima ? 'sc-low' : 'note', 'Scorta minima del tipo: ' + p.scorta_minima + (p.totale <= p.scorta_minima ? ' — sotto scorta' : '')));
      box.appendChild(g);
      if (!st.ro) { editSotto(box, p); if (p.tipo) editScorta(box, p); }
      [['Punteggi', p.punteggi && p.punteggi.split('|').map(function (x) { return x.trim(); }).filter(Boolean).join('\n')],
       ['Nutrizione (100 g)', p.nutrizione && p.nutrizione.split('|').map(function (x) { return x.trim(); }).filter(Boolean).join('\n')],
       ['Adatto a', p.free_from], ['Dettagli', p.dettagli], ['Composizione', p.composizione], ['Smaltimento e riciclo', p.smaltimento],
       ['Aggiornato il', p.aggiornato]].forEach(function (a) { var s = secTxt(a[0], a[1]); if (s) box.appendChild(s); });
    }).catch(function (e) { box.textContent = 'Scheda non disponibile: ' + e.message; });
  }
  function editScorta(box, p) {   // la scorta minima e del TIPO: vale per tutti i prodotti di quel tipo
    var s = el('div', 'sc-sec'); s.appendChild(el('h3', '', 'Scorta minima del tipo «' + p.tipo + '»'));
    var row = el('div', 'sc-edit'), inp = el('input', ''), ok = el('button', 'btn primary', 'Salva'); ok.type = 'button';
    inp.type = 'number'; inp.min = '0'; inp.max = '999'; inp.step = '1'; inp.inputMode = 'numeric'; inp.value = String(p.scorta_minima || 0); inp.setAttribute('aria-label', 'Scorta minima');
    row.appendChild(inp); row.appendChild(ok); s.appendChild(row);
    s.appendChild(el('p', 'note', 'Quando la giacenza totale del tipo scende a questo numero, finisce nella lista della spesa. Con 0 non compare mai.'));
    box.appendChild(s);
    ok.addEventListener('click', function () {
      ok.disabled = true;
      api('POST', 'api/tipi/scorta', { tipo: p.tipo, scorta: Number(inp.value) }).then(function (r) {
        toast('Scorta minima di «' + r.tipo + '»: ' + r.scorta_minima + '.'); st.stock = []; st.prod = null; try { localStorage.removeItem('prodCache'); localStorage.removeItem('stockCache'); } catch (e) { /* ok */ } openScheda(p.barcode);
      }).catch(function (e) { toast('Non salvato: ' + e.message, true); }).then(function () { ok.disabled = false; });
    });
  }
  function editSotto(box, p) {   // la sottocategoria e del prodotto: si cambia qui, non con un movimento
    var s = el('div', 'sc-sec'); s.appendChild(el('h3', '', 'Cambia sottocategoria'));
    var row = el('div', 'sc-edit'), sel = el('select', ''), ok = el('button', 'btn primary', 'Salva'); ok.type = 'button'; sel.setAttribute('aria-label', 'Nuova sottocategoria');
    row.appendChild(sel); row.appendChild(ok); s.appendChild(row); box.appendChild(s);
    (st.cats ? Promise.resolve(st.cats) : api('GET', 'api/categorie').then(function (c) { st.cats = c || []; return st.cats; })).then(function (cs) {
      var c = cs.filter(function (x) { return x.categoria === p.categoria; })[0];
      ((c && c.sottocategorie) || []).forEach(function (x) { var o = el('option', '', x); o.value = x; sel.appendChild(o); });
      sel.value = p.sottocategoria;
    });
    ok.addEventListener('click', function () {
      ok.disabled = true;
      api('PATCH', 'api/prodotto/' + p.barcode, { sottocategoria: sel.value }).then(function (r) { toast('Sottocategoria cambiata (' + r.movimenti_aggiornati + ' movimenti aggiornati).'); st.stock = []; st.prod = null; try { localStorage.removeItem('prodCache'); localStorage.removeItem('stockCache'); } catch (e) { /* ok */ } openScheda(p.barcode); })
        .catch(function (e) { toast('Non salvato: ' + e.message, true); }).then(function () { ok.disabled = false; });
    });
  }
  function closeScheda() { $('scheda').hidden = true; }

  /* ---------- stock ---------- */
  function loadStock() {
    if (!st.stock || !st.stock.length) { try { st.stock = JSON.parse(localStorage.getItem('stockCache') || 'null') || []; } catch (e) { st.stock = []; } if (st.stock.length) renderStock(); }   // subito la copia salvata
    api('GET', 'api/stock').then(function (r) {
      r = r || []; var nuovo = JSON.stringify(r), vecchio = JSON.stringify(st.stock || []);
      st.stock = r; $('sub').textContent = r.length + ' prodotti';
      if (nuovo !== vecchio || !$('stock').children.length) renderStock();   // non ridisegna se non e cambiato nulla
      try { localStorage.setItem('stockCache', nuovo); } catch (e) { /* spazio pieno: pazienza */ }
    }).catch(function (e) { toast('Stock non caricato: ' + e.message, true); });
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
        if (r.img) thumbLazy(th, r.img);
        it.appendChild(th); it.tabIndex = 0; it.setAttribute('role', 'button'); it.setAttribute('aria-label', 'Apri la scheda di ' + r.nome);
        (function (bc) { it.addEventListener('click', function () { openScheda(bc); }); it.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); openScheda(bc); } }); })(r.barcode);
        n.appendChild(el('b', '', r.nome));
        var sub = [r.marca, r.conf].filter(Boolean).join(' · '); if (sub) n.appendChild(el('span', 'sub2', sub));
        if (r.tipo) n.appendChild(el('span', 'tipo', r.tipo)); n.appendChild(el('span', '', [r.sotto, r.luogo].filter(Boolean).join(' · ')));
        it.appendChild(n); it.appendChild(el('span', 'badge' + (isLow(r) ? ' low' : ''), isLow(r) ? 'Sotto scorta' : 'Ok'));
        it.appendChild(el('div', 'qta', String(r.qta)));
        d.appendChild(swipeRiga(it, { right: { label: '+1 Carico', ok: function () { return !st.ro; }, fn: function () { movRapidoStock('Carico', r); } },
                                      left: { label: '−1 Scarico', ok: function () { return !st.ro && r.qta > 0; }, fn: function () { movRapidoStock('Scarico', r); } } }));
      });
      box.appendChild(d);
    });
  }


  /* ---------- elenco prodotti ---------- */
  function loadProd() {
    if (!st.prod) { try { st.prod = JSON.parse(localStorage.getItem('prodCache') || 'null'); } catch (e) { st.prod = null; } if (st.prod) renderProd(); }   // subito la copia salvata
    api('GET', 'api/prodotti').then(function (r) {
      r = r || []; var nuovo = JSON.stringify(r), vecchio = JSON.stringify(st.prod || []);
      st.prod = r; $('sub').textContent = r.length + ' prodotti';
      if (nuovo !== vecchio || !$('prodlist').children.length) renderProd();   // non ridisegna se non e cambiato nulla
      try { localStorage.setItem('prodCache', nuovo); } catch (e) { /* spazio pieno: pazienza */ }
    }).catch(function (e) { toast('Elenco non caricato: ' + e.message, true); });
  }
  var FILTRI_PROD = [['tutti', 'Tutti'], ['casa', 'In casa'], ['esauriti', 'Esauriti'], ['sotto', 'Sotto scorta']];
  var prodFiltro = (function () { try { var f = localStorage.getItem('prodFiltro'); return FILTRI_PROD.some(function (x) { return x[0] === f; }) ? f : 'tutti'; } catch (e) { return 'tutti'; } })();
  var prodCat = (function () { try { return localStorage.getItem('prodCat') || ''; } catch (e) { return ''; } })();
  function buildCatProd() {   // riga di categorie per isolare un solo reparto
    var box = $('prod-cat'); if (!box) return; box.textContent = '';
    var conta = {}; (st.prod || []).forEach(function (r) { var c = (r.categoria || '').trim() || 'Senza categoria'; conta[c] = (conta[c] || 0) + 1; });
    var nomi = Object.keys(conta).sort(function (x, y) { if (x === 'Senza categoria') return 1; if (y === 'Senza categoria') return -1; return x.localeCompare(y, 'it'); });
    if (prodCat && !conta[prodCat]) prodCat = '';
    [''].concat(nomi).forEach(function (c) {
      var b = el('button', 'chip', c ? c + ' ' + conta[c] : 'Tutte'); b.type = 'button'; b.setAttribute('aria-pressed', String(prodCat === c));
      b.addEventListener('click', function () { prodCat = c; try { localStorage.setItem('prodCat', c); } catch (e) { /* ok */ } buildCatProd(); renderProd(); });
      box.appendChild(b);
    });
  }
  function chiusiProd() { try { return JSON.parse(localStorage.getItem('prodChiusi') || '[]') || []; } catch (e) { return []; } }
  function salvaChiusiProd(k) { try { localStorage.setItem('prodChiusi', JSON.stringify(k)); } catch (e) { /* ok */ } }
  function buildFiltriProd() {
    var box = $('prod-flt'); box.textContent = '';
    FILTRI_PROD.forEach(function (o) {
      var b = el('button', 'chip', o[1]); b.type = 'button'; b.setAttribute('aria-pressed', String(prodFiltro === o[0]));
      b.addEventListener('click', function () { prodFiltro = o[0]; try { localStorage.setItem('prodFiltro', o[0]); } catch (e) { /* ok */ } buildFiltriProd(); renderProd(); }); box.appendChild(b);
    });
  }
  function sottoScorta(r) { return r.minima > 0 && (r.qta || 0) <= r.minima; }
  function righePosti(r) { return (r.posti || []).map(function (p) { return p.luogo + ' ' + p.qta; }).join(' · '); }
  function renderProd() {   // una sola vista: gruppi per tipo (A-Z, "Senza tipo" in fondo), prodotti in ordine alfabetico dentro il gruppo
    var q = $('qp2').value.trim().toLowerCase(), box = $('prodlist');
    box.textContent = ''; buildCatProd();
    var list = (st.prod || []).filter(function (r) {
      if (prodCat && ((r.categoria || '').trim() || 'Senza categoria') !== prodCat) return false;
      if (prodFiltro === 'casa' && !(r.qta > 0)) return false;
      if (prodFiltro === 'esauriti' && r.qta > 0) return false;
      if (prodFiltro === 'sotto' && !sottoScorta(r)) return false;
      return !q || [r.nome, r.marca, r.conf, r.categoria, r.sotto, r.tipo, String(r.barcode)].join(' ').toLowerCase().indexOf(q) >= 0;
    });
    var pezzi = 0, sotto = 0; list.forEach(function (r) { pezzi += r.qta || 0; if (sottoScorta(r)) sotto++; });
    $('prod-sum').textContent = list.length + ' prodotti · ' + pezzi + ' pezzi in casa' + (sotto ? ' · ' + sotto + ' sotto scorta' : '');
    if (!list.length) { box.appendChild(el('p', 'empty', 'Nessun prodotto trovato.')); return; }
    var gruppi = {}, chiavi = [];
    list.forEach(function (r) { var k = (r.tipo || '').trim() || 'Senza tipo'; if (!gruppi[k]) { gruppi[k] = []; chiavi.push(k); } gruppi[k].push(r); });
    chiavi.sort(function (x, y) { if (x === 'Senza tipo') return 1; if (y === 'Senza tipo') return -1; return x.localeCompare(y, 'it'); });
    var chiusi = chiusiProd(), frag = document.createDocumentFragment();
    chiavi.forEach(function (k) {
      var id = 'tipo:' + k, d = el('details', 'g'); d.open = !!q || chiusi.indexOf(id) < 0; d.dataset.k = id;
      var tot = 0; gruppi[k].forEach(function (r) { tot += r.qta || 0; });
      var sm = el('summary', ''); sm.appendChild(el('span', 'gn', k));
      var cn = el('span', 'gc', ''); cn.appendChild(el('b', '', tot + ' pz')); cn.appendChild(document.createTextNode(' · ' + gruppi[k].length + (gruppi[k].length === 1 ? ' prodotto' : ' prodotti'))); sm.appendChild(cn);
      d.appendChild(sm);
      d.addEventListener('toggle', function () { if (q) return; var c = chiusiProd().filter(function (x) { return x !== id; }); if (!d.open) c.push(id); salvaChiusiProd(c); });
      gruppi[k].forEach(function (r) {
        var it = el('div', 'item pr'), n = el('div', 'n'), th = el('div', 'th');
        if (r.img) thumbLazy(th, r.img);
        it.appendChild(th); it.tabIndex = 0; it.setAttribute('role', 'button'); it.setAttribute('aria-label', 'Apri la scheda di ' + r.nome);
        n.appendChild(el('b', '', r.nome));
        var l2 = [[r.marca, r.conf].filter(Boolean).join(' · '), righePosti(r)].filter(Boolean).join('  ·  ');
        if (l2) n.appendChild(el('span', 'm1', l2));
        var cs = [r.categoria, r.sotto].filter(Boolean).join(' › '); if (cs) n.appendChild(el('span', 'm2', cs));
        it.appendChild(n);
        var zero = !r.qta, low = !zero && sottoScorta(r), q2 = el('div', 'qp ' + (zero ? 'zero' : low ? 'low' : 'ok'));
        q2.appendChild(el('b', '', String(r.qta || 0))); q2.appendChild(el('small', '', 'pz'));
        if ((zero || low) && r.minima > 0) q2.appendChild(el('i', '', 'da comprare'));
        it.appendChild(q2);
        (function (bc) { it.addEventListener('click', function () { openScheda(bc); }); it.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); openScheda(bc); } }); })(r.barcode);
        d.appendChild(swipeRiga(it, { right: { label: '+1 Carico', ok: function () { return !st.ro; }, fn: function () { movRapidoProd('Carico', r); } },
                                      left: { label: '−1 Scarico', ok: function () { return !st.ro && r.qta > 0; }, fn: function () { movRapidoProd('Scarico', r); } } }));
      });
      frag.appendChild(d);
    });
    box.appendChild(frag);
  }
  function tuttiProd(apri) {
    var tutti = [];
    document.querySelectorAll('#prodlist details.g').forEach(function (d) { d.open = apri; if (!apri) tutti.push(d.dataset.k); });
    salvaChiusiProd(apri ? [] : tutti);
  }

  /* ---------- campi condivisi: categoria > sottocategoria, tipo ---------- */
  function ensureRef() {
    var a = st.cats ? Promise.resolve() : api('GET', 'api/categorie').then(function (c) { st.cats = c || []; }).catch(function () { st.cats = []; });
    var b = st.tipi ? Promise.resolve() : api('GET', 'api/tipi').then(function (t) { st.tipi = t || []; }).catch(function () { st.tipi = []; });
    return Promise.all([a, b]);
  }
  function campoTesto(box, label, val) {
    var w = el('label', 'fld'); w.appendChild(el('span', '', label));
    var i = el('input'); i.type = 'text'; i.value = val || ''; i.setAttribute('aria-label', label); w.appendChild(i); box.appendChild(w); return i;
  }
  function campiCatSot(box, cat0, sot0, tipo0) {   // ritorna {cat, sot, tipo}
    var wc = el('label', 'fld'); wc.appendChild(el('span', '', 'Categoria'));
    var cat = el('select'); cat.setAttribute('aria-label', 'Categoria'); wc.appendChild(cat);
    var ws = el('label', 'fld'); ws.appendChild(el('span', '', 'Sottocategoria'));
    var sot = el('select'); sot.setAttribute('aria-label', 'Sottocategoria'); ws.appendChild(sot);
    var o0 = el('option', '', 'Scegli la categoria'); o0.value = ''; cat.appendChild(o0);
    (st.cats || []).forEach(function (c) { var o = el('option', '', c.categoria); o.value = c.categoria; cat.appendChild(o); });
    function fill() {
      sot.textContent = '';
      var c = (st.cats || []).filter(function (x) { return x.categoria === cat.value; })[0];
      var o = el('option', '', cat.value ? 'Scegli la sottocategoria' : 'Scegli prima la categoria'); o.value = ''; sot.appendChild(o);
      ((c && c.sottocategorie) || []).forEach(function (s) { var p = el('option', '', s); p.value = s; sot.appendChild(p); });
    }
    cat.addEventListener('change', fill);
    cat.value = cat0 || ''; fill(); sot.value = sot0 || '';
    box.appendChild(wc); box.appendChild(ws);
    var tipo = campoTesto(box, 'Tipo', tipo0); tipo.setAttribute('list', 'tipi-dl');
    var dl = $('tipi-dl') || el('datalist'); dl.id = 'tipi-dl'; dl.textContent = '';
    (st.tipi || []).forEach(function (x) { var o = el('option'); o.value = x; dl.appendChild(o); }); box.appendChild(dl);
    return { cat: cat, sot: sot, tipo: tipo, fill: fill };
  }
  function azzeraCache() { st.stock = []; st.prod = null; try { localStorage.removeItem('prodCache'); localStorage.removeItem('stockCache'); } catch (e) { /* ok */ } }


  /* ---------- scorrimenti laterali (swipe) sulle righe ---------- */
  /* Swipe sulle righe, definiti dall'utente. Ogni pagina ha la sua definizione (azione a destra e a sinistra:
     { label, fn, ok?, prima?, conferma? }) nel punto in cui costruisce le righe, passata a swipeRiga().
     ok = l'azione e disponibile; prima = controllo prima dell'annulla (false = ferma); conferma = testo dell'annulla di 5 secondi,
     la scrittura sul foglio parte solo allo scadere. Ogni gesto ha anche un pulsante equivalente. */
  var SWIPE_RIGHE = { attivo: true };
  function swipeRiga(row, def) { return SWIPE_RIGHE.attivo ? swipeWrap(row, def) : row; }
  var SW_APRI = 92;   // larghezza dell'area azione quando la riga resta aperta (stile Apple Music)
  var swAperta = null, ultimoTouch = 0, swCont = { touchstart: 0, touchmove: 0, mousedown: 0, pointerdown: 0, wheel: 0 };
  function swGlobali() {   // una volta sola: un tocco fuori dalla riga aperta, o uno scroll, la richiude; contatori per la diagnostica
    if (swGlobali.fatto) return; swGlobali.fatto = true;
    Object.keys(swCont).forEach(function (n) { document.addEventListener(n, function () { swCont[n]++; }, { capture: true, passive: true }); });
    ['touchstart', 'mousedown'].forEach(function (n) {
      document.addEventListener(n, function (e) {
        if (n === 'mousedown' && Date.now() - ultimoTouch < 800) return;
        if (swAperta && !swAperta.wrap.contains(e.target)) swAperta.chiudi();
      }, { capture: true, passive: true });
    });
    window.addEventListener('scroll', function () { if (swAperta) swAperta.chiudi(); }, true);
  }
  function swEsegui(d) { if (!d) return; if (d.prima && d.prima() === false) return; if (d.conferma) conAnnulla(d.conferma, d.fn); else d.fn(); }
  function swipeWrap(row, o) {   // o.right / o.left = { label, fn, ok?, prima?, conferma? }; restituisce l'elemento da inserire al posto della riga
    swGlobali();
    var wrap = el('div', 'sw'), bg = el('div', 'sw-bg');
    function mk(lato) {
      var d = o[lato], b = el('button', 'sw-act ' + (lato === 'right' ? 'sw-r' : 'sw-l') + (d && /rifiut|scart/i.test(d.label) ? ' bad' : ''), d ? d.label : '');
      b.type = 'button'; b.tabIndex = -1; b.setAttribute('aria-hidden', 'true'); return b;
    }
    var bR = mk('right'), bL = mk('left');
    bg.appendChild(bR); bg.appendChild(bL);
    if (row.classList.contains('card')) wrap.classList.add('sw-card');
    row.classList.add('sw-fg'); wrap.appendChild(bg); wrap.appendChild(row);
    var x = 0, aperto = 0, att = false, drag = false, deciso = false, orizz = false, base = 0, x0 = 0, y0 = 0, traccia = [], blocca = 0, wacc = 0, wt = null;
    var api = { wrap: wrap, chiudi: function () { aperto = 0; applica(0, true); if (swAperta === api) swAperta = null; } };
    function azione(lato) { var d = o[lato]; return d && (!d.ok || d.ok()) ? d : null; }
    function largo() { return row.offsetWidth || 320; }
    function applica(v, anim) {
      x = v;
      row.style.transition = anim ? '' : 'none';
      row.style.transform = v ? 'translate3d(' + v + 'px,0,0)' : '';
      wrap.classList.toggle('mostra-r', v > 0); wrap.classList.toggle('mostra-l', v < 0);
      bR.style.width = Math.max(SW_APRI, v) + 'px'; bL.style.width = Math.max(SW_APRI, -v) + 'px';
      bR.setAttribute('aria-hidden', v > 0 ? 'false' : 'true'); bL.setAttribute('aria-hidden', v < 0 ? 'false' : 'true');
      bR.tabIndex = v > 0 ? 0 : -1; bL.tabIndex = v < 0 ? 0 : -1;
      wrap.classList.toggle('pronto', Math.abs(v) >= largo() * 0.6 && !!azione(v > 0 ? 'right' : 'left'));
    }
    function apri(lato) { aperto = lato === 'right' ? 1 : -1; applica(aperto * SW_APRI, true); swAperta = api; }
    function lancia(lato, d) {   // swipe lungo: la riga esce, poi parte l'azione
      applica((lato === 'right' ? 1 : -1) * largo(), true);
      setTimeout(function () { swEsegui(d); api.chiudi(); }, 170);
    }
    function inizio(cx, cy, target) {
      if (target && target.closest && target.closest('input,button,a,select,textarea,label')) return false;
      if (swAperta && swAperta !== api) swAperta.chiudi();
      x0 = cx; y0 = cy; base = x; deciso = false; orizz = false; drag = false; traccia = [[Date.now(), cx]];
      return true;
    }
    function muovi(cx, cy, ev) {
      var mx = cx - x0, my = cy - y0;
      if (!deciso) {
        if (Math.abs(mx) < 10 && Math.abs(my) < 10) return;
        deciso = true; orizz = Math.abs(mx) > Math.abs(my) * 1.2;   // gesto prevalentemente orizzontale: altrimenti e scroll verticale
        if (!orizz) { att = false; return; }
        drag = true; row.classList.add('drag');
      }
      if (!orizz) return;
      if (ev && ev.cancelable) ev.preventDefault();
      var v = base + mx, d = azione(v > 0 ? 'right' : 'left'), max = largo() * 0.92;
      v = d ? Math.max(-max, Math.min(max, v)) : Math.max(-14, Math.min(14, v / 6));   // senza azione disponibile: solo un cenno
      traccia.push([Date.now(), cx]); if (traccia.length > 6) traccia.shift();
      applica(v, false);
    }
    function fine(annullato) {
      if (!att) return; att = false;
      if (!drag) return;   // tocco semplice
      drag = false; row.classList.remove('drag'); blocca = Date.now();
      if (annullato) { if (aperto) applica(aperto * SW_APRI, true); else applica(0, true); return; }
      var n = traccia.length, vel = n > 1 ? (traccia[n - 1][1] - traccia[0][1]) / Math.max(1, traccia[n - 1][0] - traccia[0][0]) : 0;   // px/ms
      var proj = x + vel * 70, lato = proj > 0 ? 'right' : 'left', d = azione(lato), w = largo();
      if (d && Math.abs(x) >= w * 0.6) { lancia(lato, d); return; }   // swipe lungo: solo se la riga e davvero arrivata oltre il 60%
      if (d && Math.abs(proj) >= Math.min(w * 0.25, 80)) { apri(lato); return; }
      api.chiudi();
    }
    // tocco (iPhone / iPad)
    row.addEventListener('touchstart', function (e) { ultimoTouch = Date.now(); att = e.touches.length === 1 && inizio(e.touches[0].clientX, e.touches[0].clientY, e.target); }, { passive: true });
    row.addEventListener('touchmove', function (e) { ultimoTouch = Date.now(); if (att && e.touches[0]) muovi(e.touches[0].clientX, e.touches[0].clientY, e); }, { passive: false });
    row.addEventListener('touchend', function (e) { ultimoTouch = Date.now(); if (att && drag && e.cancelable) e.preventDefault(); fine(false); }, { passive: false });
    row.addEventListener('touchcancel', function () { ultimoTouch = Date.now(); fine(true); }, { passive: true });
    // mouse (Mac): mousedown sulla riga, poi move/up sul documento
    function mm(e) { muovi(e.clientX, e.clientY, e); }
    function mu() { document.removeEventListener('mousemove', mm, true); document.removeEventListener('mouseup', mu, true); fine(false); }
    row.addEventListener('mousedown', function (e) {
      if (e.button !== 0 || Date.now() - ultimoTouch < 800) return;
      att = inizio(e.clientX, e.clientY, e.target); if (!att) return;
      document.addEventListener('mousemove', mm, true); document.addEventListener('mouseup', mu, true);
    });
    row.addEventListener('dragstart', function (e) { e.preventDefault(); });
    // trackpad (Mac): scorrimento orizzontale a due dita, come in Mail
    row.addEventListener('wheel', function (e) {
      if (Math.abs(e.deltaX) < Math.abs(e.deltaY) * 1.2 || Math.abs(e.deltaX) < 2) return;
      e.preventDefault(); swChiudiAltre();
      if (!att) { att = true; drag = true; orizz = true; deciso = true; base = x; wacc = 0; traccia = [[Date.now(), 0]]; row.classList.add('drag'); }
      wacc -= e.deltaX; var d = azione((base + wacc) > 0 ? 'right' : 'left'), max = largo() * 0.92, v = base + wacc;
      v = d ? Math.max(-max, Math.min(max, v)) : Math.max(-14, Math.min(14, v / 6));
      traccia.push([Date.now(), wacc]); if (traccia.length > 6) traccia.shift(); applica(v, false);
      clearTimeout(wt); wt = setTimeout(function () { fine(false); }, 140);
    }, { passive: false });
    function swChiudiAltre() { if (swAperta && swAperta !== api) swAperta.chiudi(); }
    // i pulsanti dietro la riga
    bR.addEventListener('click', function () { var d = azione('right'); api.chiudi(); swEsegui(d); });
    bL.addEventListener('click', function () { var d = azione('left'); api.chiudi(); swEsegui(d); });
    // un tocco sulla riga aperta la richiude (senza aprire la scheda); dopo un trascinamento il rilascio non vale come tocco
    row.addEventListener('click', function (e) {
      if (!e.isTrusted) return;
      if (Date.now() - blocca < 400) { e.stopPropagation(); e.preventDefault(); return; }
      if (aperto) { e.stopPropagation(); e.preventDefault(); api.chiudi(); }
    }, true);
    return wrap;
  }
  var undoT = null, undoFn = null;
  function conAnnulla(msg, fn) {   // azione con 5 secondi per annullare: la scrittura sul foglio parte solo se non si annulla
    if (undoFn) { clearTimeout(undoT); var prima = undoFn; undoFn = null; prima(); }
    var box = $('undo'); box.textContent = ''; box.appendChild(el('span', '', msg));
    var b = el('button', '', 'Annulla'); b.type = 'button'; box.appendChild(b); box.hidden = false;
    undoFn = fn;
    undoT = setTimeout(function () { box.hidden = true; var f = undoFn; undoFn = null; if (f) f(); }, 5000);
    b.addEventListener('click', function () { clearTimeout(undoT); undoFn = null; box.hidden = true; toast('Annullato.'); });
  }


  document.addEventListener('visibilitychange', function () { if (document.hidden && undoFn) { clearTimeout(undoT); var f = undoFn; undoFn = null; $('undo').hidden = true; f(); } });   // l'app va in secondo piano: meglio scrivere subito che perdere l'azione
  function scegli(titolo, voci, cb) {   // piccolo menu per scegliere una voce (es. in quale posizione scaricare)
    var vecchio = document.getElementById('pick'); if (vecchio) vecchio.remove();
    var bg = el('div', ''); bg.id = 'pick'; bg.setAttribute('role', 'dialog'); bg.setAttribute('aria-label', titolo);
    var box = el('div', 'pk'); box.appendChild(el('h3', '', titolo));
    function chiudi() { bg.remove(); }
    voci.forEach(function (v) { var b = el('button', 'btn', v.label); b.type = 'button'; b.addEventListener('click', function () { chiudi(); cb(v.valore); }); box.appendChild(b); });
    var x = el('button', 'btn ghost', 'Chiudi'); x.type = 'button'; x.addEventListener('click', chiudi); box.appendChild(x);
    bg.addEventListener('click', function (e) { if (e.target === bg) chiudi(); });
    bg.appendChild(box); document.body.appendChild(bg); var p = box.querySelector('button'); if (p) p.focus();
  }
  function scriviMov(tipo, r) {   // Carico/Scarico di 1 sulla riga di stock r {barcode, luogo, categoria, nome}
    return api('POST', 'api/movimento', { barcode: String(r.barcode), tipo: tipo, location: r.luogo || 'Casa', quantita: 1, categoria: r.categoria || '', prodotto: r.nome || '' })
      .then(function () { azzeraCache(); toast((tipo === 'Carico' ? 'Caricato 1' : 'Scaricato 1') + (r.nome ? ' · ' + r.nome : '') + '.'); if (st.tab === 'stock') loadStock(); else if (st.tab === 'prod') loadProd(); })
      .catch(function (e) { toast('Non riuscito: ' + e.message, true); });
  }
  function movRapidoStock(tipo, r) {   // riga di stock nota: 5 secondi per annullare, poi scrive
    if (st.ro) { toast('Sola lettura: nessuna modifica.', true); return; }
    if (tipo === 'Scarico' && !(r.qta > 0)) { toast('Giacenza a zero: niente da scaricare.', true); return; }
    conAnnulla((tipo === 'Carico' ? 'Carico 1 · ' : 'Scarico 1 · ') + r.nome + (r.luogo ? ' (' + [r.luogo, r.categoria].filter(Boolean).join(' · ') + ')' : '') + '…', function () { scriviMov(tipo, r); });
  }
  function movRapidoProd(tipo, p) {   // elenco prodotti: usa la riga di stock principale; se ce ne sono piu di una chiede quale
    if (st.ro) { toast('Sola lettura: nessuna modifica.', true); return; }
    if (tipo === 'Scarico' && !(p.qta > 0)) { toast('Giacenza a zero: niente da scaricare.', true); return; }
    api('GET', 'api/scheda/' + p.barcode).then(function (sc) {
      var righe = (sc.giacenze || []).filter(function (x) { return tipo === 'Carico' || x.qta > 0; })
        .map(function (x) { return { barcode: p.barcode, nome: p.nome, luogo: x.luogo, categoria: x.categoria, qta: x.qta }; });
      if (!righe.length) righe = [{ barcode: p.barcode, nome: p.nome, luogo: 'Casa', categoria: p.categoria || '', qta: 0 }];   // mai stato in giacenza: carico a Casa
      if (righe.length === 1) { movRapidoStock(tipo, righe[0]); return; }
      scegli((tipo === 'Carico' ? 'Carica 1 dove?' : 'Scarica 1 da dove?') + ' ' + p.nome, righe.map(function (x) { return { label: [x.luogo, x.categoria].filter(Boolean).join(' · ') + ' — ' + x.qta, valore: x }; }),
        function (x) { movRapidoStock(tipo, x); });
    }).catch(function (e) { toast('Non riuscito: ' + e.message, true); });
  }
  function bottoniRapidi(riga, onMeno, onPiu, dis) {   // pulsanti equivalenti ai due scorrimenti
    var w = el('div', 'rapidi'), m = el('button', 'rp', '−1'), p = el('button', 'rp', '+1');
    m.type = p.type = 'button'; m.title = 'Scarica 1'; p.title = 'Carica 1'; m.setAttribute('aria-label', 'Scarica 1: ' + riga.nome); p.setAttribute('aria-label', 'Carica 1: ' + riga.nome);
    m.disabled = !!dis || !(riga.qta > 0); p.disabled = !!dis;
    m.addEventListener('click', function (e) { e.stopPropagation(); onMeno(); }); p.addEventListener('click', function (e) { e.stopPropagation(); onPiu(); });
    m.addEventListener('keydown', function (e) { e.stopPropagation(); }); p.addEventListener('keydown', function (e) { e.stopPropagation(); });
    w.appendChild(m); w.appendChild(p); return w;
  }

  /* ---------- spesa ---------- */
  function carrello() { try { return JSON.parse(localStorage.getItem('carrello') || '{}') || {}; } catch (e) { return {}; } }
  function salvaCarrello(c) { try { localStorage.setItem('carrello', JSON.stringify(c)); } catch (e) { /* ok */ } }
  function loadSpesa() {
    api('GET', 'api/spesa').then(function (s) { renderSpesa(s || { voci: [] }); })
      .catch(function (e) { toast('Spesa non caricata: ' + e.message, true); });
  }
  var spFiltro = 'Tutti';
  function listaIOS(voci) {   // tutte le voci da comprare e non ancora nel carrello, una per riga
    var car = carrello(), righe = voci.filter(function (v) { return !car[v.tipo]; }).map(function (v) { return v.tipo; });
    if (!righe.length) { toast('Niente da aggiungere: tutto è già nel carrello.'); return; }
    var testo = righe.join('\n');
    var ios = /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    function ripiego() {
      if (navigator.share) { navigator.share({ title: 'Lista della spesa', text: testo }).catch(function () { /* annullato */ }); return; }
      if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard.writeText(testo).then(function () { toast('Elenco copiato: incollalo in Promemoria.'); }, function () { toast('Non riesco a copiare l\'elenco.', true); }); return; }
      toast('Il dispositivo non permette di condividere l\'elenco.', true);
    }
    if (!ios) { ripiego(); return; }
    var a2 = document.createElement('a'); a2.href = 'shortcuts://run-shortcut?name=' + encodeURIComponent(st.shortcut || 'Spesa AppSheet') + '&input=text&text=' + encodeURIComponent(testo);
    a2.target = '_top'; a2.rel = 'noopener'; document.body.appendChild(a2); a2.click(); document.body.removeChild(a2);
    toast('Aggiungo ' + righe.length + (righe.length === 1 ? ' voce' : ' voci') + ' ai Promemoria…');
  }
  function oggi() { var d = new Date(); return d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate(); }
  function nascosteOggi() { try { var o = JSON.parse(localStorage.getItem('spesaNascoste') || 'null'); return (o && o.g === oggi() && Array.isArray(o.t)) ? o.t : []; } catch (e) { return []; } }
  function salvaNascoste(t) { try { localStorage.setItem('spesaNascoste', JSON.stringify({ g: oggi(), t: t })); } catch (e) { /* ok */ } }
  function chiusiSpesa() { try { return JSON.parse(localStorage.getItem('spesaChiusi') || '[]') || []; } catch (e) { return []; } }
  function renderSpesa(s) {
    var box = $('spesa-list'), top = $('spesa-top'), car = carrello(); box.textContent = ''; top.textContent = '';
    var tutte = s.voci || [], nasc = nascosteOggi();
    var voci = tutte.filter(function (v) { return nasc.indexOf(v.tipo) < 0; });
    s = Object.assign({}, s, { voci: voci, finiti: voci.filter(function (v) { return v.stato === 'FINITO'; }).length, in_esaurimento: voci.filter(function (v) { return v.stato !== 'FINITO'; }).length });
    var nCar = voci.filter(function (v) { return car[v.tipo]; }).length, nDa = voci.length - nCar;
    $('sub').textContent = voci.length ? nDa + ' da comprare' + (nCar ? ' · ' + nCar + ' nel carrello' : '') : 'Niente da comprare';
    setStk();
    var nNasc = tutte.length - voci.length;
    function ripristina() {
      if (!nNasc) return null;
      var b = el('button', 'btn ghost sp-ripr', 'Rimetti in lista le ' + nNasc + ' tolte oggi'); b.type = 'button';
      b.addEventListener('click', function () { salvaNascoste([]); renderSpesa(Object.assign({}, s, { voci: tutte })); loadSpesa(); }); return b;
    }
    if (!voci.length) { box.appendChild(el('p', 'empty', nNasc ? 'Hai tolto tutto dalla lista per oggi.' : 'Scorte a posto: niente da comprare.')); var rp0 = ripristina(); if (rp0) box.appendChild(rp0); return; }
    var ch = el('div', 'chips'); ch.setAttribute('role', 'group'); ch.setAttribute('aria-label', 'Filtro');
    [['Tutti', voci.length], ['Finiti', s.finiti || 0], ['In esaurimento', s.in_esaurimento || 0]].forEach(function (f) {
      var b = el('button', 'chip', f[0] + ' ' + f[1]); b.type = 'button'; b.setAttribute('aria-pressed', String(spFiltro === f[0]));
      b.addEventListener('click', function () { spFiltro = f[0]; renderSpesa(s); }); ch.appendChild(b);
    });
    top.appendChild(ch);
    var ios = el('button', 'btn ghost sp-ios', 'Aggiungi alla lista della spesa di iOS'); ios.type = 'button';
    ios.addEventListener('click', function () { listaIOS(voci); });
    box.appendChild(ios);
    box.appendChild(el('div', 'note sp-nota', 'Manda a Promemoria le voci non ancora nel carrello, tramite il comando rapido «' + (st.shortcut || 'Spesa AppSheet') + '».'));
    setStk();
    var gruppi = {}, ordine = [];
    voci.filter(function (v) { return spFiltro === 'Tutti' || (spFiltro === 'Finiti') === (v.stato === 'FINITO'); }).forEach(function (v) {
      var k = v.categoria || 'Altro'; if (!gruppi[k]) { gruppi[k] = []; ordine.push(k); } gruppi[k].push(v);
    });
    var chiusi = chiusiSpesa();
    ordine.forEach(function (g) {
      var d = el('details', 'g'); d.open = chiusi.indexOf(g) < 0;
      d.appendChild(el('summary', '', g + ' (' + gruppi[g].length + ')'));
      d.addEventListener('toggle', function () { var k = chiusiSpesa().filter(function (x) { return x !== g; }); if (!d.open) k.push(g); try { localStorage.setItem('spesaChiusi', JSON.stringify(k)); } catch (e) { /* ok */ } });
      gruppi[g].forEach(function (v) {
        var fin = v.stato === 'FINITO', row = el('div', 'sp-row' + (car[v.tipo] ? ' done' : ''));
        var lab = el('label', 'sp-chk'); var chk = el('input'); chk.type = 'checkbox'; chk.checked = !!car[v.tipo]; chk.setAttribute('aria-label', 'Nel carrello: ' + v.tipo);
        chk.addEventListener('change', function () { var k = carrello(); if (chk.checked) k[v.tipo] = 1; else delete k[v.tipo]; salvaCarrello(k); renderSpesa(s); });
        lab.appendChild(chk); row.appendChild(lab);
        var th = el('div', 'th'); if (v.immagine) thumbLazy(th, v.immagine); row.appendChild(th);
        var n = el('div', 'n'); n.appendChild(el('b', '', v.tipo)); if (v.sottocategoria) n.appendChild(el('span', '', v.sottocategoria)); row.appendChild(n);
        var q = el('span', 'sp-q ' + (fin ? 'zero' : 'low'), v.giacenza + ' / ' + v.minima); q.title = (fin ? 'Finito' : 'In esaurimento') + ' · ' + (v.dettaglio || ''); row.appendChild(q);
        var ok = el('button', 'sp-plus', '+1'); ok.type = 'button'; ok.title = 'Comprato +1: lo carica a Casa'; ok.setAttribute('aria-label', 'Comprato, carica 1 a Casa: ' + v.tipo);
        ok.disabled = st.ro || !v.barcode;
        ok.addEventListener('click', function () {
          ok.disabled = true;
          api('POST', 'api/movimento', { barcode: String(v.barcode), tipo: 'Carico', location: 'Casa', quantita: 1, prodotto: v.prodotto || '' }).then(function () {
            var k = carrello(); delete k[v.tipo]; salvaCarrello(k); azzeraCache(); toast('Caricato 1 a Casa.'); loadSpesa();
          }).catch(function (e) { ok.disabled = false; toast('Non riuscito: ' + e.message, true); });
        });
        row.appendChild(ok);
        var x = el('button', 'sp-x', '✕'); x.type = 'button'; x.title = 'Togli dalla lista per oggi'; x.setAttribute('aria-label', 'Togli dalla lista per oggi: ' + v.tipo);
        function togli() { var n = nascosteOggi(); if (n.indexOf(v.tipo) < 0) n.push(v.tipo); salvaNascoste(n); toast('«' + v.tipo + '» tolto dalla lista per oggi.'); renderSpesa(s); }
        x.addEventListener('click', togli); row.appendChild(x);
        d.appendChild(swipeRiga(row, { right: { label: '+1 Comprato', ok: function () { return !ok.disabled; }, fn: function () { ok.click(); } },
                                       left: { label: 'Togli per oggi', fn: togli } }));
      });
      box.appendChild(d);
    });
    if (!ordine.length) box.appendChild(el('p', 'empty', 'Nessuna voce in questo filtro.'));
    var rp = ripristina(); if (rp) box.appendChild(rp);
  }

  /* ---------- da inserire (bozze) ---------- */
  function loadBozze() {
    ensureRef().then(function () { return api('GET', 'api/bozze'); }).then(function (l) { renderBozze(l || []); })
      .catch(function (e) { toast('Bozze non caricate: ' + e.message, true); });
  }
  function renderBozze(list) {
    var box = $('bozze-list'); box.textContent = '';
    $('sub').textContent = list.length ? list.length + (list.length === 1 ? ' prodotto da completare' : ' prodotti da completare') : 'Niente da inserire';
    if (!list.length) { box.appendChild(el('p', 'empty', 'Nessun prodotto in attesa di essere inserito.')); return; }
    list.forEach(function (b) {
      var c = el('article', 'card');
      c.appendChild(el('h2', '', b.nome || ('Codice ' + b.barcode)));
      c.appendChild(el('div', 'm', 'Codice ' + b.barcode + ' · ' + b.movimento + ' ' + b.quantita + ' a ' + b.location + (b.fonte ? ' · ' + b.fonte : '')));
      if (b.nota) c.appendChild(el('div', 'why', b.nota));
      if (b.foto) { var a = el('a', 'm', 'Apri la foto'); a.href = b.foto; a.target = '_blank'; a.rel = 'noopener'; c.appendChild(a); }
      var nome = campoTesto(c, 'Nome', b.nome), marca = campoTesto(c, 'Marca', b.marca), conf = campoTesto(c, 'Confezione', b.confezione);
      var f = campiCatSot(c, b.categoria, b.sottocategoria, b.tipo);
      var nt = el('div', 'note', ''); c.appendChild(nt);
      function campi() { return { nome: nome.value.trim(), marca: marca.value.trim(), confezione: conf.value.trim(), categoria: f.cat.value, sottocategoria: f.sot.value, tipo: f.tipo.value.trim() }; }
      var bt = el('div', 'btns'), cerca = el('button', 'btn', 'Cerca e suggerisci'), salva = el('button', 'btn', 'Salva bozza'),
        ok = el('button', 'btn ok', "Aggiungi all'inventario"), no = el('button', 'btn bad', 'Scarta');
      [cerca, salva, ok, no].forEach(function (x) { x.type = 'button'; bt.appendChild(x); });
      ok.disabled = salva.disabled = no.disabled = st.ro;
      var base = 'api/bozze/' + encodeURIComponent(b.id) + '/';
      function blocca(v) { [cerca, salva, ok, no].forEach(function (x) { x.disabled = v || (st.ro && x !== cerca); }); }
      cerca.addEventListener('click', function () {   // completa solo i campi vuoti; se non trova nulla non cambia niente
        blocca(true); note(nt, 'Cerco nei database e chiedo all\'AI…');
        api('GET', 'api/cerca/' + encodeURIComponent(b.barcode)).catch(function () { return { found: false }; }).then(function (r) {
          if (r && r.found) { if (!nome.value.trim() && r.nome) nome.value = r.nome; if (!marca.value.trim() && r.marca) marca.value = r.marca; if (!conf.value.trim() && r.confezione) conf.value = r.confezione; }
          return api('POST', 'api/suggerisci', { nome: nome.value.trim(), marca: marca.value.trim(), confezione: conf.value.trim() }).then(function (a) {
            if (a && a.ai) {
              if (!f.cat.value && a.categoria) { f.cat.value = a.categoria; f.fill(); if (!f.sot.value && a.sottocategoria) f.sot.value = a.sottocategoria; }
              if (!f.tipo.value.trim() && a.tipo) f.tipo.value = a.tipo;
              note(nt, (r && r.found ? 'Trovato su ' + r.fonte + '. ' : 'Non trovato nei database. ') + 'Suggerimento AI inserito: controlla.', 'ok');
            } else note(nt, (r && r.found ? 'Trovato su ' + r.fonte + '. ' : 'Non trovato nei database. ') + 'L\'AI non ha risposto: completa a mano.', 'warn');
          });
        }).catch(function (e) { note(nt, 'Ricerca non riuscita: ' + e.message, 'warn'); }).then(function () { blocca(false); });
      });
      salva.addEventListener('click', function () {
        blocca(true);
        api('POST', base + 'salva', { campi: campi() }).then(function () { toast('Bozza salvata.'); }).catch(function (e) { toast('Non salvata: ' + e.message, true); }).then(function () { blocca(false); });
      });
      ok.addEventListener('click', function () {
        var k = campi();
        if (!k.nome) { toast('Il nome è obbligatorio.', true); nome.focus(); return; }
        if (!k.categoria || !k.sottocategoria) { toast('Scegli categoria e sottocategoria.', true); return; }
        blocca(true);
        api('POST', base + 'conferma', { campi: k }).then(function () { toast('Prodotto inserito.'); azzeraCache(); loadBozze(); })
          .catch(function (e) { blocca(false); toast('Non inserito: ' + e.message, true); });
      });
      no.addEventListener('click', function () {
        blocca(true);
        api('POST', base + 'scarta', {}).then(function () { toast('Bozza scartata.'); loadBozze(); }).catch(function (e) { blocca(false); toast('Non riuscito: ' + e.message, true); });
      });
      c.appendChild(bt);
      function aggiungiSwipe() {   // completa = nome, categoria e sottocategoria; altrimenti avvisa e porta al primo campo mancante
        var mancante = !nome.value.trim() ? nome : !f.cat.value ? f.cat : !f.sot.value ? f.sot : null;
        if (mancante) { if (navigator.vibrate) { try { navigator.vibrate(60); } catch (e) { /* ok */ } } toast('Completa prima i campi.', true); try { mancante.scrollIntoView({ block: 'center' }); mancante.focus(); } catch (e) { /* ok */ } return; }
        if (!ok.disabled) ok.click();
      }
      box.appendChild(swipeRiga(c, { right: { label: '＋ Aggiungi all\'inventario', ok: function () { return !st.ro; }, fn: aggiungiSwipe },
                                     left: { label: 'Scarta', ok: function () { return !no.disabled; }, conferma: 'Scarto «' + (b.nome || b.barcode) + '»…', fn: function () { if (!no.disabled) no.click(); } } }));
    });
  }

  /* ---------- approvazioni ---------- */
  function loadAppr() {
    ensureRef().then(function () { return api('GET', 'api/approvazioni'); }).then(function (list) { renderAppr(list || []); })
      .catch(function (e) { toast('Approvazioni non caricate: ' + e.message, true); });
  }
  function renderAppr(list) {
    var box = $('appr'); box.textContent = '';
    $('sub').textContent = list.length ? list.length + (list.length === 1 ? ' proposta in attesa' : ' proposte in attesa') : 'Nessuna proposta in attesa';
    if (!list.length) { box.appendChild(el('p', 'empty', 'Tutto approvato.')); return; }
    list.forEach(function (a) {
      var c = el('article', 'card'), pd = function (cls, k, v) { var r = el('div', 'pd ' + cls); r.appendChild(el('div', 'k', k)); r.appendChild(el('div', 'v', v)); return r; };
      c.appendChild(el('h2', '', a.titolo + (a.sicurezza != null ? ' · sicura al ' + a.sicurezza + '%' : '')));
      if (a.prima) c.appendChild(pd('prima', 'ATTUALE', a.prima));
      c.appendChild(pd('dopo', 'NUOVO', a.dopo));
      if (a.motivo) c.appendChild(el('div', 'why', a.motivo));
      var K = a.campi || {}, ed = null, nome, f, scorta;
      var form = el('div', 'edit'); form.hidden = true;
      if (a.genere === 'P') { nome = campoTesto(form, 'Nome', K.nome); f = campiCatSot(form, K.categoria, K.sottocategoria, K.tipo); }
      else if (a.genere === 'T') { scorta = campoTesto(form, 'Scorta minima', K.scorta_min == null ? 0 : K.scorta_min); scorta.type = 'number'; scorta.min = '0'; }
      c.appendChild(form);
      var bt = el('div', 'btns'), ok = el('button', 'btn ok', 'Approva'), cor = el('button', 'btn', 'Correggi'), no = el('button', 'btn bad', 'Rifiuta');
      [ok, cor, no].forEach(function (x) { x.type = 'button'; bt.appendChild(x); });
      if (a.genere === 'C') cor.hidden = true;
      function leggi() {
        if (a.genere === 'P') return { nome: nome.value.trim(), categoria: f.cat.value, sottocategoria: f.sot.value, tipo: f.tipo.value.trim() };
        if (a.genere === 'T') return { scorta_min: Number(scorta.value || 0) };
        return {};
      }
      function invia(azione, campi, msg) {
        [ok, cor, no].forEach(function (x) { x.disabled = true; });
        api('POST', 'api/approvazioni/' + encodeURIComponent(a.id), { azione: azione, campi: campi }).then(function () {
          toast(msg); azzeraCache(); loadAppr();
        }).catch(function (e) { [ok, cor, no].forEach(function (x) { x.disabled = false; }); toast('Non riuscito: ' + e.message, true); });
      }
      function valido() {
        if (a.genere === 'T' && !(Number(scorta.value) >= 0)) { toast('La scorta minima non può essere negativa.', true); form.hidden = false; return false; }
        if (a.genere === 'P' && (!f.cat.value || !f.sot.value)) { toast('Scegli categoria e sottocategoria (tocca Correggi).', true); form.hidden = false; return false; }
        return true;
      }
      ok.addEventListener('click', function () { if (valido()) invia('APPROVA', leggi(), 'Approvata.'); });
      cor.addEventListener('click', function () { form.hidden = !form.hidden; cor.textContent = form.hidden ? 'Correggi' : 'Chiudi correzione'; });
      no.addEventListener('click', function () { invia('RIFIUTA', {}, 'Rifiutata.'); });
      c.appendChild(bt);
      box.appendChild(swipeRiga(c, {
        right: { label: '✓ Approva', ok: function () { return !ok.disabled; }, prima: valido, conferma: 'Approvo «' + a.titolo + '»…', fn: function () { if (!ok.disabled) invia('APPROVA', leggi(), 'Approvata.'); } },
        left: { label: 'Rifiuta', ok: function () { return !no.disabled; }, conferma: 'Rifiuto «' + a.titolo + '»…', fn: function () { if (!no.disabled) no.click(); } } }));
    });
  }


  /* ---------- scorrimento sulla barra in basso: cambia pagina ---------- */
  function navInd(extra, anim) {   // indicatore sotto la scheda attiva (come la tab bar di iOS): segue il dito durante lo swipe
    var nav = $('nav'), ind = $('nav-ind'), b = nav && nav.querySelector('button[aria-current=page]');
    if (!ind || !b) return;
    ind.style.width = b.offsetWidth + 'px'; ind.style.transition = anim === false ? 'none' : '';
    ind.style.transform = 'translate3d(' + (b.offsetLeft + (extra || 0)) + 'px,0,0)';
  }
  function swipeNav() {
    var nav = $('nav'), att = false, deciso = false, orizz = false, x0 = 0, y0 = 0, mx = 0, blocca = 0, traccia = [];
    var ids = [];
    function vicino(dir) { ids = idVisibili(); var n = ids.indexOf(st.tab) + dir; return n >= 0 && n < ids.length ? n : -1; }
    function inizio(cx, cy) { att = true; deciso = false; orizz = false; mx = 0; x0 = cx; y0 = cy; traccia = [[Date.now(), cx]]; }
    function muovi(cx, cy, ev) {
      var dx = cx - x0, dy = cy - y0;
      if (!deciso) {
        if (Math.abs(dx) < 10 && Math.abs(dy) < 10) return;
        deciso = true; orizz = Math.abs(dx) > Math.abs(dy) * 1.2;
        if (!orizz) { att = false; return; }
      }
      if (!orizz) return;
      if (ev && ev.cancelable) ev.preventDefault();
      mx = dx; traccia.push([Date.now(), cx]); if (traccia.length > 6) traccia.shift();
      var bw = (nav.querySelector('button') || {}).offsetWidth || 60, dir = dx < 0 ? 1 : -1;   // verso sinistra = pagina successiva
      var e = vicino(dir) < 0 ? -dx / 8 : Math.max(-bw, Math.min(bw, -dx * (bw / 140)));
      navInd(Math.max(-bw, Math.min(bw, e)), false);
    }
    function fine(annullato) {
      if (!att) return; att = false;
      if (!orizz) return;
      orizz = false; blocca = Date.now();
      var n = traccia.length, vel = n > 1 ? (traccia[n - 1][1] - traccia[0][1]) / Math.max(1, traccia[n - 1][0] - traccia[0][0]) : 0, proj = mx + vel * 120;
      var dir = proj < 0 ? 1 : -1, t = vicino(dir);
      if (!annullato && Math.abs(proj) >= 40 && t >= 0) show(ids[t]); else navInd(0, true);
    }
    nav.addEventListener('touchstart', function (e) { ultimoTouch = Date.now(); if (e.touches.length === 1) inizio(e.touches[0].clientX, e.touches[0].clientY); else att = false; }, { passive: true });
    nav.addEventListener('touchmove', function (e) { ultimoTouch = Date.now(); if (att && e.touches[0]) muovi(e.touches[0].clientX, e.touches[0].clientY, e); }, { passive: false });
    nav.addEventListener('touchend', function (e) { ultimoTouch = Date.now(); if (att && orizz && e.cancelable) e.preventDefault(); fine(false); }, { passive: false });
    nav.addEventListener('touchcancel', function () { ultimoTouch = Date.now(); fine(true); }, { passive: true });
    function mm(e) { muovi(e.clientX, e.clientY, e); }
    function mu() { document.removeEventListener('mousemove', mm, true); document.removeEventListener('mouseup', mu, true); fine(false); }
    nav.addEventListener('mousedown', function (e) {
      if (e.button !== 0 || Date.now() - ultimoTouch < 800) return;
      inizio(e.clientX, e.clientY); document.addEventListener('mousemove', mm, true); document.addEventListener('mouseup', mu, true);
    });
    nav.addEventListener('click', function (e) { if (e.isTrusted && Date.now() - blocca < 400) { e.stopPropagation(); e.preventDefault(); } }, true);
    window.addEventListener('resize', function () { navInd(0, false); });
    navInd(0, false);
  }
  function hintSwipe(vid) {   // suggerimento discreto, chiudibile e ricordato
    try { if (localStorage.getItem('swHint')) return; } catch (e) { /* ok */ }
    var v = $(vid); if (!v || v.querySelector('.sw-hint')) return;
    var h = el('div', 'sw-hint'), b = el('button', '', '✕'); b.type = 'button'; b.setAttribute('aria-label', 'Chiudi il suggerimento');
    h.appendChild(el('span', '', 'Suggerimento: scorri una riga verso sinistra per −1 (Scarico) o verso destra per +1 (Carico).')); h.appendChild(b);
    b.addEventListener('click', function () { try { localStorage.setItem('swHint', '1'); } catch (e) { /* ok */ } h.remove(); });
    v.insertBefore(h, v.firstChild);
  }
  function diagnosiGesti() {   // tocco lungo 3 s sul titolo: mostra se gli eventi di tocco e mouse arrivano
    var t = $('title'), tm = null;
    function via() { clearTimeout(tm); }
    function parti() {
      via(); tm = setTimeout(function () {
        var box = el('div', 'diag');
        box.appendChild(el('b', '', 'Diagnostica gesti'));
        box.appendChild(el('div', '', 'touchstart ' + swCont.touchstart + ' · touchmove ' + swCont.touchmove + ' · mousedown ' + swCont.mousedown + ' · pointerdown ' + swCont.pointerdown + ' · wheel ' + swCont.wheel));
        box.appendChild(el('div', '', 'ontouchstart: ' + ('ontouchstart' in window) + ' · maxTouchPoints: ' + (navigator.maxTouchPoints || 0) + ' · righe swipe: ' + document.querySelectorAll('.sw-fg').length));
        box.appendChild(el('div', '', String(navigator.userAgent).slice(0, 110)));
        var ok = el('button', 'btn', 'Chiudi'); ok.type = 'button'; ok.addEventListener('click', function () { box.remove(); }); box.appendChild(ok);
        document.body.appendChild(box);
      }, 3000);
    }
    t.addEventListener('touchstart', parti, { passive: true }); t.addEventListener('touchend', via, { passive: true }); t.addEventListener('touchcancel', via, { passive: true });
    t.addEventListener('mousedown', function () { if (Date.now() - ultimoTouch > 800) parti(); }); t.addEventListener('mouseup', via); t.addEventListener('mouseleave', via);
  }

  /* ---------- avvio ---------- */
  function init() {
    api('GET', 'api/config').then(function (c) { st.ro = !c || c.sola_lettura !== false; st.ai = !!(c && c.ai); st.shortcut = (c && c.shortcut_spesa) || 'Spesa AppSheet'; var ex = document.getElementById('esci'); if (ex) ex.hidden = !(c && c.diretto); }).catch(function () { st.ro = true; });
    window.addEventListener('resize', setStk); window.addEventListener('load', setStk);
    buildNav(); swipeNav(); diagnosiGesti(); buildSeg('tipo', TIPI, 'tipo'); buildSeg('luogo', LUOGHI, 'luogo'); buildChips(); setQta(1);
    $('qm').addEventListener('click', function () { setQta(st.qta - 1); });
    $('qp').addEventListener('click', function () { setQta(st.qta + 1); });
    $('scan').addEventListener('click', startScan); $('sc-close').addEventListener('click', closeScheda); buildFiltriProd(); $('prod-chiudi').addEventListener('click', function () { tuttiProd(false); }); $('prod-apri').addEventListener('click', function () { tuttiProd(true); }); $('qp2').addEventListener('input', renderProd); $('sc-mov').addEventListener('click', function () { var bc = st.schedaBc; closeScheda(); show('mov'); if (bc) { $('bc').value = bc; lookup(); } }); document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape' && !$('scheda').hidden) closeScheda(); }); $('scanfile').addEventListener('change', function (e) { scanPhoto(e.target.files[0]); }); $('scanstop').addEventListener('click', stopScan);
    $('cancel').addEventListener('click', function () { stopScan(); resetForm(); });
    $('f').addEventListener('submit', save);
    var dbt;
    $('bc').addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); lookup().then(function () { (st.known === false ? $('pr') : $('save')).focus(); }); } });
    $('bc').addEventListener('input', function () { clearTimeout(dbt); setKnown(null); if (/^\d{8,24}$/.test($('bc').value.trim())) dbt = setTimeout(lookup, 450); });
    $('bc').addEventListener('change', lookup);
    $('file').addEventListener('change', function () {
      var f = $('file').files[0]; if (!f) return;
      resizeImage(f).then(function (b) { st.fotoBlob = b; var p = $('prev'); p.src = URL.createObjectURL(b); p.hidden = false; });
    });
    $('q').addEventListener('input', renderStock);
    show('mov');
    (function () {   // collegamento diretto allo scanner: ?scan=1 o #scan, anche dall'indirizzo del pannello di Home Assistant (stessa origine)
      function chiede(w) { try { return /(^|[?&#])scan(=1|=true)?($|&)/.test(w.location.search + w.location.hash) || /scan/.test(w.location.hash); } catch (e) { return false; } }
      if (chiede(window) || chiede(window.parent)) setTimeout(function () { try { startScan(); } catch (e) { /* ok */ } }, 400);
    })();
    if ('serviceWorker' in navigator && location.protocol !== 'file:') navigator.serviceWorker.register('sw.js').catch(function () {});
  }
  init();
})();
