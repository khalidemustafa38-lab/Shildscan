/* ============================================
   ShieldScan — Main Script
   ============================================ */

/* ============ Theme ============ */
function initTheme(){
  var saved = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-theme', saved);
  updateThemeIcon();
}
function toggleTheme(){
  var cur = document.documentElement.getAttribute('data-theme');
  var next = cur === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
  updateThemeIcon();
}
function updateThemeIcon(){
  var b = document.getElementById('themeBtn');
  if(!b) return;
  b.textContent = document.documentElement.getAttribute('data-theme') === 'dark' ? '☀️' : '🌙';
}

/* ============ Tabs ============ */
document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('.tab').forEach(function(t){
    t.addEventListener('click', function(){
      document.querySelectorAll('.tab').forEach(function(x){ x.classList.remove('active'); });
      document.querySelectorAll('.panel').forEach(function(x){ x.classList.remove('active'); });
      t.classList.add('active');
      var p = document.getElementById(t.dataset.tab + '-panel');
      if(p) p.classList.add('active');
      var r = document.getElementById('result');
      if(r) r.classList.add('hidden');
    });
  });
});

/* ============ Helpers ============ */
function esc(s){ var d=document.createElement('div'); d.textContent=s==null?'':s; return d.innerHTML; }
function sleep(ms){ return new Promise(function(r){ setTimeout(r,ms); }); }
function formatSize(b){ return b<1024?b+' B':b<1048576?(b/1024).toFixed(1)+' KB':(b/1048576).toFixed(1)+' MB'; }
function isValidUrl(x){ try{ var u=new URL(x); return u.protocol==='http:'||u.protocol==='https:'; }catch(e){ return false; } }

/* ============ Auth Guard ============ */
function requireLogin(){
  if(window.SS && SS.isLoggedIn()) return true;
  showLoginRequired();
  return false;
}
function showLoginRequired(){
  var r = document.getElementById('result');
  if(!r) return;
  r.className = 'result warning';
  r.innerHTML = '<div class="result-head"><span class="emoji">🔒</span><div><h3>تسجيل الدخول مطلوب</h3><p>يجب تسجيل الدخول أولاً لتتمكن من الفحص</p></div></div>' +
    '<div style="display:flex;gap:10px;margin-top:16px;flex-wrap:wrap">' +
    '<a href="login.html" style="flex:1;min-width:140px;padding:14px;background:linear-gradient(135deg,#6366f1,#ec4899);color:#fff;text-decoration:none;border-radius:12px;font-weight:800;text-align:center">🔐 تسجيل الدخول</a>' +
    '<a href="register.html" style="flex:1;min-width:140px;padding:14px;background:#f1f5f9;color:#6366f1;text-decoration:none;border-radius:12px;font-weight:800;text-align:center;border:2px solid #e0e7ff">✨ حساب جديد</a>' +
    '</div>';
  r.classList.remove('hidden');
  r.scrollIntoView({behavior:'smooth',block:'center'});
}

/* ============ Result Display ============ */
function showResult(type, emoji, title, msg, rows, reasons, recommend){
  var r = document.getElementById('result');
  if(!r) return;
  r.className = 'result ' + type;

  var html = '<div class="result-head">' +
    '<span class="emoji">' + emoji + '</span>' +
    '<div><h3>' + title + '</h3><p>' + msg + '</p></div>' +
  '</div>';

  if(rows && rows.length){
    html += '<div class="result-body">' + rows.map(function(a){
      return '<div class="row"><span>'+a[0]+'</span><span>'+esc(String(a[1]))+'</span></div>';
    }).join('') + '</div>';
  }

  if(reasons && reasons.length){
    html += '<div class="result-reasons">' +
      '<h4>لماذا هذه النتيجة؟</h4>' +
      '<ul>' + reasons.map(function(x){ return '<li>'+esc(x)+'</li>'; }).join('') + '</ul>' +
    '</div>';
  }

  if(recommend){
    html += '<div class="result-recommend">' +
      '<span class="rec-icon">' + recommend.i + '</span>' +
      '<span class="rec-text">' + recommend.t + '</span>' +
    '</div>';
  }

  r.innerHTML = html;
  r.classList.remove('hidden');
  r.scrollIntoView({behavior:'smooth', block:'center'});
}

