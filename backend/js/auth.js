
/* ============ Real Email Validator ============ */
function isRealEmail(email){
  var lower = email.toLowerCase();
  // صيغة صحيحة
  if(!/^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$/.test(lower)) return { ok:false, msg:'صيغة بريد غير صالحة' };
  // نطاقات مؤقتة محظورة
  var temp = ['mailinator.com','guerrillamail.com','10minutemail.com','tempmail.com','throwaway.email','yopmail.com','sharklasers.com','trashmail.com','getnada.com','dispostable.com','fakeinbox.com','maildrop.cc','temp-mail.org','mailnesia.com','spam4.me'];
  var domain = lower.split('@')[1];
  if(temp.indexOf(domain) !== -1) return { ok:false, msg:'لا يمكن التسجيل ببريد مؤقت' };
  // انتحال نطاقات مشهورة
  var typos = ['gmal.com','gmial.com','gmai.com','gmail.co','gmail.con','gmail.cm','gmaill.com','yaho.com','yahooo.com','hotmal.com','hotmai.com','outlok.com','outloo.com'];
  if(typos.indexOf(domain) !== -1) return { ok:false, msg:'النطاق غير صحيح (ربما تقصد gmail.com؟)' };
  return { ok:true };
}

function initTheme(){var s=localStorage.getItem('theme')||'light';document.documentElement.setAttribute('data-theme',s);updateThemeIcon();}
function toggleTheme(){var c=document.documentElement.getAttribute('data-theme');var n=c==='dark'?'light':'dark';document.documentElement.setAttribute('data-theme',n);localStorage.setItem('theme',n);updateThemeIcon();}
function updateThemeIcon(){var b=document.getElementById('themeBtn');if(!b)return;b.textContent=document.documentElement.getAttribute('data-theme')==='dark'?'☀️':'🌙';}
function togglePass(id,btn){var i=document.getElementById(id);if(!i)return;if(i.type==='password'){i.type='text';btn.textContent='🙈';}else{i.type='password';btn.textContent='👁️';}}
function showAuthError(m){var e=document.getElementById('authError');if(!e)return;e.textContent=m;e.classList.remove('hidden');setTimeout(function(){e.classList.add('hidden');},4000);}

async function handleLogin(e){
  e.preventDefault();
  if(typeof SS==='undefined'){showAuthError('❌ api.js غير محمّل');return;}
  var em=document.getElementById('loginEmail').value.trim().toLowerCase();
  var p=document.getElementById('loginPass').value;
  var b=document.querySelector('.btn-auth');
  b.disabled=true;var o=b.textContent;b.textContent='⏳ جاري...';
  try{
    var r=await SS.login(em,p);
    b.disabled=false;b.textContent=o;
    if(!r.ok){showAuthError('❌ '+r.error);return;}
    b.textContent='✅ تم الدخول';
    if(document.getElementById('rememberMe').checked)localStorage.setItem('remember',em);
    setTimeout(function(){location.href='index.html';},600);
  }catch(err){
    b.disabled=false;b.textContent=o;
    showAuthError('❌ خطأ: '+err.message);
  }
}

async function handleRegister(e){
  e.preventDefault();
  if(typeof SS==='undefined'){showAuthError('❌ api.js غير محمّل');return;}
  var n=document.getElementById('regName').value.trim();
  var em=document.getElementById('regEmail').value.trim().toLowerCase();
  var p=document.getElementById('regPass').value;
  var p2=document.getElementById('regPass2').value;
  if(n.length<3){showAuthError('❌ الاسم قصير');return;}
  var emailCheck = isRealEmail(em);
  if(!emailCheck.ok){showAuthError('❌ ' + emailCheck.msg);return;}
  if(p.length<6){showAuthError('❌ كلمة المرور أقل من 6');return;}
  if(p!==p2){showAuthError('❌ غير متطابقتين');return;}
  var b=document.querySelector('.btn-auth');
  b.disabled=true;var o=b.textContent;b.textContent='⏳ جاري...';
  try{
    var r=await SS.register(n,em,p);
    b.disabled=false;b.textContent=o;
    if(!r.ok){showAuthError('❌ '+r.error);return;}
    b.textContent='🎉 تم';
    setTimeout(function(){location.href='index.html';},700);
  }catch(err){
    b.disabled=false;b.textContent=o;
    showAuthError('❌ خطأ: '+err.message);
  }
}

document.addEventListener('input',function(e){
  if(e.target.id!=='regPass')return;
  var v=e.target.value;
  var bar=document.querySelector('#passStrength .ps-bar span');
  var txt=document.querySelector('#passStrength .ps-text');
  if(!bar)return;
  var sc=0;
  if(v.length>=6)sc++;if(v.length>=10)sc++;
  if(/[A-Z]/.test(v))sc++;if(/[0-9]/.test(v))sc++;if(/[^A-Za-z0-9]/.test(v))sc++;
  var pct=[0,20,40,60,80,100][sc];
  bar.style.width=pct+'%';
  var colors=['#ef4444','#ef4444','#f59e0b','#f59e0b','#10b981','#10b981'];
  var labels=['ضعيفة جداً','ضعيفة','متوسطة','جيدة','قوية','قوية جداً'];
  bar.style.background=colors[sc];
  txt.textContent='قوة كلمة المرور: '+labels[sc];
  txt.style.color=colors[sc];
});

function logout(){if(window.SS)SS.logout();localStorage.removeItem('currentUser');location.href='index.html';}
function checkUserNav(){
  var u=window.SS?SS.currentUser():null;
  if(!u){try{u=JSON.parse(localStorage.getItem('currentUser')||'null');}catch(e){}}
  var l=document.getElementById('loginLink');
  var r=document.getElementById('registerLink');
  var m=document.getElementById('userMenu');
  var n=document.getElementById('userName');
  if(u){
    if(l)l.classList.add('hidden');
    if(r)r.classList.add('hidden');
    if(m)m.classList.remove('hidden');
    if(n)n.textContent='👤 '+(u.name||'').split(' ')[0];
  }else{
    if(m)m.classList.add('hidden');
  }
}
function toggleUserMenu(){var d=document.getElementById('userDropdown');if(d)d.classList.toggle('hidden');}
document.addEventListener('click',function(e){
  var d=document.getElementById('userDropdown');
  var m=document.getElementById('userMenu');
  if(!d||!m)return;
  if(!d.contains(e.target)&&!m.contains(e.target))d.classList.add('hidden');
});
document.addEventListener('DOMContentLoaded',function(){
  var p=location.pathname;
  if(window.SS&&SS.isLoggedIn()&&(p.endsWith('login.html')||p.endsWith('register.html'))){location.href='index.html';return;}
  var r=localStorage.getItem('remember');
  if(r&&document.getElementById('loginEmail')){
    document.getElementById('loginEmail').value=r;
    document.getElementById('rememberMe').checked=true;
  }
});
