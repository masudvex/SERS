// ============ SIDE MENU ============
(function(){
  const openMenu=document.getElementById("openMenu"),closeMenu=document.getElementById("closeMenu"),
        sideMenu=document.getElementById("sideMenu"),menuOverlay=document.getElementById("menuOverlay");
  if(!openMenu)return;
  function openSide(){sideMenu.classList.add("active");menuOverlay.classList.add("active");document.body.style.overflow="hidden";}
  function closeSide(){sideMenu.classList.remove("active");menuOverlay.classList.remove("active");document.body.style.overflow="";}
  openMenu.addEventListener("click",openSide);
  closeMenu.addEventListener("click",closeSide);
  menuOverlay.addEventListener("click",closeSide);
  sideMenu.querySelectorAll("a").forEach(a=>a.addEventListener("click",closeSide));
})();

// ============ HOME HERO: ⌣ / ︵ boat-shaped mask with a scrolling filmstrip ============
(function(){
  const mask=document.getElementById('arcMask');
  const strip=document.getElementById('arcStrip');
  if(!mask||!strip)return;

  const dataEl=document.getElementById('heroImagesData');
  let POOL=[];
  try{POOL=JSON.parse(dataEl.textContent);}catch(e){}
  if(!POOL.length)return;

  // Geometry scales continuously with the actual viewport width instead of a few fixed
  // breakpoints, so it fits any device smoothly — small phones, large phones, tablets in
  // either orientation, laptops and wide desktop monitors alike.
  // bandH = big square tile size at the ends. topDip/bottomRise are always kept IDENTICAL
  // so the ⌣ on top and the ︵ on the bottom are exact mirrors of each other.
  // The admin setting "hero_strip_scale" (percent) enlarges the photos in both width and height.
  const SCALE=Math.min(3,Math.max(0.5,(parseInt(mask.dataset.scale,10)||100)/100));
  function geometryFor(w){
    const clamp=(min,val,max)=>Math.min(max,Math.max(min,val));
    const bandH=clamp(68*SCALE,w*0.145*SCALE,232*SCALE);
    const gap=clamp(6,w*0.010,16);
    const topPad=clamp(7,bandH*0.07,18);
    const bottomPad=clamp(5,bandH*0.045,11);
    const curve=clamp(16,bandH*0.40,92*SCALE); // shared by top and bottom — always symmetric
    return {bandH,gap,topPad,bottomPad,topDip:curve,bottomRise:curve};
  }

  // build enough tiles to comfortably fill the widest screen twice over (for a seamless loop)
  function buildTiles(){
    strip.innerHTML='';
    // Two identical halves (the CSS animation slides by exactly 50%), each long enough to fill the widest screen.
    const perHalf=POOL.length*Math.ceil((Math.ceil(Math.max(window.innerWidth,1920)/(60*SCALE))+2)/POOL.length);
    const need=perHalf*2;
    for(let i=0;i<need;i++){
      const tile=document.createElement('div');
      tile.className='arc-tile';
      const img=document.createElement('img');
      img.src=POOL[i%POOL.length].src;
      img.alt=POOL[i%POOL.length].alt||'';
      tile.appendChild(img);
      strip.appendChild(tile);
    }
  }

  function layout(){
    const w=mask.offsetWidth;
    const g=geometryFor(w);
    const maskHeight=g.topPad+g.bandH+g.bottomPad;
    mask.style.height=maskHeight+'px';

    // big square tiles — size is the band height itself
    Array.from(strip.children).forEach(tile=>{
      tile.style.width=g.bandH+'px';
      tile.style.height=g.bandH+'px';
    });
    strip.style.gap=g.gap+'px';
    strip.style.paddingRight=g.gap+'px'; // keeps the 50% loop point exact, so there is no jump at the seam
    strip.style.height=g.bandH+'px';
    strip.style.top=g.topPad+'px';

    const topEnd=g.topPad;
    const bottomEnd=g.topPad+g.bandH;
    // top dips DOWN toward the centre (⌣); bottom rises UP toward the centre (︵) —
    // the shape pinches thinner in the middle, full big squares at both ends.
    const d=`M 0,${topEnd} Q ${w/2},${topEnd+g.topDip} ${w},${topEnd} `+
            `L ${w},${bottomEnd} Q ${w/2},${bottomEnd-g.bottomRise} 0,${bottomEnd} Z`;
    mask.style.clipPath=`path('${d}')`;
    mask.style['-webkit-clip-path']=`path('${d}')`;
  }

  buildTiles();
  layout();
  window.addEventListener('resize',layout);
  window.addEventListener('load',layout);
  window.addEventListener('orientationchange',()=>setTimeout(layout,50));
})();

