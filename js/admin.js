(function(){
'use strict';
var VIEWS = {
  dashboard:['لوحة القيادة','نظرة عامة'],
  'pages-editor':['محتوى الصفحات','تحرير كل الصفحات'],
  content:['المحتوى','تحرير سريع'],
  design:['التصميم','الألوان'],
  images:['الصور','الشعار'],
  scans:['الفحوصات','السجل'],
  users:['المستخدمون','الحسابات'],
  messages:['الرسائل','الواردة'],
  backup:['النسخ الاحتياطي',''],
  settings:['الإعدادات','الأمان']
};
var PAGES_DATA = {};
var CURRENT_PAGE_KEY = 'index';

function esc(s){ var d=document.createElement('div'); d.textContent=s==null?'':s; return d.innerHTML; }
function toast(msg, type){
  var w = document.getElementById('admToastWrap');
  if(!w){ console.log(msg); return; }
  var t = document.createElement('div');
  t.className = 'adm-toast ' + (type||'info');
  t.innerHTML = '<span>' + (type==='success'?'✅':type==='error'?'❌':'ℹ️') + '</span><span>' + msg + '</span>';
  w.appendChild(t);
  setTimeout(function(){ t.classList.add('show'); }, 30);
  setTimeout(function(){ t.classList.remove('show'); setTimeout(function(){ t.remove(); }, 400); }, 3000);
}
function authHeader(){
  return {'Content-Type':'application/json', 'Authorization':'Bearer ' + (localStorage.getItem('ss_token')||'')};
}

var ADM = {};

ADM.login = async function(e){
  if(e) e.preventDefault();
  var u = document.getElementById('lUser').value.trim();
  var p = document.getElementById('lPass').value;
  if(typeof SS === 'undefined'){ toast('api.js غير محمّل','error'); return; }
  try{
    var r = await SS.login(u, p);
    if(!r.ok){ toast(r.error||'فشل','error'); return; }
    if(!r.data.user.is_admin){ toast('ليس أدمن','error'); SS.logout(); return; }
    toast('مرحباً ' + r.data.user.name, 'success');
    ADM.show();
  }catch(err){ toast('خطأ: '+err.message, 'error'); }
};

ADM.logout = function(){ if(typeof SS!=='undefined') SS.logout(); location.reload(); };

ADM.show = function(){
  var l = document.getElementById('admLogin');
  var d = document.getElementById('admDash');
  if(l) l.classList.add('hidden');
  if(d) d.classList.remove('hidden');
  ADM.init();
};

ADM.updateTheme = function(){
  var b = document.getElementById('themeBtn');
  if(b) b.textContent = document.documentElement.getAttribute('data-theme')==='dark'?'☀️':'🌙';
};
ADM.toggleTheme = function(){ if(window.toggleTheme) window.toggleTheme(); ADM.updateTheme(); };

ADM.go = function(v){
  document.querySelectorAll('.adm-link[data-view]').forEach(function(l){ l.classList.remove('active'); });
  document.querySelectorAll('.adm-view').forEach(function(x){ x.classList.remove('active'); });
  var link = document.querySelector('.adm-link[data-view="'+v+'"]');
  if(link) link.classList.add('active');
  var page = document.getElementById('view-'+v);
  if(page) page.classList.add('active');
  var meta = VIEWS[v]||['',''];
  var t = document.getElementById('admTitle'); if(t) t.textContent = meta[0];
  var s = document.getElementById('admSubtitle'); if(s) s.textContent = meta[1];
  if(window.innerWidth <= 900) ADM.closeSide();
  if(v==='pages-editor') ADM.pagesLoad();
  if(v==='scans') ADM.loadScans();
  if(v==='users') ADM.loadUsers();
  if(v==='messages') ADM.loadMessages();
  if(v==='dashboard') ADM.loadDashboard();
  if(v==='content') ADM.loadContent();
  if(v==='design') ADM.loadDesign();
  if(v==='images') ADM.loadImages();
};

ADM.toggleSide = function(){
  var s = document.getElementById('admSide'), o = document.getElementById('admOverlay');
  if(s) s.classList.toggle('open');
  if(o) o.classList.toggle('open');
};
ADM.closeSide = function(){
  var s = document.getElementById('admSide'), o = document.getElementById('admOverlay');
  if(s) s.classList.remove('open');
  if(o) o.classList.remove('open');
};

/* DASHBOARD */
ADM.loadDashboard = async function(){
  try{
    var s = await SS.adminStats();
    if(!s) return;
    var set = function(id, v){ var e = document.getElementById(id); if(e) e.textContent = v; };
    set('kpiUrls', s.url_scans || 0);
    set('kpiFiles', s.file_scans || 0);
    set('kpiEmails', s.email_scans || 0);
    set('kpiThreats', s.threats || 0);
    set('kpiUsers', s.users || 0);
    set('cntScans', s.scans || 0);
    set('cntUsers', s.users || 0);
    set('cntMsgs', s.messages || 0);
    ADM.loadRecent();
  }catch(e){}
};

ADM.loadRecent = async function(){
  try{
    var scans = await SS.adminScans();
    var r = document.getElementById('recentScans');
    if(!r) return;
    var list = (scans||[]).slice(0,5);
    if(!list.length){ r.innerHTML = '<div class="adm-empty">📭 لا توجد</div>'; return; }
    r.innerHTML = list.map(function(s){
      var ico = s.type==='url'?'🔗':s.type==='email'?'📧':'📁';
      var st = s.status==='safe'?'آمن':s.status==='danger'?'خطير':'مشتبه';
      return '<div class="adm-recent-item"><span>'+ico+'</span><div><b>'+esc(s.target)+'</b><span>'+st+' • '+esc(s.created_at||'')+'</span></div></div>';
    }).join('');
  }catch(e){}
};

/* PAGES EDITOR */
ADM.pagesLoad = function(){
  var loading = document.getElementById('pagesEditorLoading');
  var content = document.getElementById('pagesEditorContent');
  if(loading){ loading.style.display = 'block'; loading.innerHTML = '⏳ جاري التحميل...'; }
  if(content) content.style.display = 'none';
  fetch('/api/pages')
    .then(function(r){ if(!r.ok) throw new Error('HTTP '+r.status); return r.json(); })
    .then(function(data){
      PAGES_DATA = data || {};
      if(loading) loading.style.display = 'none';
      if(content) content.style.display = 'block';
      ADM.pagesRender();
    })
    .catch(function(e){
      if(loading){
        loading.innerHTML = '<div style="color:#ef4444;padding:20px;text-align:center">❌ '+e.message+'</div><div style="text-align:center;margin-top:10px"><button onclick="ADM.pagesLoad()" style="padding:10px 20px;background:#6366f1;color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:700">🔄 حاول</button></div>';
      }
    });
};
ADM.pagesReload = function(){ ADM.pagesLoad(); };

ADM.pagesTab = function(page){
  CURRENT_PAGE_KEY = page;
  document.querySelectorAll('[data-pagetab]').forEach(function(b){ b.classList.remove('active'); });
  var btn = document.querySelector('[data-pagetab="'+page+'"]');
  if(btn) btn.classList.add('active');
  ADM.pagesRender();
};

ADM.pagesRender = function(){
  var content = document.getElementById('pagesEditorContent');
  if(!content) return;
  var pageData = PAGES_DATA[CURRENT_PAGE_KEY] || {};
  var titleMap = {hero:'🎯 الهيرو',scanner:'🔍 الفحص',quick:'⚡ البطاقات',cta:'🚀 دعوة',info:'📞 معلومات',main:'📌 المحتوى',links:'🔗 روابط',f1:'⚡ ميزة 1',f2:'🔒 ميزة 2',f3:'🛡️ ميزة 3',f4:'📊 ميزة 4',f5:'🆓 ميزة 5',f6:'🌙 ميزة 6',f7:'📱 ميزة 7',f8:'🚀 ميزة 8',f9:'🔄 ميزة 9',q1:'❓ سؤال 1',q2:'❓ سؤال 2',q3:'❓ سؤال 3',q4:'❓ سؤال 4',q5:'❓ سؤال 5',q6:'❓ سؤال 6',s1:'📄 قسم 1',s2:'📄 قسم 2',s3:'📄 قسم 3'};
  var sections = Object.keys(pageData);
  if(sections.length === 0){
    content.innerHTML = '<div style="text-align:center;padding:50px 20px;color:#94a3b8;font-size:15px">📭 لا يوجد محتوى</div>';
    return;
  }
  var html = '';
  sections.forEach(function(section){
    var fields = pageData[section];
    var sectionTitle = titleMap[section] || ('📌 '+section);
    html += '<div style="background:#f8fafc;border:2px solid #e2e8f0;border-radius:14px;padding:20px;margin-bottom:16px">';
    html += '<h4 style="margin:0 0 16px;color:#0f172a;font-size:14px;font-weight:800;padding-bottom:10px;border-bottom:2px solid #fff">'+sectionTitle+'</h4>';
    Object.keys(fields).forEach(function(key){
      var value = fields[key] || '';
      var isLong = (typeof value === 'string' && (value.length > 70 || key==='desc' || key==='content' || key==='answer'));
      var fid = 'f_'+CURRENT_PAGE_KEY+'_'+section+'_'+key;
      html += '<div style="margin-bottom:12px">';
      html += '<label style="display:block;font-size:12px;color:#64748b;font-weight:700;margin-bottom:6px">'+esc(key)+'</label>';
      if(isLong){
        html += '<textarea id="'+fid+'" data-page="'+CURRENT_PAGE_KEY+'" data-sec="'+section+'" data-key="'+key+'" rows="3" style="width:100%;padding:12px;border:2px solid #e2e8f0;border-radius:10px;font-family:inherit;font-size:14px;background:#fff;color:#1e293b;resize:vertical;box-sizing:border-box">'+esc(value)+'</textarea>';
      }else{
        html += '<input type="text" id="'+fid+'" data-page="'+CURRENT_PAGE_KEY+'" data-sec="'+section+'" data-key="'+key+'" value="'+esc(value)+'" style="width:100%;padding:12px;border:2px solid #e2e8f0;border-radius:10px;font-family:inherit;font-size:14px;background:#fff;color:#1e293b;box-sizing:border-box">';
      }
      html += '</div>';
    });
    html += '</div>';
  });
  content.innerHTML = html;
};

ADM.pagesSaveAll = function(){
  var fields = document.querySelectorAll('[data-page][data-sec][data-key]');
  if(!fields.length){ toast('لا توجد حقول','error'); return; }
  var data = {};
  fields.forEach(function(f){
    var p = f.getAttribute('data-page'), s = f.getAttribute('data-sec'), k = f.getAttribute('data-key');
    if(!data[p]) data[p] = {};
    if(!data[p][s]) data[p][s] = {};
    data[p][s][k] = f.value;
  });
  fetch('/api/admin/pages', {method:'POST', headers: authHeader(), body: JSON.stringify(data)})
    .then(function(r){ return r.json(); })
    .then(function(d){
      if(d.success) toast('✅ تم حفظ '+d.updated+' حقل','success');
      else toast('❌ '+(d.error||'فشل'),'error');
    })
    .catch(function(e){ toast('❌ '+e.message,'error'); });
};

/* CONTENT */
ADM.loadContent = async function(){
  try{
    var c = await SS.getContent();
    if(!c) return;
    document.querySelectorAll('[data-c]').forEach(function(el){
      var k = el.getAttribute('data-c');
      if(c[k] != null) el.value = c[k];
    });
  }catch(e){}
};
ADM.contentSave = async function(){
  var obj = {};
  document.querySelectorAll('[data-c]').forEach(function(el){ obj[el.getAttribute('data-c')] = el.value; });
  var r = await SS.adminUpdateContent(obj);
  toast(r.ok?'تم الحفظ':r.error, r.ok?'success':'error');
};
ADM.contentReset = function(){ if(confirm('استعادة؟')) location.reload(); };

/* DESIGN */
ADM.loadDesign = async function(){
  try{
    var d = await SS.getDesign();
    if(!d) return;
    var set = function(id,v){ var e=document.getElementById(id); if(e) e.value=v; };
    set('cPrimary', d.primary); set('cSecondary', d.secondary); set('cAccent', d.accent);
    set('cBg', d.bg); set('cText', d.text); set('cMuted', d.muted);
    set('rSize', d.size); set('rRadius', d.radius);
    var s1 = document.getElementById('rSizeV'), s2 = document.getElementById('rRadiusV');
    if(s1) s1.textContent = d.size+'%';
    if(s2) s2.textContent = d.radius+'%';
  }catch(e){}
};
ADM.designSave = async function(){
  var v = function(id){ var e = document.getElementById(id); return e?e.value:''; };
  var r = await SS.adminUpdateDesign({
    primary:v('cPrimary'),secondary:v('cSecondary'),accent:v('cAccent'),
    bg:v('cBg'),text:v('cText'),muted:v('cMuted'),size:v('rSize'),radius:v('rRadius')
  });
  toast(r.ok?'تم الحفظ':r.error, r.ok?'success':'error');
};
ADM.designReset = function(){ if(confirm('استعادة؟')) location.reload(); };

/* IMAGES */
ADM.loadImages = function(){
  var imgs = {}; try{ imgs = JSON.parse(localStorage.getItem('siteImages')||'{}'); }catch(e){}
  var lp = document.getElementById('logoPrev'), le = document.getElementById('logoEmoji');
  if(lp){
    if(imgs.logoData) lp.innerHTML = '<img src="'+imgs.logoData+'" style="max-width:100%;max-height:100%">';
    else lp.textContent = imgs.logoEmoji || '🛡️';
  }
  if(le) le.value = imgs.logoEmoji || '';
};
ADM.uploadLogo = function(e){
  var f = e.target.files[0]; if(!f) return;
  var r = new FileReader();
  r.onload = function(ev){
    var imgs = {}; try{ imgs = JSON.parse(localStorage.getItem('siteImages')||'{}'); }catch(e){}
    imgs.logoData = ev.target.result;
    localStorage.setItem('siteImages', JSON.stringify(imgs));
    ADM.loadImages();
    toast('تم الرفع','success');
  };
  r.readAsDataURL(f);
};
ADM.removeLogo = function(){
  var imgs = {}; try{ imgs = JSON.parse(localStorage.getItem('siteImages')||'{}'); }catch(e){}
  delete imgs.logoData;
  localStorage.setItem('siteImages', JSON.stringify(imgs));
  ADM.loadImages();
  toast('تم الحذف','info');
};

/* SCANS */
ADM.loadScans = async function(){
  try{
    var scans = await SS.adminScans();
    var tb = document.getElementById('scansBody');
    if(!tb) return;
    if(!scans || !scans.length){ tb.innerHTML = '<tr><td colspan="4"><div class="adm-empty">📭 لا توجد</div></td></tr>'; return; }
    tb.innerHTML = scans.map(function(s,i){
      var type = s.type==='url'?'🔗':s.type==='email'?'📧':'📁';
      var tag = s.status==='safe'?'آمن':s.status==='danger'?'خطير':'مشتبه';
      return '<tr><td>'+(i+1)+'</td><td>'+type+'</td><td style="max-width:250px;word-break:break-all">'+esc(s.target)+'</td><td><span class="adm-tag '+s.status+'">'+tag+'</span></td></tr>';
    }).join('');
  }catch(e){}
};
ADM.scansClear = async function(){
  if(!confirm('حذف كل الفحوصات؟')) return;
  var r = await SS.adminClearScans();
  if(r.ok){ ADM.loadScans(); ADM.loadDashboard(); toast('تم','info'); }
};

/* USERS */
ADM.loadUsers = async function(){
  try{
    var users = await SS.adminUsers();
    var tb = document.getElementById('usersBody');
    if(!tb) return;
    if(!users || !users.length){ tb.innerHTML = '<tr><td colspan="4"><div class="adm-empty">📭 لا يوجد</div></td></tr>'; return; }
    tb.innerHTML = users.map(function(u,i){
      var ban = u.is_banned ? '<button class="adm-btn-mini" style="background:#d1fae5;color:#065f46" onclick="ADM.ban('+u.id+')">✅</button>' : '<button class="adm-btn-mini" style="background:#fef3c7;color:#92400e" onclick="ADM.ban('+u.id+')">🚫</button>';
      return '<tr><td>'+(i+1)+'</td><td>'+esc(u.name)+'</td><td>'+esc(u.email)+'</td><td>'+ban+' <button class="adm-btn-mini" onclick="ADM.delUser('+u.id+')">🗑️</button></td></tr>';
    }).join('');
  }catch(e){}
};
ADM.delUser = async function(id){
  if(!confirm('حذف؟')) return;
  var r = await SS.adminDelUser(id);
  if(r.ok){ ADM.loadUsers(); ADM.loadDashboard(); toast('تم','info'); }
  else toast(r.error||'فشل','error');
};
ADM.ban = async function(id){ await SS.adminBanUser(id); ADM.loadUsers(); toast('تم','info'); };

/* MESSAGES */
ADM.loadMessages = async function(){
  try{
    var msgs = await SS.adminMessages();
    var w = document.getElementById('msgsList');
    if(!w) return;
    if(!msgs || !msgs.length){ w.innerHTML = '<div class="adm-empty">📭 لا توجد</div>'; return; }
    w.innerHTML = msgs.map(function(m){
      return '<div class="adm-msg"><div class="adm-msg-head"><b>'+esc(m.name)+' — '+esc(m.email)+'</b><span>'+esc(m.created_at||'')+'</span></div><div class="adm-msg-sub">'+esc(m.subject||'—')+'</div><div class="adm-msg-body">'+esc(m.message)+'</div></div>';
    }).join('');
  }catch(e){}
};
ADM.msgsClear = async function(){
  if(!confirm('حذف كل الرسائل؟')) return;
  var r = await SS.adminClearMessages();
  if(r.ok){ ADM.loadMessages(); ADM.loadDashboard(); toast('تم','info'); }
};

/* SETTINGS */
ADM.changePass = async function(e){
  e.preventDefault();
  var old = document.getElementById('cpOld').value;
  var np = document.getElementById('cpNew').value;
  var np2 = document.getElementById('cpNew2').value;
  if(np.length < 6) return toast('قصيرة','error');
  if(np !== np2) return toast('غير متطابقتين','error');
  var r = await SS.adminChangePassword(old, np);
  if(r.ok){ e.target.reset(); toast('تم','success'); }
  else toast(r.error||'فشل','error');
};

ADM.export = function(){
  var data = {};
  ['siteContent','siteDesign','siteImages','users','scans','messages'].forEach(function(k){
    var v = localStorage.getItem(k); if(v) data[k] = v;
  });
  var blob = new Blob([JSON.stringify(data,null,2)], {type:'application/json'});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'shieldscan-'+Date.now()+'.json';
  a.click();
  toast('تم التصدير','success');
};
ADM.import = function(e){
  var f = e.target.files[0]; if(!f) return;
  var r = new FileReader();
  r.onload = function(ev){
    try{
      var data = JSON.parse(ev.target.result);
      Object.keys(data).forEach(function(k){ if(data[k]) localStorage.setItem(k, data[k]); });
      toast('تم','success');
      setTimeout(function(){ location.reload(); }, 1000);
    }catch(err){ toast('ملف غير صالح','error'); }
  };
  r.readAsText(f);
};
ADM.wipeAll = function(){
  if(!confirm('⚠️ حذف كل البيانات؟')) return;
  if(!confirm('⚠️ تأكيد!')) return;
  ['siteContent','siteDesign','siteImages','users','scans','messages'].forEach(function(k){ localStorage.removeItem(k); });
  toast('تم','info');
  setTimeout(function(){ location.reload(); }, 1000);
};

/* INIT */
ADM.init = function(){
  ADM.updateTheme();
  ADM.loadDashboard();
  document.querySelectorAll('.adm-link[data-view]').forEach(function(l){
    l.addEventListener('click', function(e){ e.preventDefault(); ADM.go(l.getAttribute('data-view')); });
  });
  var lf = document.getElementById('loginForm');
  if(lf) lf.addEventListener('submit', ADM.login);
  function tick(){
    var s = null; try{ s = JSON.parse(localStorage.getItem('admSession2')||'null'); }catch(e){}
    if(!s || !s.exp) return;
    var left = s.exp - Date.now();
    if(left <= 0){ location.reload(); return; }
    var m = Math.floor(left/60000);
    var el = document.getElementById('sessionTime'); if(el) el.textContent = m+' د';
  }
  tick();
  setInterval(tick, 60000);
};

document.addEventListener('DOMContentLoaded', function(){
  if(typeof SS === 'undefined') return;
  if(!SS.isLoggedIn()) return;
  var u = SS.currentUser();
  if(u && u.is_admin){ ADM.show(); return; }
  SS.me().then(function(r){
    if(r.ok && r.data && r.data.user && r.data.user.is_admin){
      localStorage.setItem('ss_user', JSON.stringify(r.data.user));
      ADM.show();
    }
  }).catch(function(){});
});

window.ADM = ADM;
})();