function showLoading(text){
  var r = document.getElementById('result');
  if(!r) return;
  r.className = 'result warning';
  r.innerHTML = '<div style="text-align:center;padding:45px 20px">' +
    '<div class="spinner" style="width:48px;height:48px;border:5px solid #fde68a;border-top-color:#d97706;border-radius:50%;animation:spin 1s linear infinite;margin:0 auto"></div>' +
    '<p style="margin-top:16px;color:#92400e;font-weight:800;font-size:15px">' + text + '</p>' +
  '</div>';
  r.classList.remove('hidden');
  r.scrollIntoView({behavior:'smooth', block:'center'});
}

/* ============ URL Scan ============ */
function fillUrl(u){ var i=document.getElementById('urlInput'); if(i){ i.value = u; scanUrl(); } }

async function scanUrl(){
  if(!requireLogin()) return;
  var url = document.getElementById('urlInput').value.trim();
  if(!url) return showResult('error','⚠️','لم يتم إدخال رابط','الرجاء إدخال رابط صحيح.');
  if(!isValidUrl(url)) return showResult('error','⚠️','رابط غير صالح','تأكد من صيغة الرابط (https://...)');

  showLoading('جاري فحص الرابط…');
  var status = 'safe', reasons = [];

  try{
    var r = await fetch(location.origin + '/api/scan/url', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({url:url})
    });
    var data = await r.json();
    if(data.error) return showResult('error','⚠️','خطأ في الفحص', data.error);
    status = data.status || 'safe';
    if(data.malicious > 0) reasons.push('الرابط مصنّف كموقع ضار أو تصيد احتيالي');
    else if(data.suspicious > 0) reasons.push('الرابط يحتوي على عناصر مشبوهة');
    else reasons.push('لم يتم رصد أي تهديد في هذا الرابط');
  }catch(e){
    return showResult('error','⚠️','فشل الاتصال','تعذّر الوصول إلى السيرفر');
  }

  if(status === 'danger'){
    showResult('danger','🚨','رابط خطير','لا تفتح هذا الرابط',
      [['الرابط', url]], reasons,
      {i:'🚫', t:'لا تفتح هذا الرابط — احذفه من أي رسالة'});
  } else if(status === 'warning'){
    showResult('warning','⚠️','رابط مشتبه به','توخَّ الحذر قبل فتحه',
      [['الرابط', url]], reasons,
      {i:'⚠️', t:'لا تُدخل بياناتك — افتحه فقط إذا كنت واثقاً'});
  } else {
    showResult('safe','✅','رابط آمن','يمكنك فتحه بأمان',
      [['الرابط', url]], reasons,
      {i:'✅', t:'يمكنك فتح الرابط دون قلق'});
  }

  if(window.SS) SS.saveScan('url', url, status, reasons.join(' • '));
  logScanLocal('url', url, status);
}

/* ============ File Scan ============ */
var dz = document.getElementById('dropzone');
var fi = document.getElementById('fileInput');
var pickedFile = null;

if(dz){
  dz.addEventListener('click', function(){ fi.click(); });
  dz.addEventListener('dragover', function(e){ e.preventDefault(); dz.classList.add('dragover'); });
  dz.addEventListener('dragleave', function(){ dz.classList.remove('dragover'); });
  dz.addEventListener('drop', function(e){ e.preventDefault(); dz.classList.remove('dragover'); if(e.dataTransfer.files[0]) pickFile(e.dataTransfer.files[0]); });
  if(fi) fi.addEventListener('change', function(e){ if(e.target.files[0]) pickFile(e.target.files[0]); });
}