// ============ PROGRAMS SLIDER (home) ============
(function(){
  const track=document.getElementById('programsTrack');
  if(!track)return;
  const originals=Array.from(track.children);
  originals.forEach(c=>track.appendChild(c.cloneNode(true)));
  let index=0,timer;
  function step(){const c=track.children[0];const gap=parseFloat(getComputedStyle(track).gap)||0;return c.getBoundingClientRect().width+gap;}
  function move(anim=true){track.style.transition=anim?"transform .7s cubic-bezier(.22,.61,.36,1)":"none";track.style.transform=`translate3d(${-index*step()}px,0,0)`;}
  function next(){index++;move(true);if(index===originals.length){setTimeout(()=>{index=0;move(false);},700);}}
  function prev(){if(index===0){index=originals.length;move(false);requestAnimationFrame(()=>requestAnimationFrame(()=>{index--;move(true);}));}else{index--;move(true);}}
  function start(){clearInterval(timer);timer=setInterval(next,3200);}
  document.getElementById('progNext').addEventListener('click',()=>{next();start();});
  document.getElementById('progPrev').addEventListener('click',()=>{prev();start();});
  track.parentElement.addEventListener('mouseenter',()=>clearInterval(timer));
  track.parentElement.addEventListener('mouseleave',start);
  window.addEventListener('resize',()=>move(false));
  move(false);start();
})();

// ============ ANIMATED COUNTERS ============
(function(){
  const els=document.querySelectorAll('[data-count]');
  if(!els.length)return;
  let done=false;
  function animate(){
    els.forEach(el=>{
      const target=parseInt(el.dataset.count,10);
      const start=performance.now();const dur=1400;
      function tick(now){
        const p=Math.min((now-start)/dur,1);const eased=1-Math.pow(1-p,3);
        el.textContent=Math.floor(eased*target).toLocaleString();
        if(p<1)requestAnimationFrame(tick);else el.textContent=target.toLocaleString()+(el.dataset.suffix||'');
      }
      requestAnimationFrame(tick);
    });
  }
  const ribbon=document.querySelector('.ribbon');
  const io=new IntersectionObserver(entries=>{entries.forEach(e=>{if(e.isIntersecting&&!done){done=true;animate();io.disconnect();}});},{threshold:.4});
  if(ribbon)io.observe(ribbon);
})();

const I18N=(window.GB&&window.GB.i18n)||{trees:'',treesN:'{n}',locating:'',pinned:'',geoFail:'',geoNone:''};

// ============ GOOGLE MAP (settings come from Site settings; markers from the Django JSON API) ============
(function(){
  const el=document.getElementById('bangladeshMap');
  const cfgEl=document.getElementById('mapConfig');
  if(!el||!cfgEl)return;
  let cfg={};try{cfg=JSON.parse(cfgEl.textContent);}catch(e){return;}

  // Simple keyless Google Maps embed, used until an API key is set (or if Google rejects the key).
  function showEmbed(){
    if(el.dataset.mode==='embed')return;
    el.dataset.mode='embed';
    el.innerHTML='';
    const f=document.createElement('iframe');
    f.src='https://www.google.com/maps?q='+encodeURIComponent(cfg.query||'')+'&z='+(cfg.zoom||7)+'&output=embed';
    f.title=el.getAttribute('aria-label')||'';
    f.loading='lazy';f.referrerPolicy='no-referrer-when-downgrade';f.allowFullscreen=true;
    f.style.cssText='border:0;width:100%;height:100%;border-radius:10px;display:block;';
    el.appendChild(f);
  }
  if(!cfg.key){showEmbed();return;}

  // Google calls this if the key is missing, restricted to another site, or billing is off.
  window.gm_authFailure=showEmbed;

  function infoNode(title,line){
    const box=document.createElement('div');box.style.cssText='font:14px/1.45 Inter,Arial,sans-serif;color:#16271d;max-width:220px;';
    const h=document.createElement('strong');h.style.color='#123d2a';h.textContent=title;box.appendChild(h);
    if(line){box.appendChild(document.createElement('br'));box.appendChild(document.createTextNode(line));}
    return box;
  }

  window.gbInitMap=async function(){
    try{
      const {Map,InfoWindow}=await google.maps.importLibrary('maps');
      const {AdvancedMarkerElement,PinElement}=await google.maps.importLibrary('marker');
      const map=new Map(el,{center:{lat:cfg.lat,lng:cfg.lng},zoom:cfg.zoom,mapId:cfg.mapId,gestureHandling:'cooperative',
                            mapTypeControl:false,streetViewControl:false,fullscreenControl:true});
      const info=new InfoWindow();
      const add=(pos,title,line,pin,z)=>{
        const m=new AdvancedMarkerElement({map,position:pos,title,content:pin.element,zIndex:z});
        m.addListener('gmp-click',()=>{info.setContent(infoNode(title,line));info.open({map,anchor:m});});
      };
      const data=await fetch(cfg.mapUrl).then(r=>r.json());
      data.divisions.forEach(d=>add({lat:d.lat,lng:d.lng},d.name,
        d.trees.toLocaleString()+' '+I18N.trees+(d.note?' · '+d.note:''),
        new PinElement({background:'#1f5b3f',borderColor:'#ffffff',glyphColor:'#ffffff'}),2));
      data.plantings.forEach(p=>add({lat:p.lat,lng:p.lng},p.place,
        I18N.treesN.replace('{n}',p.trees)+(p.species?' · '+p.species:''),
        new PinElement({background:'#c38a34',borderColor:'#ffffff',glyphColor:'#ffffff',scale:.7}),1));
    }catch(err){showEmbed();}
  };

  const s=document.createElement('script');
  s.async=true;
  s.src='https://maps.googleapis.com/maps/api/js?key='+encodeURIComponent(cfg.key)+'&v=weekly&loading=async&callback=gbInitMap';
  s.onerror=showEmbed;
  document.head.appendChild(s);
})();

