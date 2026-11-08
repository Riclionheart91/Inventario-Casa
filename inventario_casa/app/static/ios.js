/* Comportamenti da app iPhone: vibrazione aptica, titolo grande, transizioni tra schede, indice A-Z, fogli che salgono dal basso.
   Tutto qui e facoltativo: se qualcosa non e supportato l'app funziona come prima. */
(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var RIDOTTO = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- vibrazione aptica ----------
     Android: navigator.vibrate. iPhone: Safari non ha vibrate; da iOS 17.4 un interruttore nativo (<input switch>) toccato da un gesto dell'utente
     fa il «tic» del sistema. Non e documentato ufficialmente: se non funziona sul tuo iPhone, non succede niente. */
  var hapOn = true; try { hapOn = localStorage.getItem('hap') !== '0'; } catch (e) { /* ok */ }
  var sw = null, ultimo = 0;
  function creaSwitch() {
    if (sw) return sw;
    var l = document.createElement('label'); l.setAttribute('aria-hidden', 'true');
    l.style.cssText = 'position:fixed;left:-200px;top:-200px;width:1px;height:1px;opacity:0;pointer-events:none';
    var i = document.createElement('input'); i.type = 'checkbox'; i.setAttribute('switch', ''); i.tabIndex = -1; l.appendChild(i);
    document.body.appendChild(l); sw = l; return l;
  }
  function haptic(tipo) {
    if (!hapOn) return;
    var t = Date.now(); if (t - ultimo < 35) return; ultimo = t;
    try {
      if (navigator.vibrate) { navigator.vibrate(tipo === 'errore' ? [18, 40, 18] : tipo === 'ok' ? 14 : 8); return; }
      creaSwitch().click();
      if (tipo === 'errore') setTimeout(function () { try { sw.click(); } catch (e) { /* ok */ } }, 90);
    } catch (e) { /* niente vibrazione */ }
  }
  window.haptic = haptic;
  window.hapticAttivo = function (v) { if (v !== undefined) { hapOn = !!v; try { localStorage.setItem('hap', v ? '1' : '0'); } catch (e) { /* ok */ } } return hapOn; };

  /* ---------- titolo grande ---------- */
  var main = document.querySelector('main'), top = document.querySelector('.top');
  var lt = $('ltitle'), ls = $('lsub');
  function copiaTitolo() { if (lt) lt.textContent = ($('title') || {}).textContent || ''; if (ls) ls.textContent = ($('sub') || {}).textContent || ''; }
  if (lt && $('title')) {
    copiaTitolo();
    new MutationObserver(copiaTitolo).observe($('title'), { childList: true, characterData: true, subtree: true });
    if ($('sub')) new MutationObserver(copiaTitolo).observe($('sub'), { childList: true, characterData: true, subtree: true });
  }
  function barraSotto() { if (top && main) top.classList.toggle('sotto', main.scrollTop > (lt ? lt.offsetHeight + 4 : 40)); }
  if (main) main.addEventListener('scroll', barraSotto, { passive: true });

  /* ---------- transizioni tra schede (verso la scheda successiva = entra da destra) ---------- */
  function ordine() { return Array.prototype.map.call(document.querySelectorAll('#nav button'), function (b) { return b.dataset.tab; }); }
  function viewVisibile() { var v = document.querySelector('.view:not([hidden])'); return v ? v.id.replace(/^v-/, '') : ''; }
  var prec = viewVisibile();
  function cambioScheda(nuova) {
    if (!nuova || nuova === prec) return;
    var o = ordine(), dir = o.indexOf(nuova) >= o.indexOf(prec) ? 1 : -1; prec = nuova;
    haptic('tic');
    var v = $('v-' + nuova);
    if (v && v.animate && !RIDOTTO) v.animate([{ transform: 'translate3d(' + (dir * 36) + 'px,0,0)', opacity: 0 }, { transform: 'translate3d(0,0,0)', opacity: 1 }], { duration: 300, easing: 'cubic-bezier(.2,.8,.2,1)' });
    if (main) main.scrollTop = 0;
    barraSotto(); aggiornaIndice();
  }
  /* un'unica sorveglianza sugli attributi: scheda visibile, riga trascinata fino alla soglia, toast */
  if (main) new MutationObserver(function (recs) {
    for (var i = 0; i < recs.length; i++) {
      var r = recs[i], t = r.target;
      if (r.attributeName === 'hidden' && t.classList && t.classList.contains('view') && !t.hidden) cambioScheda(t.id.replace(/^v-/, ''));
      else if (r.attributeName === 'class' && t.classList && t.classList.contains('sw') && t.classList.contains('pronto') && (r.oldValue || '').indexOf('pronto') < 0) haptic('tic');
    }
  }).observe(main, { subtree: true, attributes: true, attributeFilter: ['hidden', 'class'], attributeOldValue: true });
  if ($('toast')) new MutationObserver(function () { var t = $('toast'); if (t.classList.contains('on')) haptic(t.classList.contains('err') ? 'errore' : 'ok'); }).observe($('toast'), { attributes: true, attributeFilter: ['class'] });
  document.addEventListener('click', function (e) { if (e.isTrusted && e.target.closest && e.target.closest('.seg button, .chip, .offname')) haptic('tic'); }, true);
  document.addEventListener('change', function (e) { if (e.isTrusted && e.target && e.target.type === 'checkbox') haptic('tic'); }, true);

  /* ---------- fogli che salgono dal basso ---------- */
  function sale(nodo) { if (nodo && nodo.animate && !RIDOTTO) nodo.animate([{ transform: 'translate3d(0,100%,0)' }, { transform: 'translate3d(0,0,0)' }], { duration: 340, easing: 'cubic-bezier(.2,.8,.2,1)' }); haptic('tic'); }
  if ($('scheda')) new MutationObserver(function () { if (!$('scheda').hidden) sale($('scheda')); }).observe($('scheda'), { attributes: true, attributeFilter: ['hidden'] });
  new MutationObserver(function (recs) { recs.forEach(function (r) { Array.prototype.forEach.call(r.addedNodes, function (n) { if (n.id === 'offscheda') sale(n); }); }); }).observe(document.body, { childList: true });

  /* ---------- indice A-Z ---------- */
  var LETTERE = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ#'.split('');
  var app = $('app'), az = document.createElement('div'), bolla = document.createElement('div'), voci = {}, attiva = '';
  az.id = 'az'; az.setAttribute('aria-hidden', 'true'); bolla.id = 'az-bolla'; bolla.setAttribute('aria-hidden', 'true');
  if (app) { app.appendChild(az); app.appendChild(bolla); }
  LETTERE.forEach(function (l) { var s = document.createElement('span'); s.textContent = l; s.dataset.l = l; az.appendChild(s); });
  function lettera(t) {
    var c = String(t || '').trim().normalize ? String(t || '').trim().normalize('NFD').replace(/[̀-ͯ]/g, '').charAt(0).toUpperCase() : '';
    return /[A-Z]/.test(c) ? c : '#';
  }
  function fonti() {   // elementi da raggiungere con l'indice, nella scheda visibile
    var t = viewVisibile(), out = [];
    if (t === 'prod') Array.prototype.forEach.call(document.querySelectorAll('#prodlist > details.g > summary'), function (s) { var n = s.querySelector('.gn'); if (n) out.push([lettera(n.textContent), s]); });
    else if (t === 'off') Array.prototype.forEach.call(document.querySelectorAll('#off .offcard:not([hidden]) .offname'), function (n) { out.push([lettera(n.textContent), n.closest('.offcard')]); });
    return out;
  }
  var tAgg = 0;
  function aggiornaIndice() { clearTimeout(tAgg); tAgg = setTimeout(disegna, 60); }
  function disegna() {
    voci = {}; var f = fonti();
    f.forEach(function (x) { if (!voci[x[0]]) voci[x[0]] = x[1]; });
    var n = Object.keys(voci).length, mostra = n >= 3 && f.length >= 8 && !!main;
    az.classList.toggle('on', mostra); if (app) app.classList.toggle('conaz', mostra);
    if (!mostra) return;
    var a = app.getBoundingClientRect(), m = main.getBoundingClientRect();
    az.style.top = (m.top - a.top + 6) + 'px'; az.style.height = Math.max(120, m.height - 12) + 'px';
    Array.prototype.forEach.call(az.children, function (s) { s.classList.toggle('vuota', !voci[s.dataset.l]); s.classList.remove('att'); }); attiva = '';
  }
  function vaiA(l) {
    var succ = LETTERE.indexOf(l), el = null;
    for (var i = succ; i < LETTERE.length && !el; i++) { if (voci[LETTERE[i]]) { el = voci[LETTERE[i]]; l = LETTERE[i]; } }
    for (var j = succ - 1; j >= 0 && !el; j--) { if (voci[LETTERE[j]]) { el = voci[LETTERE[j]]; l = LETTERE[j]; } }
    if (!el) return;
    if (l !== attiva) {
      attiva = l; haptic('tic');
      Array.prototype.forEach.call(az.children, function (s) { s.classList.toggle('att', s.dataset.l === l); });
      bolla.textContent = l;
    }
    var stk = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--stk'), 10) || 0;
    main.scrollTop += el.getBoundingClientRect().top - (main.getBoundingClientRect().top + stk - 8);
  }
  function daY(y) { var r = az.getBoundingClientRect(), i = Math.max(0, Math.min(LETTERE.length - 1, Math.floor((y - r.top) / r.height * LETTERE.length))); return LETTERE[i]; }
  function muoviBolla(y) { var a = app.getBoundingClientRect(); bolla.style.top = Math.max(0, y - a.top - 29) + 'px'; }
  function giu(e) { e.preventDefault(); var p = e.touches ? e.touches[0] : e; bolla.classList.add('on'); muoviBolla(p.clientY); vaiA(daY(p.clientY)); }
  function su() { bolla.classList.remove('on'); setTimeout(function () { Array.prototype.forEach.call(az.children, function (s) { s.classList.remove('att'); }); attiva = ''; }, 500); }
  az.addEventListener('touchstart', giu, { passive: false });
  az.addEventListener('touchmove', giu, { passive: false });
  az.addEventListener('touchend', su); az.addEventListener('touchcancel', su);
  az.addEventListener('mousedown', function (e) {
    giu(e);
    var mm = function (ev) { giu(ev); }, mu = function () { document.removeEventListener('mousemove', mm); document.removeEventListener('mouseup', mu); su(); };
    document.addEventListener('mousemove', mm); document.addEventListener('mouseup', mu);
  });
  ['prodlist', 'off'].forEach(function (id) { if ($(id)) new MutationObserver(aggiornaIndice).observe($(id), { childList: true, subtree: false }); });
  window.addEventListener('resize', aggiornaIndice);
  if ($('off')) new MutationObserver(aggiornaIndice).observe($('off'), { subtree: true, attributes: true, attributeFilter: ['hidden'] });
  aggiornaIndice(); barraSotto();

  /* ---------- «Aspetto» in Impostazioni ---------- */
  function cardAspetto() {
    var imp = $('imp'); if (!imp || imp.querySelector('.aspetto')) return;
    var c = document.createElement('div'); c.className = 'card aspetto';
    var h = document.createElement('h2'); h.textContent = 'Aspetto e vibrazione'; c.appendChild(h);
    var p = document.createElement('p'); p.className = 'm'; p.textContent = 'La vibrazione leggera accompagna i cambi di scheda, l\'indice A-Z e i gesti. Su iPhone funziona da iOS 17.4; se non la senti, il tuo sistema non la permette.'; c.appendChild(p);
    var b = document.createElement('button'); b.type = 'button'; b.className = 'btn';
    function testo() { b.textContent = 'Vibrazione: ' + (hapOn ? 'attiva' : 'spenta'); }
    b.addEventListener('click', function () { window.hapticAttivo(!hapOn); testo(); haptic('ok'); }); testo();
    c.appendChild(b); imp.insertBefore(c, imp.firstChild);
  }
  if ($('imp')) new MutationObserver(cardAspetto).observe($('imp'), { childList: true });
})();