function pickFile(f){
  if(f.size > 50*1024*1024) return showResult('error','⚠️','ملف كبير جداً','الحد الأقصى 50 ميجابايت.');
  pickedFile = f;
  var p = document.getElementById('filePreview');
  p.innerHTML = '<div>📄 <b>'+esc(f.name)+'</b> — '+formatSize(f.size)+'</div><button onclick="clearFile()">✕</button>';
  p.classList.remove('hidden');
  document.getElementById('result').classList.add('hidden');
}
function clearFile(){ pickedFile=null; if(fi) fi.value=''; document.getElementById('filePreview').classList.add('hidden'); }

async function scanFile(){
  if(!requireLogin()) return;
  if(!pickedFile) return showResult('error','⚠️','لا يوجد ملف','الرجاء اختيار ملف.');

  showLoading('جاري فحص الملف…');
  var status = 'safe', msg = '', reasons = [];

  try{
    var fd = new FormData();
    fd.append('file', pickedFile);
    var r = await fetch(location.origin + '/api/scan/file', {method:'POST', body: fd});
    var data = await r.json();
    if(data.error) return showResult('error','⚠️','خطأ في الفحص', data.error);
    status = data.status || 'safe';
    msg = data.message || '';
    if(data.queued) status = 'warning';

    if(data.malicious > 0) reasons.push('الملف مصنّف كبرمجية ضارة');
    else if(data.suspicious > 0) reasons.push('الملف يحتوي على عناصر مشبوهة');
    else if(data.queued) reasons.push('الملف قيد الفحص — قد يستغرق دقائق');
    else reasons.push('لم يتم رصد أي تهديد في هذا الملف');
  }catch(e){
    return showResult('error','⚠️','فشل الاتصال','تعذّر رفع الملف');
  }

  if(status === 'danger'){
    showResult('danger','🚨','ملف خطير','لا تفتح هذا الملف',
      [['الملف', pickedFile.name]], reasons,
      {i:'🚫', t:'احذف الملف فوراً من جهازك'});
  } else if(status === 'warning'){
    showResult('warning','⚠️', msg || 'قيد الفحص','انتظر اكتمال الفحص',
      [['الملف', pickedFile.name]], reasons,
      {i:'⚠️', t:'لا تفتح الملف حتى ينتهي الفحص'});
  } else {
    showResult('safe','✅','ملف آمن','يمكنك فتحه بأمان',
      [['الملف', pickedFile.name]], reasons,
      {i:'✅', t:'يمكنك فتح الملف دون قلق'});
  }

  if(window.SS) SS.saveScan('file', pickedFile.name, status, reasons.join(' • '));
  logScanLocal('file', pickedFile.name, status);
}