// ============ GALLERY: lightbox (filtering is done server-side) ============
(function(){
  const grid=document.querySelector('.gallery-grid');
  const lightbox=document.getElementById('lightbox');
  if(!grid||!lightbox)return;
  const lbImg=document.getElementById('lightboxImg');
  const open=it=>{lbImg.src=it.querySelector('img').src;lightbox.classList.add('active');};
  grid.querySelectorAll('.g-item').forEach(it=>{
    it.addEventListener('click',()=>open(it));
    it.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open(it);}});
  });
  const close=()=>lightbox.classList.remove('active');
  document.getElementById('lightboxClose').addEventListener('click',close);
  lightbox.addEventListener('click',e=>{if(e.target===lightbox)close();});
  document.addEventListener('keydown',e=>{if(e.key==='Escape')close();});
})();

// ============ PHOTO UPLOAD PREVIEW (register page) ============
(function(){
  const box=document.getElementById('uploadBox');
  if(!box)return;
  const input=document.getElementById('photoInput');
  const thumb=document.getElementById('thumb');
  function showFile(file){
    if(!file)return;
    const reader=new FileReader();
    reader.onload=e=>{thumb.innerHTML=`<img src="${e.target.result}" alt="Preview">`;};
    reader.readAsDataURL(file);
  }
  input.addEventListener('change',()=>showFile(input.files[0]));
  ['dragover','dragenter'].forEach(ev=>box.addEventListener(ev,e=>{e.preventDefault();box.classList.add('drag');}));
  ['dragleave','drop'].forEach(ev=>box.addEventListener(ev,e=>{e.preventDefault();box.classList.remove('drag');}));
  box.addEventListener('drop',e=>{const file=e.dataTransfer.files[0];if(file){input.files=e.dataTransfer.files;showFile(file);}});
})();

// ============ DONATE: live total ============
(function(){
  const form=document.getElementById('donateForm');
  if(!form)return;
  const price=parseInt(form.dataset.price,10)||0;
  const input=form.querySelector('input[name=saplings]');
  const out=document.getElementById('donateTotal');
  const update=()=>{const n=Math.max(0,parseInt(input.value,10)||0);out.textContent=(n*price).toLocaleString();};
  input.addEventListener('input',update);update();
})();

// ============ DASHBOARD: pin current location ============
(function(){
  const btn=document.getElementById('geoBtn');
  if(!btn)return;
  const status=document.getElementById('geoStatus');
  btn.addEventListener('click',()=>{
    if(!navigator.geolocation){status.textContent=I18N.geoNone;return;}
    status.textContent=I18N.locating;
    navigator.geolocation.getCurrentPosition(pos=>{
      document.getElementById('id_latitude').value=pos.coords.latitude.toFixed(6);
      document.getElementById('id_longitude').value=pos.coords.longitude.toFixed(6);
      status.textContent=I18N.pinned;
    },()=>{status.textContent=I18N.geoFail;},{timeout:10000});
  });
})();
