/* I miei codici a barre: etichetta EAN-13 (da salvare o condividere) e schermata «I miei codici» nelle Impostazioni. */
(function () {
  'use strict';
  var L = ['0001101', '0011001', '0010011', '0111101', '0100011', '0110001', '0101111', '0111011', '0110111', '0001011'];
  var G = ['0100111', '0110011', '0011011', '0100001', '0011101', '0111001', '0000101', '0010001', '0001001', '0010111'];
  var R = ['1110010', '1100110', '1101100', '1000010', '1011100', '1001110', '1010000', '1000100', '1001000', '1110100'];
  var PAR = ['LLLLLL', 'LLGLGG', 'LLGGLG', 'LLGGGL', 'LGLLGG', 'LGGLLG', 'LGGGLL', 'LGLGLG', 'LGLGGL', 'LGGLGL'];
  function moduli(c) {   // 95 moduli: bordo 101, sei cifre a sinistra, centro 01010, sei a destra, bordo 101
    var p = PAR[+c[0]], s = '101', i;
    for (i = 1; i <= 6; i++) s += (p[i - 1] === 'L' ? L : G)[+c[i]];
    s += '01010';
    for (i = 7; i <= 12; i++) s += R[+c[i]];
    return s + '101';
  }
  function cifraControllo(d12) { var t = 0; for (var i = 0; i < 12; i++) t += (+d12[i]) * (i % 2 ? 3 : 1); return String((10 - t % 10) % 10); }
  function valido(c) { return /^\d{13}$/.test(c) && cifraControllo(c.slice(0, 12)) === c[12]; }
  window.eanModuli = moduli; window.eanValido = valido;

  /* disegna l'etichetta: nome in alto, barre, cifre sotto (formato EAN: 1 + 6 + 6). Ritorna un canvas bianco ad alta risoluzione. */
  function disegna(codice, nome) {
    var m = 4, quiet = 11 * m, W = (95 + 22) * m, barre = 150, testoH = 34, nomeH = nome ? 64 : 12, H = nomeH + barre + testoH + 14;
    var cv = document.createElement('canvas'); cv.width = W; cv.height = H;
    var g = cv.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, W, H);
    g.fillStyle = '#000'; g.textAlign = 'center';
    if (nome) {
      g.font = '600 26px -apple-system, Helvetica, Arial, sans-serif'; var righe = [], parole = String(nome).split(/\s+/), r = '';
      parole.forEach(function (w) { var t = r ? r + ' ' + w : w; if (g.measureText(t).width > W - 30 && r) { righe.push(r); r = w; } else r = t; });
      if (r) righe.push(r);
      righe = righe.slice(0, 2); righe.forEach(function (t, i) { g.fillText(t, W / 2, 30 + i * 28); });
    }
    var s = moduli(codice), y0 = nomeH;
    for (var i = 0; i < s.length; i++) {
      if (s[i] !== '1') continue;
      var guardia = i < 3 || (i >= 45 && i < 50) || i >= 92;   // le barre di bordo e centrali scendono un po' sotto le altre
      g.fillRect(quiet + i * m, y0, m, barre + (guardia ? 10 : 0));
    }
    g.font = '30px "Courier New", monospace';
    g.fillText(codice[0], quiet / 2 + 6, y0 + barre + 28);
    g.fillText(codice.slice(1, 7), quiet + (3 + 21) * m, y0 + barre + 28);
    g.fillText(codice.slice(7), quiet + (50 + 21) * m, y0 + barre + 28);
    return cv;
  }
  window.eanEtichetta = disegna;

  function el(t, c, x) { var e = document.createElement(t); if (c) e.className = c; if (x !== undefined) e.textContent = x; return e; }
  function formatta(c) { return !c ? '' : (/^PERS/.test(c) ? c : c[0] + ' ' + c.slice(1, 7) + ' ' + c.slice(7)); }

  /* foglio con l'etichetta: anteprima, salva immagine, condividi */
  function foglioEtichetta(codice, titolo, testo, alt, sorgente, stampa, extra) {   // extra: function(corpo, imposta) per i controlli sopra l'anteprima (imposta(blob) cambia l'immagine)   // stampa: funzione(bottone) che manda l'etichetta alla X1, oppure null   // sorgente: canvas oppure Blob PNG già pronto
    var old = document.getElementById('etichetta'); if (old) old.remove();
    var ov = el('div'); ov.id = 'etichetta'; ov.setAttribute('role', 'dialog'); ov.setAttribute('aria-modal', 'true');
    var bar = el('div', 'sc-bar'), x = el('button', 'sq', '←'); x.type = 'button'; x.setAttribute('aria-label', 'Chiudi'); bar.appendChild(x); bar.appendChild(el('b', '', titolo));
    var corpo = el('div', 'sc-body etic-corpo'), foot = el('div', 'sc-foot');
    ov.appendChild(bar); ov.appendChild(corpo); ov.appendChild(foot); document.body.appendChild(ov);
    var img = el('img', 'etic-img'); img.alt = alt; var blob = null;
    if (extra) extra(corpo, function (b) { blob = b; if (b) img.src = URL.createObjectURL(b); });
    corpo.appendChild(img); corpo.appendChild(el('p', 'm', testo));
    var nomeFile = 'etichetta-' + codice + '.png';
    if (sorgente.toBlob) sorgente.toBlob(function (b) { blob = b; if (b) img.src = URL.createObjectURL(b); }, 'image/png');
    else { blob = sorgente; img.src = URL.createObjectURL(sorgente); }
    var salva = el('button', 'btn', 'Salva immagine'), cond = el('button', 'btn', 'Condividi / Stampa');
    if (stampa) {   // stampa diretta sulla X1 tramite il servizio di Home Assistant
      var st = el('button', 'btn primary etic-stampa', 'Stampa con la X1'); st.type = 'button'; foot.appendChild(st);
      st.addEventListener('click', function () { stampa(st); });
    } else salva.className = 'btn primary';
    [salva, cond].forEach(function (b) { b.type = 'button'; foot.appendChild(b); });
    var esito = el('p', 'm', ''); corpo.appendChild(esito);
    function dì(t) { esito.textContent = t; }
    function condividi() {   // foglio di condivisione di sistema (da lì: Salva immagine, AirDrop, Stampa…)
      try {
        var f = new File([blob], nomeFile, { type: 'image/png' });
        if (navigator.canShare && navigator.canShare({ files: [f] })) { navigator.share({ files: [f], title: 'Etichetta ' + codice }).catch(function () { /* annullato */ }); return true; }
      } catch (e) { /* ok */ }
      return false;
    }
    function copia() {
      try {
        if (navigator.clipboard && window.ClipboardItem) { navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]).then(function () { dì('Immagine copiata: incollala dove vuoi (Pagine, Anteprima, Note) e stampa.'); }, function () { dì('Copia non riuscita: tieni premuta l\'immagine (o clic destro) e scegli «Salva immagine».'); }); return; }
      } catch (e) { /* ok */ }
      dì('Tieni premuta l\'immagine (o clic destro) e scegli «Salva immagine».');
    }
    salva.textContent = 'Salva / Condividi'; cond.textContent = 'Copia immagine';
    salva.addEventListener('click', function () {
      if (!blob) return;
      if (condividi()) return;
      // senza condivisione di sistema (es. alcuni browser desktop): scarico; nelle app che bloccano il download resta la copia
      var a = document.createElement('a'); a.href = img.src; a.download = nomeFile; document.body.appendChild(a); a.click(); setTimeout(function () { a.remove(); }, 500);
      dì('Se il download non parte, usa «Copia immagine» oppure clic destro sull\'immagine → «Salva immagine».');
    });
    cond.addEventListener('click', function () { if (blob) copia(); });
    x.addEventListener('click', function () { ov.remove(); });
  }
  window.mostraEtichetta = function (codice, nome) {
    if (!valido(String(codice))) return;
    foglioEtichetta(codice, 'Etichetta del codice', 'Codice ' + formatta(String(codice)) + '. Stampala o attaccala sul prodotto: la fotocamera dell\'app la legge come un codice normale.', 'Codice a barre ' + codice, disegna(String(codice), nome || ''));
  };

  /* etichetta per la stampante termica (12 x 40 mm): la compone il server (QR + nome + posizione) */
  window.mostraEtichettaStampante = function (barcode, api, toast) {
    var memo = {}; try { memo = JSON.parse(localStorage.getItem('etichetta_opz') || '{}'); } catch (e) { /* ok */ }
    var o = { posiz: memo.posiz !== false, codice: !!memo.codice, usadata: !!memo.usadata, tipo: memo.tipo === 'prod' ? 'prod' : 'scad', usalotto: !!memo.usalotto, usaicona: !!memo.usaicona, icona: memo.icona || 'dolce', data: '', lotto: '' };
    function salvaOpz() { try { localStorage.setItem('etichetta_opz', JSON.stringify({ posiz: o.posiz, codice: o.codice, usadata: o.usadata, tipo: o.tipo, usalotto: o.usalotto, usaicona: o.usaicona, icona: o.icona })); } catch (e) { /* ok */ } }
    function query() {
      var q = ['posiz=' + (o.posiz ? 1 : 0), 'codice=' + (o.codice ? 1 : 0)];
      if (o.usadata && o.data) q.push('data=' + encodeURIComponent(o.data), 'tipo_data=' + o.tipo);
      if (o.usalotto && o.lotto.trim()) q.push('lotto=' + encodeURIComponent(o.lotto.trim()));
      if (o.usaicona) q.push('icona=' + o.icona);
      return '?' + q.join('&');
    }
    function png(r) { var bin = atob(r.png), a = new Uint8Array(bin.length), i; for (i = 0; i < bin.length; i++) a[i] = bin.charCodeAt(i); return new Blob([a], { type: 'image/png' }); }
    api('GET', 'api/etichetta/' + encodeURIComponent(barcode) + query()).then(function (r) {
      var imposta = null, tempo = null;
      function rigenera() {   // ridisegna l'anteprima dopo ogni scelta (con una breve attesa mentre si scrive)
        clearTimeout(tempo);
        tempo = setTimeout(function () {
          api('GET', 'api/etichetta/' + encodeURIComponent(barcode) + query()).then(function (n) { if (imposta) imposta(png(n)); })
            .catch(function (e) { toast('Etichetta non aggiornata: ' + e.message, true); });
        }, 250);
      }
      function flag(box, testo, chiave, extraEl) {
        var riga = el('div', 'etic-riga'), lab = el('label', 'etic-flag'), c = document.createElement('input');
        c.type = 'checkbox'; c.checked = !!o[chiave]; lab.appendChild(c); lab.appendChild(el('span', '', testo)); riga.appendChild(lab);
        if (extraEl) { riga.appendChild(extraEl); extraEl.style.display = c.checked ? '' : 'none'; }
        c.addEventListener('change', function () { o[chiave] = c.checked; if (extraEl) extraEl.style.display = c.checked ? '' : 'none'; salvaOpz(); rigenera(); });
        box.appendChild(riga);
      }
      function controlli(corpo, imp) {
        imposta = imp;
        var box = el('div', 'card etic-opz'); box.appendChild(el('b', '', 'Cosa stampare'));
        box.appendChild(el('div', 'm', 'Nome e QR ci sono sempre.'));
        flag(box, 'Posizione', 'posiz');
        flag(box, 'Numero del codice sotto il QR', 'codice');
        var dv = el('span', 'etic-extra'), sel = document.createElement('select'), di = document.createElement('input');
        [['scad', 'Scade il'], ['prod', 'Prodotto il']].forEach(function (t) { var op = el('option', '', t[1]); op.value = t[0]; sel.appendChild(op); }); sel.value = o.tipo;
        di.type = 'date'; di.setAttribute('aria-label', 'Data'); o.data = new Date().toISOString().slice(0, 10); di.value = o.data;
        sel.addEventListener('change', function () { o.tipo = sel.value; salvaOpz(); rigenera(); });
        di.addEventListener('input', function () { o.data = di.value; rigenera(); });
        dv.appendChild(sel); dv.appendChild(di); flag(box, 'Data', 'usadata', dv);
        var lv = el('span', 'etic-extra'), li = document.createElement('input');
        li.type = 'text'; li.maxLength = 12; li.placeholder = 'es. 3'; li.setAttribute('aria-label', 'Lotto'); li.addEventListener('input', function () { o.lotto = li.value; rigenera(); });
        lv.appendChild(li); flag(box, 'Lotto', 'usalotto', lv);
        var iv = el('span', 'etic-extra'), isel = document.createElement('select');
        [['dolce', '♥ Dolce'], ['freddo', '❄ Surgelato'], ['frutta', '✿ Frutta/verdura'], ['bevanda', '☕ Bevanda'], ['speciale', '★ Speciale']].forEach(function (t) { var op = el('option', '', t[1]); op.value = t[0]; isel.appendChild(op); }); isel.value = o.icona;
        isel.addEventListener('change', function () { o.icona = isel.value; salvaOpz(); rigenera(); });
        iv.appendChild(isel); flag(box, 'Icona', 'usaicona', iv);
        corpo.appendChild(box);
      }
      var stampa = !r.stampante ? null : function (b) {
        b.disabled = true; var t0 = b.textContent; b.textContent = 'Stampo…';
        api('POST', 'api/stampa/' + encodeURIComponent(barcode) + query()).then(function () { toast('Etichetta inviata alla stampante.'); })
          .catch(function (e) { toast('Non stampata: ' + e.message, true); })
          .then(function () { b.disabled = false; b.textContent = t0; });
      };
      foglioEtichetta(r.barcode, 'Etichetta per la stampante', 'Rotolo da 12 × 40 mm (203 DPI). Il QR contiene il codice ' + r.barcode + ': l\'app lo legge con la fotocamera.' + (r.stampante ? ' «Stampa con la X1» la manda alla stampante collegata a Home Assistant (accesa e vicina al Raspberry).' : ' Salvala in Foto e importala in XeasyLabel, oppure collega la stampante nelle opzioni dell\'add-on.'), 'Etichetta di ' + (r.nome || r.barcode), png(r), stampa, controlli);
    }).catch(function (e) { toast('Etichetta non creata: ' + e.message, true); });
  };

  /* prodotti fatti in casa: chat con l'AI (primo messaggio gia scritto: basta premere Invia) e salvataggio delle stime nella scheda */
  window.chatAiCasa = function (barcode, api, toast, aggiorna) {
    var old = document.getElementById('chat-ai'); if (old) old.remove();
    var ov = el('div'); ov.id = 'chat-ai'; ov.setAttribute('role', 'dialog'); ov.setAttribute('aria-modal', 'true');
    var bar = el('div', 'sc-bar'), x = el('button', 'sq', '←'); x.type = 'button'; x.setAttribute('aria-label', 'Chiudi'); bar.appendChild(x); bar.appendChild(el('b', '', 'Chiedi all\'AI'));
    var corpo = el('div', 'sc-body chat-corpo'), foot = el('div', 'chat-foot');
    var ta = document.createElement('textarea'); ta.rows = 6; ta.setAttribute('aria-label', 'Messaggio per l\'AI'); ta.disabled = true; ta.value = 'Preparo il messaggio…';
    var invia = el('button', 'btn primary', 'Invia'); invia.type = 'button'; invia.disabled = true;
    var copia = el('button', 'btn', 'Copia'); copia.type = 'button'; copia.title = 'Copia il messaggio per usarlo in un\'altra app di AI';
    var rig = el('div', 'chat-btn'); rig.appendChild(copia); rig.appendChild(invia);
    foot.appendChild(ta); foot.appendChild(rig);
    ov.appendChild(bar); ov.appendChild(corpo); ov.appendChild(foot); document.body.appendChild(ov);
    corpo.appendChild(el('p', 'm', 'Stime indicative per un prodotto fatto in casa: ingredienti, valori per 100 g, conservazione. Il messaggio è già pronto (puoi modificarlo): premi Invia. Quello che l\'AI propone si salva nella scheda solo se lo confermi.'));
    var msgs = [], occupato = false;
    function bolla(chi, testo) { var b = el('div', 'chat-msg ' + chi); b.textContent = testo; corpo.appendChild(b); b.scrollIntoView({ block: 'end' }); return b; }
    function proposta(sc) {   // cosa verrebbe scritto nella scheda: si vede e si conferma
      var c = el('div', 'card chat-salva'); c.appendChild(el('b', '', 'Salvare nella scheda?'));
      [['Ingredienti', sc.composizione], ['Valori per 100 g', sc.nutrizione], ['Note', sc.dettagli]].forEach(function (r) { if (r[1]) { var d = el('div', 'm'); d.textContent = r[0] + ': ' + r[1].replace(/^🧪 Ingredienti:\s*/, ''); c.appendChild(d); } });
      c.appendChild(el('div', 'm', 'Sostituisce quello che c\'è ora in questi campi. Sono stime indicative.'));
      var ok = el('button', 'btn primary', 'Salva nella scheda'); ok.type = 'button'; c.appendChild(ok); corpo.appendChild(c); c.scrollIntoView({ block: 'end' });
      ok.addEventListener('click', function () {
        ok.disabled = true;
        api('PATCH', 'api/prodotto/' + encodeURIComponent(barcode) + '/info', { composizione: sc.composizione, nutrizione: sc.nutrizione, dettagli: sc.dettagli, tieni_note: true })
          .then(function () { toast('Scheda aggiornata.'); ov.remove(); if (aggiorna) aggiorna(); })
          .catch(function (e) { toast('Non salvato: ' + e.message, true); ok.disabled = false; });
      });
    }
    invia.addEventListener('click', function () {
      var t = ta.value.trim(); if (!t || occupato) return;
      occupato = true; invia.disabled = true; ta.value = ''; msgs.push({ ruolo: 'utente', testo: t }); var mio = bolla('io', t);
      var att = bolla('ai', 'L\'AI sta scrivendo…');
      api('POST', 'api/ai/casa', { barcode: barcode, messaggi: msgs }).then(function (r) {
        att.textContent = r.testo.replace(/```json[\s\S]*?(```|$)/g, '').trim() || r.testo; msgs.push({ ruolo: 'ai', testo: r.testo });
        if (r.scheda) proposta(r.scheda);
      }).catch(function (e) { mio.remove(); att.remove(); toast('Non riuscito: ' + e.message, true); msgs.pop(); ta.value = t; })
        .then(function () { occupato = false; invia.disabled = false; });
    });
    copia.addEventListener('click', function () {
      var t = ta.value; try { navigator.clipboard.writeText(t).then(function () { toast('Messaggio copiato.'); }, function () { ta.select(); toast('Selezionato: copia a mano.'); }); } catch (e) { ta.select(); }
    });
    x.addEventListener('click', function () { ov.remove(); });
    api('GET', 'api/ai/casa/' + encodeURIComponent(barcode)).then(function (r) {
      ta.value = r.prompt; ta.disabled = false; invia.disabled = !r.ai;
      if (!r.ai) corpo.appendChild(el('p', 'note warn', 'L\'AI integrata è spenta (manca la chiave Gemini): puoi copiare il messaggio e usarlo in un\'altra app.'));
    }).catch(function (e) { ta.value = ''; toast('Non posso preparare il messaggio: ' + e.message, true); });
  };

  /* modifica a mano di ingredienti, valori per 100 g e note di un mio prodotto */
  window.editInfoCasa = function (box, p, api, toast, ricarica) {
    var f = el('div', 'sc-sec edit'); f.appendChild(el('h3', '', 'Ingredienti, valori e note'));
    function area(label, val, righe, hint) {
      var w = el('label', 'fld'); w.appendChild(el('span', '', label)); var t = document.createElement('textarea'); t.rows = righe; t.value = val || ''; t.setAttribute('aria-label', label); w.appendChild(t);
      if (hint) w.appendChild(el('small', 'm', hint)); f.appendChild(w); return t;
    }
    var ing = area('Ingredienti (e allergeni)', (p.composizione || '').replace(/^🧪\s*Ingredienti:\s*/i, ''), 3, 'Es.: albicocche, zucchero — ⚠️ Allergeni: nessuno');
    var nut = area('Valori per 100 g', p.nutrizione, 2, 'Es.: 🔥 250 kcal  |  🫙 0.2 g grassi  |  🍬 60 g zuccheri  |  🧂 0 g sale');
    var det = area('Note e dettagli', p.dettagli, 3, 'Separa le voci con | (conservazione, durata, data di preparazione…)');
    var ok = el('button', 'btn primary', 'Salva'); ok.type = 'button'; f.appendChild(ok); box.appendChild(f);
    ok.addEventListener('click', function () {
      ok.disabled = true;
      api('PATCH', 'api/prodotto/' + encodeURIComponent(p.barcode) + '/info', { composizione: ing.value, nutrizione: nut.value, dettagli: det.value })
        .then(function () { toast('Salvato.'); if (ricarica) ricarica(); }).catch(function (e) { toast('Non salvato: ' + e.message, true); ok.disabled = false; });
    });
  };

  /* schermata «I miei codici» nelle Impostazioni */
  window.IMP_EXTRA = window.IMP_EXTRA || {};
  window.IMP_EXTRA.cod = function (det, ctx) {
    var api = ctx.api, toast = ctx.toast;
    var c = el('div', 'card'); c.appendChild(el('p', 'm', 'Codici tuoi per prodotti senza codice a barre (fatti in casa, sfusi, freschi). Sono nel formato PERS + 9 cifre casuali: non esistono in nessun archivio e non vengono mai cercati online, quindi la scheda prodotto la compili tu a mano. Non si ripetono mai, nemmeno se togli il prodotto.'));
    var nome = el('input'); nome.type = 'text'; nome.placeholder = 'Nome del prodotto (facoltativo)'; nome.maxLength = 80; nome.setAttribute('aria-label', 'Nome del nuovo codice');
    var nuovo = el('button', 'btn primary', 'Crea un nuovo codice'); nuovo.type = 'button';
    c.appendChild(nome); c.appendChild(nuovo); det.appendChild(c);
    var lista = el('div', 'cod-lista'); det.appendChild(lista);
    function carica() {
      api('GET', 'api/codici').then(function (l) {
        lista.textContent = '';
        if (!l.length) { lista.appendChild(el('p', 'm', 'Non hai ancora creato codici.')); return; }
        l.forEach(function (v) {
          var r = el('div', 'card cod-voce'), nm = el('input'); nm.type = 'text'; nm.value = v.nome || ''; nm.placeholder = 'Senza nome'; nm.maxLength = 80; nm.setAttribute('aria-label', 'Nome');
          nm.addEventListener('change', function () { api('POST', 'api/codici/nome', { codice: v.codice, nome: nm.value.trim() }).then(function () { toast('Nome salvato.'); }).catch(function (e) { toast('Non salvato: ' + e.message, true); }); });
          r.appendChild(nm);
          r.appendChild(el('div', 'cod-num', formatta(v.codice)));
          r.appendChild(el('div', 'm', v.alias_di ? 'Vale lo stesso prodotto del codice ' + v.alias_di : v.nel_catalogo ? 'In uso: ' + (v.prodotto || 'prodotto') : 'Non ancora usato in Movimento'));
          var bt = el('div', 'btns'), et = el('button', 'btn primary', 'Etichetta'), co = el('button', 'btn', 'Collega a un prodotto'), el_ = el('button', 'btn danger', 'Elimina');
          [et, co, el_].forEach(function (b) { b.type = 'button'; bt.appendChild(b); }); r.appendChild(bt);
          var armato = false;   // due tocchi invece di una finestra di conferma (che alcune app non mostrano)
          el_.addEventListener('click', function () {
            if (!armato) { armato = true; el_.textContent = 'Tocca ancora per eliminare'; r.appendChild(el('p', 'm cod-avviso', 'Il codice sparisce dall\'elenco e non verrà mai riusato: le etichette già stampate non varranno più.')); setTimeout(function () { armato = false; el_.textContent = 'Elimina'; var w = r.querySelector('.cod-avviso'); if (w) w.remove(); }, 6000); return; }
            el_.disabled = true; api('POST', 'api/codici/elimina', { codice: v.codice }).then(function () { toast('Codice eliminato.'); carica(); }).catch(function (e) { toast('Non eliminato: ' + e.message, true); el_.disabled = false; armato = false; el_.textContent = 'Elimina'; });
          });
          et.addEventListener('click', function () { window.mostraEtichettaStampante(v.codice, api, toast); });
          var area = el('div', 'cod-coll'); area.hidden = true; r.appendChild(area);
          co.addEventListener('click', function () {
            area.hidden = !area.hidden; if (area.hidden) return; area.textContent = '';
            area.appendChild(el('p', 'm', 'Scrivi il codice a barre del prodotto (già nel tuo catalogo) che questo codice deve rappresentare: scansionandolo si aprirà quel prodotto.'));
            var pr = el('input'); pr.type = 'text'; pr.inputMode = 'numeric'; pr.placeholder = 'Codice del prodotto'; pr.setAttribute('aria-label', 'Codice del prodotto');
            var ok = el('button', 'btn', 'Collega'); ok.type = 'button'; area.appendChild(pr); area.appendChild(ok);
            ok.addEventListener('click', function () {
              var p = /^pers\d{9}$/i.test(pr.value.trim()) ? pr.value.trim().toUpperCase() : pr.value.replace(/\D/g, ''); if (!p) return; ok.disabled = true;
              api('POST', 'api/codici/collega', { codice: v.codice, principale: p }).then(function () { toast('Collegato.'); carica(); }).catch(function (e) { toast('Non collegato: ' + e.message, true); ok.disabled = false; });
            });
          });
          lista.appendChild(r);
        });
      }).catch(function (e) { lista.textContent = 'Non riesco a leggere i codici: ' + e.message; });
    }
    nuovo.addEventListener('click', function () {
      nuovo.disabled = true;
      api('POST', 'api/codici/nuovo', { nome: nome.value.trim() }).then(function (v) { nome.value = ''; toast('Codice creato.'); carica(); window.mostraEtichettaStampante(v.codice, api, toast); })
        .catch(function (e) { toast('Non creato: ' + e.message, true); }).then(function () { nuovo.disabled = false; });
    });
    carica();
  };
})();
