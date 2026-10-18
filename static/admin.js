(function () {
'use strict';
var S = JSON.parse(document.getElementById('schema').textContent);
var CSRF = document.querySelector('meta[name=csrf]').content;
var C = {}, cur = null, dirty = false, opened = new Set();
var $ = function (id) { return document.getElementById(id); };

function el(tag, attrs, kids) {
  var e = document.createElement(tag), k;
  attrs = attrs || {};
  for (k in attrs) {
    var v = attrs[k];
    if (k === 'class') e.className = v;
    else if (k === 'text') e.textContent = v;
    else if (k.slice(0, 2) === 'on') e[k] = v;
    else if (v !== false && v != null) e.setAttribute(k, v === true ? '' : v);
  }
  (kids || []).forEach(function (c) { if (c) e.appendChild(c); });
  return e;
}
function toast(msg, bad) {
  var t = $('toast'); t.textContent = msg; t.className = 'show' + (bad ? ' bad' : '');
  clearTimeout(toast.t); toast.t = setTimeout(function () { t.className = ''; }, 3800);
}
function api(path, opt) {
  opt = opt || {}; opt.credentials = 'same-origin';
  opt.headers = Object.assign({ 'X-CSRF-Token': CSRF }, opt.headers || {});
  return fetch(path, opt).then(function (r) {
    return r.json().catch(function () { return {}; }).then(function (j) {
      if (r.status === 401) { location.href = '/admin/login'; throw new Error(j.error || 'Sesi berakhir'); }
      if (!r.ok) throw new Error(j.error || ('Gagal (' + r.status + ')'));
      return j;
    });
  });
}
function mark() { dirty = true; $('save').classList.add('dirty'); }
function clean() { dirty = false; $('save').classList.remove('dirty'); }

function help(wrap, f) { if (f.help) wrap.appendChild(el('small', { text: f.help })); }
function imageField(f, obj, wrap, lab, id) {
  var prev = el('img', { class: 'prev', alt: '' });
  var inp = el('input', { id: id, type: 'file', accept: 'image/png,image/jpeg,image/webp,image/gif' });
  var clr = el('button', { type: 'button', class: 'btn ghost sm', text: 'Hapus gambar' });
  function show() {
    if (obj[f.k]) { prev.src = obj[f.k]; prev.hidden = false; clr.hidden = false; }
    else { prev.removeAttribute('src'); prev.hidden = true; clr.hidden = true; }
  }
  inp.onchange = function () {
    var file = inp.files[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { toast('Ukuran gambar maksimal 5 MB.', true); inp.value = ''; return; }
    var fd = new FormData(); fd.append('file', file);
    api('/admin/api/upload', { method: 'POST', body: fd }).then(function (j) {
      obj[f.k] = j.url; show(); mark(); toast('Gambar terunggah. Klik Simpan untuk menerapkan.');
    }).catch(function (e) { toast(e.message, true); });
    inp.value = '';
  };
  clr.onclick = function () { obj[f.k] = ''; show(); mark(); };
  show();
  wrap.appendChild(lab); wrap.appendChild(prev);
  wrap.appendChild(el('div', { class: 'row' }, [inp, clr])); help(wrap, f);
  return wrap;
}
function field(f, obj) {
  var id = 'f' + Math.random().toString(36).slice(2), wrap = el('div', { class: 'fld' });
  var lab = el('label', { for: id, text: f.label }), ctl, v = obj[f.k];
  if (f.type === 'image') return imageField(f, obj, wrap, lab, id);
  if (f.type === 'textarea' || f.type === 'lines') {
    ctl = el('textarea', { id: id, rows: f.type === 'lines' ? 5 : 4 });
    ctl.value = f.type === 'lines' ? (v || []).join('\n') : (v || '');
    ctl.oninput = function () { obj[f.k] = f.type === 'lines' ? ctl.value.split('\n') : ctl.value; mark(); };
  } else if (f.type === 'bool') {
    ctl = el('input', { id: id, type: 'checkbox' }); ctl.checked = !!v;
    ctl.onchange = function () { obj[f.k] = ctl.checked; mark(); };
    wrap.className = 'fld chk'; wrap.appendChild(ctl); wrap.appendChild(lab); return wrap;
  } else if (f.type === 'select') {
    ctl = el('select', { id: id });
    f.options.forEach(function (o) { ctl.appendChild(el('option', { value: o[0], text: o[1] })); });
    ctl.value = v; ctl.onchange = function () { obj[f.k] = ctl.value; mark(); };
  } else if (f.type === 'color') {
    ctl = el('input', { id: id, type: 'color' }); ctl.value = v || '#000000';
    ctl.oninput = function () { obj[f.k] = ctl.value; mark(); };
  } else {
    ctl = el('input', { id: id, type: f.type === 'number' ? 'number' : 'text' });
    if (f.type === 'number') { ctl.min = '0'; ctl.step = '1'; }
    ctl.value = v == null ? '' : v;
    ctl.oninput = function () { obj[f.k] = f.type === 'number' ? (ctl.value === '' ? 0 : Number(ctl.value)) : ctl.value; mark(); };
  }
  wrap.appendChild(lab); wrap.appendChild(ctl); help(wrap, f);
  return wrap;
}
function blank(fields) {
  var o = {};
  fields.forEach(function (f) {
    o[f.k] = f.type === 'bool' ? false : f.type === 'lines' ? [] : f.type === 'number' ? 0 :
      f.type === 'select' ? f.options[0][0] : f.type === 'color' ? '#19a1c8' : '';
  });
  return o;
}
function itemEl(sec, data, it, i) {
  var d = el('details', { class: 'item' });
  d.open = opened.has(it);
  d.ontoggle = function () { if (d.open) opened.add(it); else opened.delete(it); };
  d.appendChild(el('summary', { text: (i + 1) + '. ' + (it[sec.title_key] || '(' + sec.item_name + ' baru)') }));
  var body = el('div', { class: 'ibody' });
  sec.item.forEach(function (f) { body.appendChild(field(f, it)); });
  var t = el('div', { class: 'tools' });
  [['Naik', -1], ['Turun', 1]].forEach(function (m) {
    t.appendChild(el('button', { type: 'button', class: 'btn ghost sm', text: m[0], onclick: function () {
      var j = i + m[1];
      if (j < 0 || j >= data.items.length) return;
      data.items.splice(j, 0, data.items.splice(i, 1)[0]); opened.add(it); mark(); render();
    } }));
  });
  t.appendChild(el('button', { type: 'button', class: 'btn ghost sm', text: 'Duplikat', onclick: function () {
    var c = JSON.parse(JSON.stringify(it)); data.items.splice(i + 1, 0, c); opened.add(c); mark(); render();
  } }));
  t.appendChild(el('button', { type: 'button', class: 'btn danger sm', text: 'Hapus', onclick: function () {
    if (confirm('Hapus item ini?')) { data.items.splice(i, 1); opened.delete(it); mark(); render(); }
  } }));
  body.appendChild(t); d.appendChild(body);
  return d;
}
function setHead(title, desc, tools) {
  $('title').textContent = title; $('desc').textContent = desc || '';
  $('save').hidden = !tools; $('reset').hidden = !tools;
}
function render() {
  var sec = S.sections[cur], data = C[cur], p = $('panel');
  p.textContent = ''; setHead(sec.label, sec.desc, true);
  var card = el('div', { class: 'card' });
  (sec.kind === 'object' ? sec.fields : sec.head).forEach(function (f) { card.appendChild(field(f, data)); });
  p.appendChild(card);
  if (sec.kind === 'list') {
    p.appendChild(el('h2', { class: 'h2', text: sec.items_label + ' (' + data.items.length + ')' }));
    var list = el('div', { class: 'items' });
    data.items.forEach(function (it, i) { list.appendChild(itemEl(sec, data, it, i)); });
    p.appendChild(list);
    p.appendChild(el('button', { type: 'button', class: 'btn ghost', text: '+ Tambah ' + sec.item_name, onclick: function () {
      var o = blank(sec.item); data.items.push(o); opened.add(o); mark(); render();
    } }));
  }
  nav();
}
function account() {
  var p = $('panel'); p.textContent = ''; setHead('Akun dan Keamanan', 'Ganti kata sandi admin.', false);
  var cp = el('input', { type: 'password', autocomplete: 'current-password' });
  var np = el('input', { type: 'password', autocomplete: 'new-password' });
  var rp = el('input', { type: 'password', autocomplete: 'new-password' });
  var btn = el('button', { type: 'button', class: 'btn', text: 'Ganti kata sandi', onclick: function () {
    if (np.value !== rp.value) { toast('Konfirmasi kata sandi tidak sama.', true); return; }
    btn.disabled = true;
    api('/admin/api/password', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current: cp.value, 'new': np.value }) })
      .then(function () { cp.value = np.value = rp.value = ''; toast('Kata sandi diganti.'); })
      .catch(function (e) { toast(e.message, true); })
      .then(function () { btn.disabled = false; });
  } });
  function row(t, i) { return el('div', { class: 'fld' }, [el('label', { text: t }), i]); }
  p.appendChild(el('div', { class: 'card' }, [row('Kata sandi saat ini', cp), row('Kata sandi baru (min. 10 karakter)', np), row('Ulangi kata sandi baru', rp), btn]));
  nav();
}
function nav() {
  var n = $('nav'); n.textContent = '';
  S.order.concat(['account']).forEach(function (k) {
    n.appendChild(el('button', { type: 'button', class: k === cur ? 'on' : '', text: k === 'account' ? 'Akun dan Keamanan' : S.sections[k].label,
      onclick: function () { go(k); } }));
  });
}
function go(k) {
  if (dirty && !confirm('Perubahan belum disimpan. Pindah halaman?')) return;
  clean(); cur = k; opened.clear(); document.body.classList.remove('open');
  if (k === 'account') account(); else render();
}
$('save').onclick = function () {
  var b = $('save'); b.disabled = true;
  api('/admin/api/content/' + cur, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(C[cur]) })
    .then(function (j) { C[cur] = j.data; clean(); render(); toast('Tersimpan. Website sudah diperbarui.'); })
    .catch(function (e) { toast(e.message, true); })
    .then(function () { b.disabled = false; });
};
$('reset').onclick = function () {
  if (!confirm('Kembalikan bagian ini ke isi bawaan? Perubahan Anda di bagian ini akan hilang.')) return;
  api('/admin/api/reset/' + cur, { method: 'POST' })
    .then(function (j) { C[cur] = j.data; clean(); render(); toast('Dikembalikan ke isi bawaan.'); })
    .catch(function (e) { toast(e.message, true); });
};
$('menu').onclick = function () { document.body.classList.toggle('open'); };
window.addEventListener('beforeunload', function (e) { if (dirty) { e.preventDefault(); e.returnValue = ''; } });
api('/admin/api/content').then(function (j) { C = j.content; go(S.order[0]); })
  .catch(function (e) { $('title').textContent = 'Gagal memuat'; toast(e.message, true); });
})();
