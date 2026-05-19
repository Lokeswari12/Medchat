/* CancerScreen AI – app.js */

/* ── Counter Animation ── */
function animateCounter(el){
  const target=parseInt(el.dataset.target)||0;
  if(target===0){el.textContent='0';return}
  const duration=1600,step=16,steps=duration/step;
  let current=0;const inc=target/steps;
  const t=setInterval(()=>{
    current+=inc;
    if(current>=target){el.textContent=target;clearInterval(t)}
    else el.textContent=Math.floor(current);
  },step);
}
const counters=document.querySelectorAll('[data-target],.counter');
if(counters.length){
  const obs=new IntersectionObserver(entries=>{
    entries.forEach(e=>{if(e.isIntersecting){animateCounter(e.target);obs.unobserve(e.target)}});
  },{threshold:0.5});
  counters.forEach(c=>obs.observe(c));
}

/* ── Mobile Nav ── */
document.getElementById('navToggle')?.addEventListener('click',()=>{
  const links=document.querySelector('.nav-links');
  const cta=document.querySelector('.nav-cta');
  if(links){
    const open=links.style.display==='flex';
    links.style.cssText=open?'':'display:flex;flex-direction:column;position:absolute;top:68px;left:0;right:0;background:#fff;border-bottom:1px solid #e2e8f0;padding:12px 16px;gap:4px;z-index:999;box-shadow:0 8px 24px rgba(15,23,42,.08)';
    if(cta)cta.style.display=open?'':'none';
  }
});

/* ── Auto-dismiss flash ── */
document.querySelectorAll('.flash').forEach(f=>{
  setTimeout(()=>{
    f.style.transition='opacity .4s,transform .4s';
    f.style.opacity='0';f.style.transform='translateX(120%)';
    setTimeout(()=>f.remove(),400);
  },4000);
});

/* ── Confidence bar animate on load ── */
window.addEventListener('load',()=>{
  document.querySelectorAll('.conf-fill').forEach(b=>{
    const w=b.style.width;b.style.width='0';
    setTimeout(()=>{b.style.transition='width 1s ease';b.style.width=w},200);
  });
});

/* ══════════════════════════════════════
   PWA — Offline / Online Detection
══════════════════════════════════════ */
function showOfflineBanner(){
  let b=document.getElementById('offlineBanner');
  if(!b){
    b=document.createElement('div');
    b.id='offlineBanner';
    b.className='offline-banner';
    b.innerHTML='<i class="fas fa-wifi-slash"></i> You\'re offline — cached pages still work, AI features need internet <button onclick="this.parentElement.remove()">✕</button>';
    document.body.prepend(b);
  }
}
function hideOfflineBanner(){
  const b=document.getElementById('offlineBanner');
  if(b){
    b.classList.add('online-flash');
    b.innerHTML='<i class="fas fa-wifi"></i> Back online! <button onclick="this.parentElement.remove()">✕</button>';
    setTimeout(()=>b.remove(),3000);
  }
}
if(!navigator.onLine) showOfflineBanner();
window.addEventListener('offline', showOfflineBanner);
window.addEventListener('online',  hideOfflineBanner);

/* ── Intercept offline API responses and show UI message ── */
const _origFetch = window.fetch;
window.fetch = async function(...args){
  try{
    const res = await _origFetch(...args);
    const url = typeof args[0]==='string'?args[0]:(args[0]?.url||'');
    // If API returned an offline JSON, show a toast
    if(url.includes('/api/') && res.headers.get('Content-Type')?.includes('json')){
      const clone = res.clone();
      clone.json().then(d=>{
        if(d.offline) showToast('You\'re offline — AI features require internet','warning');
      }).catch(()=>{});
    }
    return res;
  }catch(err){
    showOfflineBanner();
    throw err;
  }
};

/* ── Toast notification ── */
function showToast(msg, type='info'){
  const t=document.createElement('div');
  t.className='app-toast app-toast-'+type;
  t.innerHTML=`<i class="fas fa-${type==='warning'?'exclamation-triangle':'info-circle'}"></i> ${msg}`;
  document.body.appendChild(t);
  requestAnimationFrame(()=>t.classList.add('show'));
  setTimeout(()=>{t.classList.remove('show');setTimeout(()=>t.remove(),300)},4000);
}
window.showToast = showToast;

/* ══════════════════════════════════════
   PWA — Install Prompt
══════════════════════════════════════ */
let _deferredInstall = null;

window.addEventListener('beforeinstallprompt', e => {
  e.preventDefault();
  _deferredInstall = e;
  const btn = document.getElementById('installBtn');
  if(btn) btn.style.display = 'flex';
});

window.addEventListener('appinstalled', () => {
  _deferredInstall = null;
  const btn = document.getElementById('installBtn');
  if(btn) btn.style.display = 'none';
  showToast('CancerScreen AI installed successfully!', 'info');
});

window.installPWA = async function(){
  if(!_deferredInstall) return;
  _deferredInstall.prompt();
  const { outcome } = await _deferredInstall.userChoice;
  if(outcome === 'accepted') _deferredInstall = null;
};

/* ── Check if already installed (standalone mode) ── */
if(window.matchMedia('(display-mode: standalone)').matches ||
   window.navigator.standalone === true){
  // Running as installed PWA — hide install button
  document.addEventListener('DOMContentLoaded',()=>{
    const btn=document.getElementById('installBtn');
    if(btn) btn.style.display='none';
  });
}

/* ── SW update notification ── */
if('serviceWorker' in navigator){
  navigator.serviceWorker.addEventListener('controllerchange',()=>{
    showToast('App updated — reload for the latest version','info');
  });
}
