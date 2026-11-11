/* Accessi recenti: contenuto della schermata «Accessi e sicurezza». Solo textContent per tutto ciò che arriva dal server. */
(function () {
  'use strict';
  window.IMP_EXTRA = window.IMP_EXTRA || {};
  function relativo(t, adesso) {
    var s = Math.max(0, Math.round((adesso - t))), m = Math.round(s / 60), h = Math.round(s / 3600), g = Math.round(s / 86400);
    if (s < 90) return 'adesso'; if (m < 60) return m + ' min fa'; if (h < 24) return h + (h === 1 ? ' ora fa' : ' ore fa');
    return g + (g === 1 ? ' giorno fa' : ' giorni fa');
  }
  function quando(t) { var d = new Date(t * 1000); return ('0' + d.getDate()).slice(-2) + '/' + ('0' + (d.getMonth() + 1)).slice(-2) + ' ' + ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2); }
  var ICO = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/></svg>';
  window.IMP_EXTRA.sic = function (det, ctx) {
    var el = ctx.el, api = ctx.api, box = el('div', 'acc-box'); det.appendChild(box);
    function disegna(r) {
      box.textContent = '';
      box.appendChild(el('div', 'imp-gt', 'Accessi recenti'));
      var g = el('div', 'imp-grp');
      if (!r.dispositivi.length) g.appendChild(el('div', 'acc-vuoto m', 'Nessun accesso registrato ancora.'));
      r.dispositivi.forEach(function (d) {
        var riga = el('div', 'imp-row acc-riga'), ic = el('span', 'imp-ico'); ic.style.background = d.via === 'ingress' ? '#0a84ff' : '#ff9f0a'; ic.innerHTML = ICO;
        var t = el('span', 'imp-t'), n = el('div', 'acc-nome', d.nome || 'Dispositivo');
        if (r.adesso - d.primo < 86400) n.appendChild(el('span', 'acc-nuovo', 'nuovo'));
        t.appendChild(n);
        t.appendChild(el('div', 'm', [d.utente, d.via === 'ingress' ? 'da Home Assistant' : 'accesso diretto', d.ip, d.n + (d.n === 1 ? ' accesso' : ' accessi')].filter(Boolean).join(' · ')));
        riga.appendChild(ic); riga.appendChild(t); riga.appendChild(el('span', 'imp-s', relativo(d.ultimo, r.adesso))); g.appendChild(riga);
      });
      box.appendChild(g);
      box.appendChild(el('p', 'm acc-nota', r.da ? 'Registro attivo dal ' + quando(r.da) + '. Una voce per dispositivo e per ora; nessun codice né cookie vengono salvati.' : 'Il registro parte dal prossimo accesso.'));
      if (r.errori.length) {
        box.appendChild(el('div', 'imp-gt', 'Codici errati e blocchi'));
        var ge = el('div', 'imp-grp');
        r.errori.forEach(function (e) {
          var riga = el('div', 'imp-row acc-riga'), t = el('span', 'imp-t', e.tipo === 'blocco' ? 'Bloccato per troppi tentativi' : 'Codice errato');
          t.appendChild(el('div', 'm', e.ip || ''));
          riga.appendChild(t); riga.appendChild(el('span', 'imp-s', quando(e.t))); ge.appendChild(riga);
        });
        box.appendChild(ge);
      }
      var b = el('button', 'btn bad', 'Svuota il registro'); b.type = 'button'; b.disabled = !r.dispositivi.length && !r.errori.length; var pronto = 0;
      b.addEventListener('click', function () {   // due tocchi per confermare
        if (!pronto) { pronto = setTimeout(function () { pronto = 0; b.textContent = 'Svuota il registro'; }, 5000); b.textContent = 'Tocca ancora per svuotare'; return; }
        clearTimeout(pronto); pronto = 0; b.disabled = true;
        api('POST', 'api/accessi/svuota').then(function () { ctx.toast('Registro svuotato.'); carica(); }).catch(function (e) { ctx.toast('Non riuscito: ' + e.message, true); b.disabled = false; });
      });
      box.appendChild(b);
    }
    function carica() { api('GET', 'api/accessi').then(disegna).catch(function (e) { box.textContent = 'Non riesco a leggere gli accessi: ' + e.message; }); }
    carica();
  };
})();
