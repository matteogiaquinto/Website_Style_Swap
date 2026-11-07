/* Original cursor-led progressive reveal. No code from swarm-cursors is included. */
(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const candidates = [...document.body.querySelectorAll('*')].filter(el => {
    if (el.closest('script,style,svg,video,audio,canvas') || el.matches('script,style,link,meta,source,br,svg,canvas')) return el.matches('svg,video,canvas') && !!el.getBoundingClientRect().width;
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility === 'visible' && Number(s.opacity) > 0;
  }).slice(0, 1800);
  if (!candidates.length) return;
  const style = document.createElement('style');
  style.textContent = '[data-restyle-building="pending"], [data-restyle-building="working"] { visibility: hidden !important; } [data-restyle-building="revealed"] { visibility: visible !important; }';
  document.head.appendChild(style);
  candidates.forEach(el => el.setAttribute('data-restyle-building', 'pending'));
  const canvas = document.createElement('canvas');
  canvas.setAttribute('aria-hidden', 'true');
  for (const [name, value] of Object.entries({position:'fixed', inset:'0', width:'100vw', height:'100vh', 'z-index':'2147483647', 'pointer-events':'none', display:'block', margin:'0', padding:'0', border:'0', background:'transparent'})) canvas.style.setProperty(name, value, 'important');
  document.body.appendChild(canvas);
  const ctx = canvas.getContext('2d');
  function revealAll(){
    candidates.forEach(el => el.removeAttribute('data-restyle-building'));
    style.remove();canvas.remove();window.removeEventListener('scroll',wake);window.removeEventListener('resize',resize);window.removeEventListener('keydown',onKey);
  }
  if (!ctx) { revealAll(); return; }
  const colors = ['#9357ee','#f15a83','#27a4e5','#eb9240','#34af86','#d65dd5'];
  const labels = ['Design','Layout','Text','Images','Style','Details'];
  const agents = colors.map((color,i)=>({color,label:labels[i],x:innerWidth*(.15+i*.12),y:Math.min(innerHeight*.45,200+i*25),element:null,start:0,fromX:0,fromY:0}));
  let width=innerWidth,height=innerHeight,animation=0,lastActivity=performance.now(),lastFrame=0;
  function resize(){width=innerWidth;height=innerHeight;const dpr=Math.min(devicePixelRatio||1,2);canvas.width=Math.ceil(width*dpr);canvas.height=Math.ceil(height*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);wake();}
  function onKey(e){if(e.key==='Escape')revealAll();}
  function visible(el){const r=el.getBoundingClientRect();return r.bottom>0 && r.top<height && r.right>0 && r.left<width;}
  function next(){return candidates.find(el=>el.getAttribute('data-restyle-building')==='pending' && visible(el));}
  function pointer(a,opacity){
    ctx.save();ctx.translate(a.x,a.y);ctx.globalAlpha=opacity;ctx.shadowColor='rgba(0,0,0,.18)';ctx.shadowBlur=4;ctx.shadowOffsetY=2;
    ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(4,20);ctx.lineTo(8,15);ctx.lineTo(13,23);ctx.lineTo(17,21);ctx.lineTo(12,13);ctx.lineTo(20,12);ctx.closePath();ctx.fillStyle=a.color;ctx.fill();ctx.strokeStyle='#fff';ctx.lineWidth=1.4;ctx.stroke();
    ctx.shadowColor='transparent';ctx.font='600 11px system-ui, sans-serif';const labelWidth=ctx.measureText(a.label).width+14;
    ctx.fillStyle=a.color;ctx.beginPath();ctx.roundRect(15,18,labelWidth,20,4);ctx.fill();ctx.fillStyle='#fff';ctx.textBaseline='middle';ctx.fillText(a.label,22,28);ctx.restore();
  }
  function frame(now){
    animation=0;
    try {
      ctx.clearRect(0,0,width,height);
      for(const a of agents){
        if(!a.element){const el=next();if(el){a.element=el;a.start=now;a.fromX=a.x;a.fromY=a.y;el.setAttribute('data-restyle-building','working');lastActivity=now;}}
        if(a.element){
          const r=a.element.getBoundingClientRect(),t=Math.min(1,(now-a.start)/550), eased=1-Math.pow(1-t,3);
          const tx=Math.max(4,Math.min(width-35,r.left+Math.min(r.width*.7,60))),ty=Math.max(4,Math.min(height-35,r.top+Math.min(r.height*.7,25)));
          a.x=a.fromX+(tx-a.fromX)*eased;a.y=a.fromY+(ty-a.fromY)*eased;
          ctx.save();ctx.globalAlpha=.55;ctx.strokeStyle=a.color;ctx.lineWidth=1;ctx.setLineDash([4,4]);ctx.strokeRect(Math.max(0,r.left),Math.max(0,r.top),Math.min(r.width,width),Math.min(r.height,height));ctx.restore();
          if(t>=1){a.element.setAttribute('data-restyle-building','revealed');a.element=null;lastActivity=now;}
        }
        const opacity=now-lastActivity<1400?1:Math.max(0,1-(now-lastActivity-1400)/600);
        if(opacity>0)pointer(a,opacity);
      }
      lastFrame=now;
      if(agents.some(a=>a.element)||next()||now-lastActivity<2000) animation=requestAnimationFrame(frame);
      else ctx.clearRect(0,0,width,height);
    } catch (error) { revealAll(); }
  }
  function wake(){lastActivity=performance.now();if(!animation)animation=requestAnimationFrame(frame);}
  resize();window.addEventListener('resize',resize,{passive:true});window.addEventListener('scroll',wake,{passive:true});window.addEventListener('keydown',onKey);
  // A user can skip the effect at any time without changing the site.
  wake();
})();
