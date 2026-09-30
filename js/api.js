/* ============================================
   ShieldScan API Layer
   ============================================ */
(function(){
'use strict';

var API_BASE = (location.origin && location.origin !== 'null')
  ? location.origin + '/api'
  : 'http://localhost:8080/api';

var TOKEN_KEY = 'ss_token';
var USER_KEY = 'ss_user';

/* ============ Core ============ */
async function req(path, opts){
  opts = opts || {};
  var headers = Object.assign({
    'Content-Type': 'application/json'
  }, opts.headers || {});

  var token = localStorage.getItem(TOKEN_KEY);
  if(token) headers['Authorization'] = 'Bearer ' + token;

  var res;
  try{
    res = await fetch(API_BASE + path, {
      method: opts.method || 'GET',
      headers: headers,
      body: opts.body ? JSON.stringify(opts.body) : undefined
    });
  }catch(e){
    return { ok:false, error:'تعذّر الاتصال بالسيرفر' };
  }

  var data = null;
  try{ data = await res.json(); }catch(e){ data = null; }

  if(!res.ok){
    return { ok:false, error: (data && data.error) || ('خطأ ' + res.status) };
  }
  return { ok:true, data: data };
}

/* ============ Auth ============ */
async function register(name, email, password){
  var r = await req('/auth/register', {
    method:'POST',
    body:{ name:name, email:email, password:password }
  });
  if(r.ok && r.data && r.data.token){
    localStorage.setItem(TOKEN_KEY, r.data.token);
    localStorage.setItem(USER_KEY, JSON.stringify(r.data.user));
  }
  return r;
}

async function login(email, password){
  var r = await req('/auth/login', {
    method:'POST',
    body:{ email:email, password:password }
  });
  if(r.ok && r.data && r.data.token){
    localStorage.setItem(TOKEN_KEY, r.data.token);
    localStorage.setItem(USER_KEY, JSON.stringify(r.data.user));
  }
  return r;
}

function logout(){
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function currentUser(){
  try{ return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); }
  catch(e){ return null; }
}

function isLoggedIn(){ return !!localStorage.getItem(TOKEN_KEY); }

async function me(){
  return await req('/auth/me');
}

/* ============ Content ============ */
async function getContent(){
  var r = await req('/content');
  return r.ok ? r.data : null;
}

async function getDesign(){
  var r = await req('/design');
  return r.ok ? r.data : null;
}

/* ============ Scans ============ */
async function saveScan(type, target, status, details){
  return await req('/scans', {
    method:'POST',
    body:{ type:type, target:target, status:status, details:details || '' }
  });
}

async function myScans(){
  var r = await req('/scans');
  return r.ok ? r.data : [];
}

/* ============ Messages ============ */
async function sendMessage(name, email, subject, message){
  return await req('/messages', {
    method:'POST',
    body:{ name:name, email:email, subject:subject, message:message }
  });
}

/* ============ Admin ============ */
async function adminStats(){ var r=await req('/admin/stats'); return r.ok?r.data:null; }
async function adminUsers(){ var r=await req('/admin/users'); return r.ok?r.data:[]; }
async function adminScans(){ var r=await req('/admin/scans'); return r.ok?r.data:[]; }
async function adminMessages(){ var r=await req('/admin/messages'); return r.ok?r.data:[]; }
async function adminClearScans(){ return await req('/admin/scans/clear',{method:'DELETE'}); }
async function adminClearMessages(){ return await req('/admin/messages/clear',{method:'DELETE'}); }
async function adminDelUser(id){ return await req('/admin/users/'+id,{method:'DELETE'}); }
async function adminBanUser(id){ return await req('/admin/users/'+id+'/ban',{method:'POST'}); }

async function adminUpdateContent(obj){
  return await req('/admin/content',{method:'POST', body:obj});
}
async function adminUpdateDesign(obj){
  return await req('/admin/design',{method:'POST', body:obj});
}
async function adminChangePassword(oldP, newP){
  return await req('/admin/change-password',{method:'POST', body:{old:oldP,new:newP}});
}

/* ============ Upload ============ */
async function uploadImage(file){
  var token = localStorage.getItem(TOKEN_KEY);
  var fd = new FormData();
  fd.append('file', file);
  try{
    var res = await fetch(API_BASE + '/admin/upload', {
      method:'POST',
      headers: token ? {'Authorization':'Bearer '+token} : {},
      body: fd
    });
    var data = await res.json();
    if(!res.ok) return { ok:false, error:data.error || 'فشل الرفع' };
    return { ok:true, data: data };
  }catch(e){
    return { ok:false, error:'تعذّر الاتصال' };
  }
}

/* ============ Export ============ */
window.SS = {
  register: register,
  login: login,
  logout: logout,
  currentUser: currentUser,
  isLoggedIn: isLoggedIn,
  me: me,
  getContent: getContent,
  getDesign: getDesign,
  saveScan: saveScan,
  myScans: myScans,
  sendMessage: sendMessage,
  adminStats: adminStats,
  adminUsers: adminUsers,
  adminScans: adminScans,
  adminMessages: adminMessages,
  adminClearScans: adminClearScans,
  adminClearMessages: adminClearMessages,
  adminDelUser: adminDelUser,
  adminBanUser: adminBanUser,
  adminUpdateContent: adminUpdateContent,
  adminUpdateDesign: adminUpdateDesign,
  adminChangePassword: adminChangePassword,
  uploadImage: uploadImage
};
})();
