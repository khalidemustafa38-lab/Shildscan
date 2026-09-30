/* ============================================
   Pages Loader — يُحدّث محتوى الصفحة من الخادم
   ============================================ */
(function(){
'use strict';

var PAGE_MAP = {
  '/': 'index',
  '/index.html': 'index',
  '/features.html': 'features',
  '/faq.html': 'faq',
  '/contact.html': 'contact',
  '/privacy.html': 'privacy',
};

async function loadPagesContent(){
  var path = location.pathname;
  if(path.endsWith('/')) path = '/';
  var page = PAGE_MAP[path];
  if(!page) return;

  try{
    var r = await fetch('/api/pages');
    if(!r.ok) return;
    var data = await r.json();
    var pageData = data[page] || {};
    applyContent(page, pageData);
    applyFooter(data.footer || {});
    applyBrand(data.brand || {});
  }catch(e){ /* silent */ }
}

function applyContent(page, pageData){
  // ============ Hero ============
  if(pageData.hero){
    setText('.hero .pill', pageData.hero.pill);
    setText('.page-hero .pill', pageData.hero.pill);
    setText('.page-hero h1', pageData.hero.title);
    setText('.page-hero p', pageData.hero.desc);
    if(pageData.hero.title1 && pageData.hero.title2){
      var h1 = document.querySelector('.hero h1');
      if(h1){
        h1.innerHTML = esc(pageData.hero.title1) + '<br>' + esc(pageData.hero.title2);
      }
    }
    setText('.hero p', pageData.hero.desc);
  }

  // ============ Scanner ============
  if(pageData.scanner){
    var tabs = document.querySelectorAll('.tab');
    if(tabs[0] && pageData.scanner.tabUrl) tabs[0].textContent = pageData.scanner.tabUrl.value || pageData.scanner.tabUrl;
    if(tabs[1] && pageData.scanner.tabFile) tabs[1].textContent = pageData.scanner.tabFile.value || pageData.scanner.tabFile;
    if(tabs[2] && pageData.scanner.tabEmail) tabs[2].textContent = pageData.scanner.tabEmail.value || pageData.scanner.tabEmail;

    var urlInp = document.getElementById('urlInput');
    if(urlInp && pageData.scanner.urlPlaceholder) urlInp.placeholder = getVal(pageData.scanner.urlPlaceholder);

    var btns = document.querySelectorAll('.btn-scan');
    if(btns[0] && pageData.scanner.btnUrl) btns[0].textContent = getVal(pageData.scanner.btnUrl);
    if(btns[1] && pageData.scanner.btnFile) btns[1].textContent = getVal(pageData.scanner.btnFile);
    if(btns[2] && pageData.scanner.btnEmail) btns[2].textContent = getVal(pageData.scanner.btnEmail);

    var dh = document.querySelector('.dropzone h3');
    if(dh && pageData.scanner.dropText) dh.textContent = getVal(pageData.scanner.dropText);

    var dl = document.querySelector('.dropzone p');
    if(dl && pageData.scanner.dropLimit) dl.textContent = getVal(pageData.scanner.dropLimit);

    var eb = document.getElementById('emailBody');
    if(eb && pageData.scanner.emailPlaceholder) eb.placeholder = getVal(pageData.scanner.emailPlaceholder);
  }

  // ============ Quick Cards ============
  if(pageData.quick){
    var qhead = document.querySelector('.quick-cards .head');
    if(qhead){
      var qp = qhead.querySelector('.pill'), qt = qhead.querySelector('h2');
      if(qp && pageData.quick.pill) qp.textContent = getVal(pageData.quick.pill);
      if(qt && pageData.quick.title) qt.textContent = getVal(pageData.quick.title);
    }
    var cards = document.querySelectorAll('.quick-card');
    var keys = [['q1Title','q1Desc'],['q2Title','q2Desc'],['q3Title','q3Desc'],['q4Title','q4Desc']];
    cards.forEach(function(card, i){
      if(!keys[i]) return;
      var h = card.querySelector('h3'), p = card.querySelector('p');
      if(h && pageData.quick[keys[i][0]]) h.textContent = getVal(pageData.quick[keys[i][0]]);
      if(p && pageData.quick[keys[i][1]]) p.textContent = getVal(pageData.quick[keys[i][1]]);
    });
  }

  // ============ CTA ============
  if(pageData.cta){
    setText('.cta h2', pageData.cta.title);
    setText('.cta p', pageData.cta.desc);
    setText('.cta .btn-cta', pageData.cta.btn);
  }

  // ============ Features ============
  if(page === 'features'){
    for(var i = 1; i <= 9; i++){
      var f = pageData['f'+i];
      if(!f) continue;
      var cards = document.querySelectorAll('#view-features .f-card, .features .f-card');
      var card = cards[i-1];
      if(!card) continue;
      var icon = card.querySelector('.fi'), title = card.querySelector('h3'), desc = card.querySelector('p');
      if(icon && f.icon) icon.textContent = getVal(f.icon);
      if(title && f.title) title.textContent = getVal(f.title);
      if(desc && f.desc) desc.textContent = getVal(f.desc);
    }
  }

  // ============ FAQ ============
  if(page === 'faq'){
    var faqItems = document.querySelectorAll('.faq-item');
    for(var i = 1; i <= 6; i++){
      var q = pageData['q'+i];
      if(!q) continue;
      var item = faqItems[i-1];
      if(!item) continue;
      var qEl = item.querySelector('.faq-q span'), aEl = item.querySelector('.faq-a p');
      if(qEl && q.question) qEl.textContent = getVal(q.question);
      if(aEl && q.answer) aEl.textContent = getVal(q.answer);
    }
  }

  // ============ Contact ============
  if(page === 'contact' && pageData.info){
    var infoItems = document.querySelectorAll('.info-item');
    var infoKeys = [['email1Label','email1Value'],['email2Label','email2Value'],['locationLabel','locationValue'],['responseLabel','responseValue']];
    infoItems.forEach(function(item, i){
      if(!infoKeys[i]) return;
      var h = item.querySelector('h4'), p = item.querySelector('p');
      if(h && pageData.info[infoKeys[i][0]]) h.textContent = getVal(pageData.info[infoKeys[i][0]]);
      if(p && pageData.info[infoKeys[i][1]]) p.textContent = getVal(pageData.info[infoKeys[i][1]]);
    });
  }

  // ============ Privacy ============
  if(page === 'privacy'){
    var privacyCards = document.querySelectorAll('.privacy-card');
    for(var i = 1; i <= 3; i++){
      var s = pageData['s'+i];
      if(!s) continue;
      var card = privacyCards[i-1];
      if(!card) continue;
      var h = card.querySelector('h2'), p = card.querySelector('p');
      if(h && s.title) h.textContent = getVal(s.title);
      if(p && s.content) p.innerHTML = getVal(s.content).split('\\n').map(function(l){ return esc(l); }).join('<br>');
    }
  }
}

function applyFooter(data){
  if(!data) return;
  if(data.main){
    var p = document.querySelector('.foot-grid > div:first-child p');
    if(p && data.main.desc) p.textContent = getVal(data.main.desc);
    var c = document.querySelector('.foot-bottom');
    if(c && data.main.copyright) c.textContent = getVal(data.main.copyright);
  }
  if(data.links){
    var h4s = document.querySelectorAll('.foot-grid h4');
    if(h4s[0] && data.links.title1) h4s[0].textContent = getVal(data.links.title1);
    if(h4s[1] && data.links.title2) h4s[1].textContent = getVal(data.links.title2);
  }
}

function applyBrand(data){
  if(!data || !data.main) return;
  var b1 = data.main.name1 ? getVal(data.main.name1) : 'Shield';
  var b2 = data.main.name2 ? getVal(data.main.name2) : 'Scan';
  document.querySelectorAll('.brand-name').forEach(function(el){
    el.innerHTML = esc(b1) + '<b>' + esc(b2) + '</b>';
  });
  if(data.main.logo){
    var logo = getVal(data.main.logo);
    document.querySelectorAll('.brand-icon').forEach(function(el){
      if(!el.querySelector('img')) el.textContent = logo;
    });
  }
}

function getVal(x){
  if(x == null) return '';
  if(typeof x === 'object' && x.value != null) return x.value;
  return String(x);
}

function setText(selector, val){
  if(!val) return;
  var v = getVal(val);
  document.querySelectorAll(selector).forEach(function(el){ el.textContent = v; });
}

function esc(s){ var d = document.createElement('div'); d.textContent = s == null ? '' : s; return d.innerHTML; }

document.addEventListener('DOMContentLoaded', function(){
  setTimeout(loadPagesContent, 100);
});

})();
