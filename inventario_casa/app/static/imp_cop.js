/* Copia ed esporta: contenuto della schermata «Copia ed esporta» (Impostazioni). */
(function () {
  'use strict';
  window.IMP_EXTRA = window.IMP_EXTRA || {};
  function quando(iso) {
    if (!iso) return 'mai';
    var d = new Date(iso); if (isNaN(d.getTime())) return String(iso);
    try { return d.toLocaleString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }); } catch (e) { return String(iso); }
  }
  window.IMP_EXTRA.cop = function (det, ctx) {
    var el = ctx.el, api = ctx.api, toast = ctx.toast;
    var c = el('div', 'card'); c.appendChild(el('h2', '', 'Copia di sicurezza'));
    c.appendChild(el('p', 'm', 'Una copia del foglio Google nella cartella Drive dell\'app. Si tengono le ultime 5 copie, le più vecchie vanno nel cestino. La copia non modifica il foglio, quindi si può fare anche in sola lettura.'));
    var corpo = el('div', ''); c.appendChild(corpo);
    var esito = el('p', 'note', ''); var bt = el('button', 'btn primary', 'Salva una copia ora'); bt.type = 'button';
    var riga = function (k, v) { var p = el('p', 'm'); p.appendChild(el('b', '', k + ': ')); p.appendChild(document.createTextNode(v)); corpo.appendChild(p); };
    function carica() {
      api('GET', 'api/copia').then(function (s) {
        corpo.textContent = '';
        riga('Ultima copia', quando(s.ultima));
        riga('Copia automatica', s.auto ? 'ogni ' + s.giorni + (s.giorni === 1 ? ' giorno' : ' giorni') + (s.prossima ? ' · prossima dopo il ' + quando(s.prossima) : '') : 'spenta (si attiva qui sotto)');
        if (s.errore) { var e = el('p', 'note warn', 'Ultimo tentativo non riuscito: ' + s.errore); corpo.appendChild(e); }
        if (!s.possibile) corpo.appendChild(el('p', 'note warn', s.motivo || 'La copia su Drive non è disponibile.'));
        (s.copie || []).forEach(function (x) {
          var p = el('p', 'm'); var a = el('a', '', x.nome); a.href = x.link; a.target = '_blank'; a.rel = 'noopener'; p.appendChild(a); p.appendChild(document.createTextNode(' · ' + quando(x.quando))); corpo.appendChild(p);
        });
        bt.disabled = !s.possibile || !!s.in_corso || !!window.__copiaInCorso;
      }).catch(function (e) { corpo.textContent = 'Non riesco a leggere lo stato: ' + e.message; });
    }
    bt.addEventListener('click', function () {
      bt.disabled = true; window.__copiaInCorso = true; ctx.note(esito, 'Sto copiando il foglio… può richiedere qualche secondo.');
      api('POST', 'api/copia/ora').then(function (r) {
        ctx.note(esito, 'Copia salvata: ' + r.nome + (r.tolte ? ' · ' + r.tolte + ' vecchie nel cestino' : ''), 'ok'); toast('Copia salvata.');
      }).catch(function (e) { ctx.note(esito, 'Non riuscita: ' + e.message, 'warn'); toast('Copia non riuscita.', true); })
        .then(function () { window.__copiaInCorso = false; carica(); });
    });
    c.appendChild(bt); c.appendChild(esito); det.appendChild(c); carica();

    var x = el('div', 'card'); x.appendChild(el('h2', '', 'Esporta'));
    x.appendChild(el('p', 'm', 'Scarica l\'inventario in un file CSV (si apre con Excel, Numbers o Fogli): prodotti, giacenze per posizione, scorta minima, prossima scadenza e ultimo carico.'));
    var nx = el('p', 'note', ''), be = el('button', 'btn', 'Esporta in CSV'); be.type = 'button';
    be.addEventListener('click', function () {
      be.disabled = true; ctx.note(nx, 'Preparo il file…');
      fetch('./api/esporta.csv').then(function (r) {
        if (!r.ok) throw new Error('errore ' + r.status);
        var nome = 'inventario.csv', cd = r.headers.get('Content-Disposition') || '', m = /filename="([^"]+)"/.exec(cd); if (m) nome = m[1];
        return r.blob().then(function (b) { return [b, nome]; });
      }).then(function (r) {
        var u = URL.createObjectURL(r[0]), a = document.createElement('a'); a.href = u; a.download = r[1]; document.body.appendChild(a); a.click(); a.remove();
        setTimeout(function () { URL.revokeObjectURL(u); }, 4000); ctx.note(nx, 'File pronto: ' + r[1], 'ok');
      }).catch(function (e) { ctx.note(nx, 'Non riuscito: ' + e.message, 'warn'); }).then(function () { be.disabled = false; });
    });
    x.appendChild(be); x.appendChild(nx); det.appendChild(x);
  };
})();