/* ============ Email Scan ============ */
async function scanEmailBody(){
  if(!requireLogin()) return;
  var body = (document.getElementById('emailBody')||{}).value || '';
  if(body.trim().length < 5){
    return showResult('error','⚠️','لم يتم إدخال نص','الرجاء لصق محتوى الرسالة أولاً.');
  }

  showLoading('جاري تحليل الرسالة…');
  var data = null;
  try{
    var r = await fetch(location.origin + '/api/scan/email', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({email:'', body: body})
    });
    data = await r.json();
    if(data.error) return showResult('error','⚠️','خطأ', data.error);
  }catch(e){
    return showResult('error','⚠️','فشل الاتصال','تعذّر تحليل الرسالة');
  }

  var summary = data.summary || {};
  var urlResults = data.url_results || [];
  var issues = data.issues || [];
  var dU = urlResults.filter(function(u){ return u.status==='danger'; }).length;
  var wU = urlResults.filter(function(u){ return u.status==='warning'; }).length;

  var status = 'safe';
  if(dU > 0) status = 'danger';
  else if(wU > 0 || issues.length > 0) status = 'warning';

  var reasons = [];
  if(dU > 0) reasons.push('تحتوي على ' + dU + ' رابط ضار');
  if(wU > 0) reasons.push('تحتوي على ' + wU + ' رابط مشتبه به');
  issues.forEach(function(i){
    var m = i.msg.replace(/^يحتوي على /,'');
    if(reasons.indexOf(m) === -1) reasons.push(m);
  });
  if(!reasons.length) reasons.push('لا توجد مؤشرات خطر في الرسالة');

  var rows = [];
  if(summary.total_urls > 0) rows.push(['الروابط المكتشفة', summary.total_urls]);

  if(status === 'danger'){
    showResult('danger','🚨','رسالة خطيرة','تحتوي على محتوى ضار أو تصيد احتيالي',
      rows, reasons,
      {i:'🚫', t:'لا تضغط على أي رابط — احذف الرسالة فوراً'});
  } else if(status === 'warning'){
    showResult('warning','⚠️','رسالة مشتبه بها','تحتوي على عناصر تستدعي الحذر',
      rows, reasons,
      {i:'⚠️', t:'لا تُدخل أي بيانات شخصية'});
  } else {
    showResult('safe','✅','رسالة آمنة','لم يتم العثور على مؤشرات خطر',
      rows, reasons,
      {i:'✅', t:'يمكنك التعامل معها بشكل طبيعي'});
  }

  if(window.SS) SS.saveScan('email', 'رسالة نصية', status, reasons.join(' • '));
  logScanLocal('email', 'رسالة نصية', status);
}

/* ============ Local Log ============ */
function logScanLocal(type, target, status){
  try{
    var arr = JSON.parse(localStorage.getItem('scans') || '[]');
    arr.unshift({type:type, target:target, status:status, date:new Date().toLocaleString('ar-EG')});
    localStorage.setItem('scans', JSON.stringify(arr.slice(0,200)));
  }catch(e){}
}

/* ============ FAQ ============ */
function toggleFaq(el){ el.classList.toggle('active'); }

/* ============ Mobile Menu ============ */
function toggleMobileMenu(){
  var mm = document.getElementById('mobileMenu');
  var hb = document.getElementById('hamburger');
  if(!mm || !hb) return;
  mm.classList.toggle('hidden');
  hb.classList.toggle('active');
}

/* ============ User Nav ============ */
function getCurrentUser(){
  if(window.SS) return SS.currentUser();
  try{ return JSON.parse(localStorage.getItem('currentUser') || 'null'); }catch(e){ return null; }
}
function checkUserNav(){
  var u = getCurrentUser();
  var l = document.getElementById('loginLink');
  var r = document.getElementById('registerLink');
  var m = document.getElementById('userMenu');
  var n = document.getElementById('userName');
  if(u){
    if(l) l.classList.add('hidden');
    if(r) r.classList.add('hidden');
    if(m) m.classList.remove('hidden');
    if(n) n.textContent = '👤 ' + (u.name || '').split(' ')[0];
  }else{
    if(m) m.classList.add('hidden');
  }
}
function toggleUserMenu(){
  var d = document.getElementById('userDropdown');
  if(d) d.classList.toggle('hidden');
}
function logout(){
  if(window.SS) SS.logout();
  localStorage.removeItem('currentUser');
  location.href = 'index.html';
}
document.addEventListener('click', function(e){
  var dd = document.getElementById('userDropdown');
  var mn = document.getElementById('userMenu');
  if(!dd || !mn) return;
  if(!dd.contains(e.target) && !mn.contains(e.target)) dd.classList.add('hidden');
});

