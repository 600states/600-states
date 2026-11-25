/* Faltet och lasrutan. EN DEFINITION, ETT STALLE.
 *
 * Koden lag inne i index.html. Nar en andra sida skulle visa ett falt med
 * samma lasruta fanns tva vagar: kopiera tvahundra rader, eller lyfta ut dem.
 * En kopia ar tva definitioner av samma sak som glider isar - FYND 004:s form,
 * den har gangen i den publika vyn - sa den ligger har och lases av bada.
 *
 * Sidan ger datan, filen ritar den:
 *
 *     <script src="data.js"></script>          window.STATE001
 *     <script src="field.js"></script>
 *     initField(window.STATE001);
 *
 * Sidan maste bara innehalla #grid, #fieldcv och #readout med lasrutans
 * element i samma form som index.html. Tre av dem star UTANFOR lasrutan,
 * under verket: .txt, .note och .lock - se kommentaren vid uppslagningen.
 * Saknas nagot av dem ritas inget falt och sidan star kvar som den ar -
 * en sida utan skript visar sin noscript-bild.
 */
(function(){
  "use strict";

  var EVIDENCE = {P: 'Publisher headline', S: 'URL text', U: 'Page title, unverified'};

  window.initField = function(data){
  var keys = document.getElementById('grid');
  var cv   = document.getElementById('fieldcv');
  var ro   = document.getElementById('readout');
  if(!(data && keys && cv && ro && cv.getContext)) return;
    var cur = -1, tilePx = 1, gapPx = 1, dpr = 1, mq = null, pending = false, locked = false;
    var box = cv.parentElement;
    var ctx = cv.getContext('2d');

    // the keyboard and screen-reader layer: 600 real buttons, visually hidden, driving the same show()
    var frag = document.createDocumentFragment();
    for(var i = 0; i < data.tiles.length; i++){
      var t0 = data.tiles[i];
      var b = document.createElement('button');
      b.type = 'button';
      b.setAttribute('tabindex', '-1');
      b.setAttribute('aria-pressed', 'false');
      b.setAttribute('aria-label', 'Tile ' + (i + 1) + ': ' + t0[2] + '. ' + t0[1]);
      frag.appendChild(b);
    }
    keys.appendChild(frag);
    var btns = keys.children;

    var idx  = ro.querySelector('.idx'),
        sw   = ro.querySelector('.swatch'),
        // TRE element ligger UTANFOR lasrutan, under verket. Pastaendet och
        // anteckningen ar de enda vars hojd beror pa observationen, hallnoten
        // ar inte rutans data alls. Lasrutan far aldrig vara hogre an canvasen,
        // sa det som vaxer med dygnet far inte sta i den.
        tx   = document.querySelector('.txt'),
        note = document.querySelector('.note'),
        lockNote = document.querySelector('.lock'),
        dds  = ro.querySelectorAll('dd');

    function onDpr(){ paint(0); }
    function watchDpr(d){
      // the query carries the ratio it was built with, so it is rebuilt whenever the ratio moves
      if(mq && mq.removeEventListener) mq.removeEventListener('change', onDpr);
      mq = matchMedia('(resolution: ' + d + 'dppx)');
      if(mq.addEventListener) mq.addEventListener('change', onDpr);
    }

    // No arrangement of CSS pixels holds whole device pixels across 30 columns: Chromium stores
    // layout in 1/64 px and the error accumulates until gridlines fall either side of a device
    // pixel. The canvas is sized and painted in device pixels, so every coordinate here is an integer.
    function paint(availPx){
      pending = false;
      dpr = window.devicePixelRatio || 1;
      var avail = (availPx > 0) ? availPx : Math.floor(box.clientWidth * dpr);
      if(avail <= 0) return;
      gapPx = Math.max(1, Math.round(dpr));
      tilePx = Math.floor((avail - 29 * gapPx) / 30);
      if(tilePx < 1) tilePx = 1;
      var wPx = 30 * tilePx + 29 * gapPx, hPx = 20 * tilePx + 19 * gapPx;
      cv.width = wPx;
      cv.height = hPx;
      cv.style.width = (wPx / dpr) + 'px';
      cv.style.height = (hPx / dpr) + 'px';
      ctx.fillStyle = '#0B0E12';
      ctx.fillRect(0, 0, wPx, hPx);
      var step = tilePx + gapPx;
      for(var j = 0; j < 600; j++){
        ctx.fillStyle = data.tiles[j][0];
        ctx.fillRect((j % 30) * step, ((j / 30) | 0) * step, tilePx, tilePx);
      }
      if(cur >= 0) mark(cur);
      watchDpr(dpr);
    }

    var GLOSS = {'3/3': ' read the same way every time',
                 '2/3': ' two of three agreed',
                 '1/3': ' the three passes never agreed'};

    // the marker is a band in the separator colour OUTSIDE the tile, so the observation's own colour is never covered
    function mark(i){
      var step = tilePx + gapPx, x = (i % 30) * step, y = ((i / 30) | 0) * step, t = gapPx * (locked ? 4 : 2);
      ctx.fillStyle = '#0B0E12';
      ctx.fillRect(x - t, y - t, tilePx + 2 * t, t);
      ctx.fillRect(x - t, y + tilePx, tilePx + 2 * t, t);
      ctx.fillRect(x - t, y, t, tilePx);
      ctx.fillRect(x + tilePx, y, t, tilePx);
    }

    function show(i){
      if(i < 0 || i >= data.tiles.length || i === cur) return;
      if(cur >= 0) btns[cur].setAttribute('aria-pressed', 'false');
      cur = i;
      btns[i].setAttribute('aria-pressed', 'true');
      paint();
      var t = data.tiles[i];
      idx.textContent = 'Tile ' + (i + 1) + ' of 600 \u00b7 ' + t[0];
      sw.style.background = t[0];
      tx.textContent = t[1];
      dds[0].textContent = t[2];
      dds[1].textContent = t[3];
      dds[2].textContent = t[5].toFixed(2);
      dds[3].textContent = t[6].toFixed(2);
      // Glossen star pa faltets varde, inte pa "allt annat an 3/3": fyra rutor
      // ar 1/3, tre pass och tre olika svar, och det ar inte en bedomningsfraga.
      // Ett nytt varde arver da ingen gloss i stallet for fel gloss.
      dds[4].textContent = t[4] + (GLOSS[t[4]] || '');
      // the link is built through the DOM and the scheme is checked: the href is data, not markup
      dds[5].textContent = '';
      if(/^https?:\/\//i.test(t[8])){
        var a = document.createElement('a');
        a.href = t[8];
        a.target = '_blank';
        a.rel = 'noopener';
        a.textContent = t[9];
        dds[5].appendChild(a);
      } else {
        dds[5].textContent = t[9];
      }
      dds[6].textContent = t[10] + ' UTC';
      dds[7].textContent = EVIDENCE[t[11]] || t[11];
      dds[8].textContent = t[12];
      note.textContent = t[7];
    }

    function hit(e){
      var step = tilePx + gapPx;
      var x = Math.floor(e.offsetX * dpr), y = Math.floor(e.offsetY * dpr);
      var c = Math.floor(x / step), r = Math.floor(y / step);
      if(c < 0 || c > 29 || r < 0 || r > 19) return -1;
      if(x - c * step >= tilePx || y - r * step >= tilePx) return -1;   // the point is on a separator
      return c + r * 30;
    }
    function hold(on){
      locked = on;
      lockNote.hidden = !on;
      cv.style.cursor = on ? 'default' : 'pointer';
      paint();
    }
    cv.addEventListener('mousemove', function(e){
      if(locked) return;
      var i = hit(e);
      if(i >= 0) show(i);
    });
    cv.addEventListener('click', function(e){
      var i = hit(e);
      if(i < 0) return;
      if(locked && i === cur){ hold(false); return; }
      show(i);
      hold(true);
    });
    addEventListener('keydown', function(e){ if(e.key === 'Escape' && locked) hold(false); });

    keys.addEventListener('focus', function(){ if(cur < 0) show(0); });
    keys.addEventListener('keydown', function(e){
      var step = {ArrowRight: 1, ArrowLeft: -1, ArrowDown: 30, ArrowUp: -30}[e.key];
      if(step === undefined) return;
      e.preventDefault();
      show(Math.min(599, Math.max(0, (cur < 0 ? 0 : cur) + step)));
      if(!locked) hold(true);
    });

    paint();
    var queue = function(){ if(!pending){ pending = true; requestAnimationFrame(function(){ paint(); }); } };
    if(window.ResizeObserver){
      // device-pixel-content-box also reports a devicePixelRatio change that leaves the CSS size alone:
      // a stale canvas at a new ratio puts every gridline on a fractional pixel
      var ro2 = new ResizeObserver(function(entries){
        var e0 = entries[0], dp = e0 && e0.devicePixelContentBoxSize && e0.devicePixelContentBoxSize[0];
        paint(dp ? dp.inlineSize : 0);
      });
      try { ro2.observe(box, {box: 'device-pixel-content-box'}); }
      catch(err){ ro2.observe(box); }
    }
    addEventListener('resize', queue);
  };
})();
