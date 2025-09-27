// Load translations
let translations = {};
let currentLang = 'en';

fetch('translations.json')
  .then(res => res.json())
  .then(data => {
    translations = data;
    applyTranslations(currentLang);
  });

// Apply translations to all elements with data-i18n
function applyTranslations(lang) {
  currentLang = lang;
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if(translations[lang] && translations[lang][key]){
      if(el.tagName.toLowerCase() === 'input' && el.hasAttribute('placeholder')){
        el.placeholder = translations[lang][key];
      } else {
        el.textContent = translations[lang][key];
      }
    }
  });

  // Update document title
  if(translations[lang] && translations[lang]['title']){
    document.title = translations[lang]['title'];
  }
}

// Change language when dropdown changes
document.getElementById('lang').addEventListener('change', (e)=>{
  applyTranslations(e.target.value);
});

// Local demo storage (still used for quick export)
const db = { mood: [], messages: [] };

const chatWindow = document.getElementById('chatWindow');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const startBtn = document.getElementById('startBtn');
const exportBtns = document.querySelectorAll('#exportBtn, #exportBtnTop');

function appendBubble(text, who='assistant'){
  const d = document.createElement('div');
  d.className = 'bubble '+who;
  d.textContent = text;
  chatWindow.appendChild(d);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  db.messages.push({who,text,time:new Date().toISOString()});
}

// send message (connected with backend)
sendBtn.addEventListener('click', async ()=>{
  const t = chatInput.value.trim();
  if(!t) return;
  appendBubble(t,'user');
  chatInput.value='';

  const lang = document.getElementById('lang').value;
  const age = document.getElementById('age').value;
  const consent = document.getElementById('consent').checked;

  // ensure user_id exists (register once)
  if(!window.userId){
    const res = await fetch('/api/register', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({language: lang, age_group: age, consent})
    });
    const data = await res.json();
    window.userId = data.user_id;
  }

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({user_id: window.userId, text: t, language: lang})
    });
    const data = await res.json();
    appendBubble(data.reply, 'assistant');
  } catch (err) {
    appendBubble('⚠️ Connection error — please try again later.', 'assistant');
  }
});

// start session
startBtn.addEventListener('click', ()=>{
  appendBubble('Session started — how are you feeling right now?', 'assistant');
});

// mood modal
document.getElementById('moodBtn').addEventListener('click', openMood);
document.getElementById('moodQuick').addEventListener('click', openMood);
function openMood(){
  const tpl = document.getElementById('moodTemplate').content.cloneNode(true);
  showModal(tpl);
}

// breath modal
document.getElementById('breathBtn').addEventListener('click', openBreath);
document.getElementById('breathQuick').addEventListener('click', openBreath);
function openBreath(){
  const tpl = document.getElementById('breathTemplate').content.cloneNode(true);
  showModal(tpl);
}

// cbt modal
document.getElementById('cbtBtn').addEventListener('click', openCbt);
function openCbt(){
  const tpl = document.getElementById('cbtTemplate').content.cloneNode(true);
  showModal(tpl);
}

function showModal(fragment){
  const overlay = document.createElement('div');
  overlay.style.position='fixed';overlay.style.left=0;overlay.style.top=0;overlay.style.right=0;overlay.style.bottom=0;
  overlay.style.background='rgba(2,6,23,0.45)';
  overlay.style.display='grid';overlay.style.placeItems='center';overlay.style.zIndex=9999;
  const modalWrap = document.createElement('div');modalWrap.style.width='min(96%,720px)';modalWrap.appendChild(fragment);
  overlay.appendChild(modalWrap);
  document.body.appendChild(overlay);

  // close/save wiring
  overlay.querySelectorAll('.close').forEach(btn=>btn.addEventListener('click', ()=>overlay.remove()));
  overlay.querySelectorAll('.save').forEach(btn=>{
    btn.addEventListener('click', async ()=>{
      const rating = overlay.querySelector('#moodRating')?.value;
      const note = overlay.querySelector('#moodNote')?.value||'';
      if(rating){
        db.mood.push({rating: Number(rating), note, time: new Date().toISOString()});
        appendBubble('Mood saved — thank you for checking in.', 'assistant');

        // also save to backend if user registered
        if(window.userId){
          await fetch('/api/mood', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({user_id: window.userId, rating: Number(rating), note})
          });
        }
      }
      overlay.remove();
    });
  });

  // mood rating preview
  overlay.querySelectorAll('#moodRating').forEach(r=>r.addEventListener('input', (e)=>{
    const p = overlay.querySelector('#moodPreview'); if(p) { p.textContent = e.target.value; }
  }));

  // CBT steps
  overlay.querySelectorAll('.next').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const content = overlay.querySelector('#cbtContent');
      if(content){
        if(!content.dataset.step) content.dataset.step='1';
        let step = Number(content.dataset.step);
        step++;
        content.dataset.step = step;
        if(step===2) content.innerHTML = '<p class="muted">Step 2: What evidence supports this thought?</p>';
        else if(step===3) content.innerHTML = '<p class="muted">Step 3: Is there a kinder, more balanced thought?</p>';
        else { appendBubble('Great job — small steps matter. Want to save this as a note?', 'assistant'); overlay.remove(); }
      }
    });
  });
}

// export data
exportBtns.forEach(b=>b.addEventListener('click', ()=>{
  const payload = {
    meta:{
      lang:document.getElementById('lang').value,
      age:document.getElementById('age').value,
      consent:document.getElementById('consent').checked
    },
    db
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], {type:'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href=url; a.download='mh-demo-export.json'; a.click(); URL.revokeObjectURL(url);
}));

// enter to send
chatInput.addEventListener('keydown', (e)=>{ if(e.key==='Enter'){ sendBtn.click(); } });

// small animation
setTimeout(()=>{ document.querySelector('.logo').animate([{transform:'scale(.95)'},{transform:'scale(1)'}],{duration:800,fill:'forwards'}) },400);