/* ============ Contact Form ============ */
async function handleContact(e){
  e.preventDefault();
  var name = document.getElementById('cName').value.trim();
  var email = document.getElementById('cEmail').value.trim();
  var subject = document.getElementById('cSubject').value;
  var message = document.getElementById('cMessage').value.trim();
  var ok = document.getElementById('contactSuccess');
  var err = document.getElementById('contactError');
  if(name.length < 3 || message.length < 10){
    if(err){ err.textContent = '❌ تأكد من ملء الحقول'; err.classList.remove('hidden'); }
    return;
  }
  var btn = e.target.querySelector('button[type="submit"]');
  var old = btn.textContent;
  btn.disabled = true;
  btn.textContent = '⏳ جاري...';
  var r = await SS.sendMessage(name, email, subject, message);
  btn.disabled = false;
  btn.textContent = old;
  if(!r.ok){
    if(err){ err.textContent = '❌ ' + r.error; err.classList.remove('hidden'); }
    return;
  }
  if(ok){ ok.classList.remove('hidden'); setTimeout(function(){ ok.classList.add('hidden'); }, 5000); }
  e.target.reset();
}

/* ============ Apply Admin Customizations ============ */
async function applySiteCustomizations(){
  var design = null, content = null;
  try{
    if(window.SS){
      design = await SS.getDesign();
      content = await SS.getContent();
    }
  }catch(e){}
  if(!design){ try{ design = JSON.parse(localStorage.getItem('siteDesign')||'{}'); }catch(e){ design={}; } }
  if(!content){ try{ content = JSON.parse(localStorage.getItem('siteContent')||'{}'); }catch(e){ content={}; } }
  if(!design || !content) return;

  if(design.primary || design.secondary || design.accent){
    var p = design.primary || '#6366f1', s = design.secondary || '#8b5cf6', a = design.accent || '#ec4899';
    document.documentElement.style.setProperty('--p', p);
    document.documentElement.style.setProperty('--p2', s);
    document.documentElement.style.setProperty('--pink', a);
    document.documentElement.style.setProperty('--grad', 'linear-gradient(135deg,'+p+','+s+' 50%,'+a+')');
  }
  if(design.bg) document.documentElement.style.setProperty('--bg', design.bg);
  if(design.text) document.documentElement.style.setProperty('--txt', design.text);
  if(design.muted) document.documentElement.style.setProperty('--muted', design.muted);

  if(design.size && parseInt(design.size) !== 100){
    document.documentElement.style.fontSize = (16 * parseInt(design.size) / 100) + 'px';
  }

  var q = function(s){ return document.querySelector(s); };
  if(content.heroPill && q('.hero .pill')) q('.hero .pill').textContent = content.heroPill;
  if(content.heroT1 && q('.hero h1')){
    q('.hero h1').innerHTML = esc(content.heroT1) + ' <span class="grad">رابط</span> أو <span class="grad">ملف</span><br>' + esc(content.heroT2 || '');
  }
  if(content.heroDesc && q('.hero p')) q('.hero p').textContent = content.heroDesc;

  var tabs = document.querySelectorAll('.tab');
  if(tabs[0] && content.tabUrl) tabs[0].textContent = content.tabUrl;
  if(tabs[1] && content.tabFile) tabs[1].textContent = content.tabFile;

  var btns = document.querySelectorAll('.btn-scan');
  if(btns[0] && content.btnUrl) btns[0].textContent = content.btnUrl;
  if(btns[1] && content.btnFile) btns[1].textContent = content.btnFile;

  var fc = q('.foot-bottom');
  if(fc && content.footCopy) fc.textContent = content.footCopy;

  if(content.brand1 || content.brand2){
    document.querySelectorAll('.brand-name').forEach(function(el){
      el.innerHTML = esc(content.brand1 || 'Shield') + '<b>' + esc(content.brand2 || 'Scan') + '</b>';
    });
  }
}

/* ============ Init ============ */
document.addEventListener('DOMContentLoaded', function(){
  initTheme();
  checkUserNav();
  applySiteCustomizations();
});
window.addEventListener('scroll', function(){
  var t = document.getElementById('toTop');
  if(t) t.classList.toggle('show', window.scrollY > 500);
});
