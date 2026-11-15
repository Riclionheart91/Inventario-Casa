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
  function formatta(c) { return c ? c[0] + ' ' + c.slice(1, 7) + ' ' + c.slice(7) : ''; }

  /* foglio con l'etichetta: anteprima, salva immagine, condividi */
  function foglioEtichetta(codice, titolo, testo, alt, sorgente, stampa) {   // stampa: funzione(bottone) che manda l'etichetta alla X1, oppure null   // sorgente: canvas oppure Blob PNG già pronto
    var old = document.getElementById('etichetta'); if (old) old.remove();
    var ov = el('div'); ov.id = 'etichetta'; ov.setAttribute('role', 'dialog'); ov.setAttribute('aria-modal', 'true');
    var bar = el('div', 'sc-bar'), x = el('button', 'sq', '←'); x.type = 'button'; x.setAttribute('aria-label', 'Chiudi'); bar.appendChild(x); bar.appendChild(el('b', '', titolo));
    var corpo = el('div', 'sc-body etic-corpo'), foot = el('div', 'sc-foot');
    ov.appendChild(bar); ov.appendChild(corpo); ov.appendChild(foot); document.body.appendChild(ov);
    var img = el('img', 'etic-img'); img.alt = alt;
    corpo.appendChild(img); corpo.appendChild(el('p', 'm', testo));
    var nomeFile = 'etichetta-' + codice + '.png', blob = null;
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
    api('GET', 'api/etichetta/' + encodeURIComponent(barcode)).then(function (r) {
      var bin = atob(r.png), a = new Uint8Array(bin.length), i; for (i = 0; i < bin.length; i++) a[i] = bin.charCodeAt(i);
      var blob = new Blob([a], { type: 'image/png' });
      var stampa = !r.stampante ? null : function (b) {
        b.disabled = true; var t0 = b.textContent; b.textContent = 'Stampo…';
        api('POST', 'api/stampa/' + encodeURIComponent(barcode)).then(function () { toast('Etichetta inviata alla stampante.'); })
          .catch(function (e) { toast('Non stampata: ' + e.message, true); })
          .then(function () { b.disabled = false; b.textContent = t0; });
      };
      foglioEtichetta(r.barcode, 'Etichetta per la stampante', 'Per il rotolo da 12 × 40 mm (203 DPI). Il QR contiene il codice ' + r.barcode + ': l\'app lo legge con la fotocamera.' + (r.stampante ? ' «Stampa con la X1» la manda alla stampante collegata a Home Assistant (accesa e vicina al Raspberry).' : ' Salvala in Foto e importala in XeasyLabel, oppure collega la stampante nelle opzioni dell\'add-on.'), 'Etichetta di ' + (r.nome || r.barcode), blob, stampa);
    }).catch(function (e) { toast('Etichetta non creata: ' + e.message, true); });
  };

  /* schermata «I miei codici» nelle Impostazioni */
  window.IMP_EXTRA = window.IMP_EXTRA || {};
  window.IMP_EXTRA.cod = function (det, ctx) {
    var api = ctx.api, toast = ctx.toast;
    var c = el('div', 'card'); c.appendChild(el('p', 'm', 'Codici tuoi per prodotti senza codice a barre (fatti in casa, sfusi, freschi). Iniziano per 2999, non possono coincidere con quelli dei prodotti comprati e non si ripetono mai, nemmeno se togli il prodotto.'));
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
              var p = pr.value.replace(/\D/g, ''); if (!p) return; ok.disabled = true;
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
