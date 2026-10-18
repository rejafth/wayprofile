(function(){
var grid=document.getElementById('grid'),tabs=document.getElementById('tabs'),more=document.getElementById('more');
if(grid&&tabs&&more){
var cards=[].slice.call(grid.children),cur='Semua',open=false,feat=cards.filter(function(c){return c.dataset.feat==='1'}).length;
function apply(){
cards.forEach(function(c){var show=cur==='Semua'?(open||feat===0||c.dataset.feat==='1'):c.dataset.cat===cur;c.hidden=!show});
more.textContent='';
if(cur==='Semua'&&feat>0&&feat<cards.length){var b=document.createElement('button');b.type='button';b.className='btn pri';b.textContent=open?grid.dataset.less:grid.dataset.more;b.onclick=function(){open=!open;apply()};more.appendChild(b)}}
[].forEach.call(tabs.children,function(t){t.onclick=function(){cur=t.dataset.cat;[].forEach.call(tabs.children,function(x){x.setAttribute('aria-pressed',x===t?'true':'false')});apply()}});
apply()}
function sc(t,c,l){
var o='<svg viewBox="0 0 320 180" role="img" aria-label="Ilustrasi '+l+'">';
if(t==="rack"){o+='<rect width="320" height="180" fill="#14233D"/><rect x="98" y="14" width="124" height="130" rx="5" fill="#22345A" stroke="#4a6490" stroke-width="2"/>';for(var i=0;i<6;i++){o+='<rect x="106" y="'+(22+i*20)+'" width="108" height="14" rx="2" fill="#0d1a30"/><circle cx="'+(200)+'" cy="'+(29+i*20)+'" r="2.5" fill="#47B2E4"/>';for(var j=0;j<8;j++)o+='<rect x="'+(112+j*10)+'" y="'+(26+i*20)+'" width="7" height="7" fill="#5b749c"/>'}
o+='<path d="M120 144c-10 20-50 10-70 30M150 144c0 22 20 22 20 34M190 144c20 20 60 6 80 34" fill="none" stroke="#47B2E4" stroke-width="3"/><path d="M135 144c-6 24-30 20-40 34M205 144c10 20 40 20 55 34" fill="none" stroke="#E8B923" stroke-width="3"/>'}
else if(t==="browser"){o+='<rect width="320" height="180" fill="#DCE8F4"/><rect x="24" y="16" width="272" height="150" rx="8" fill="#fff"/><rect x="24" y="16" width="272" height="20" rx="8" fill="#37517E"/><circle cx="38" cy="26" r="3" fill="#fff"/><circle cx="48" cy="26" r="3" fill="#fff"/><circle cx="58" cy="26" r="3" fill="#fff"/><rect x="36" y="46" width="248" height="48" rx="5" fill="'+c+'"/><rect x="48" y="58" width="110" height="8" rx="3" fill="#fff"/><rect x="48" y="72" width="70" height="6" rx="3" fill="#ffffffaa"/>';for(var k=0;k<3;k++)o+='<rect x="'+(36+k*84)+'" y="106" width="76" height="48" rx="5" fill="#E8F0FA"/><rect x="'+(44+k*84)+'" y="114" width="40" height="6" rx="3" fill="'+c+'"/><rect x="'+(44+k*84)+'" y="126" width="58" height="5" rx="2" fill="#b7c7dc"/>'}
else{o+='<rect width="320" height="180" fill="#14233D"/><rect x="16" y="16" width="288" height="148" rx="8" fill="#1d2f52"/>';for(var m=0;m<4;m++)o+='<rect x="'+(28+m*68)+'" y="28" width="58" height="26" rx="4" fill="#27395A"/><rect x="'+(34+m*68)+'" y="36" width="30" height="5" rx="2" fill="'+c+'"/><rect x="'+(34+m*68)+'" y="44" width="20" height="5" rx="2" fill="#9DB0C8"/>';
var h=[40,62,48,80,66,92,74,100];for(var n=0;n<8;n++)o+='<rect x="'+(34+n*34)+'" y="'+(156-h[n])+'" width="22" height="'+h[n]+'" rx="3" fill="'+(n%2?c:"#47B2E4")+'"/>'}
return o+'</svg>'}
[].forEach.call(document.querySelectorAll('.art'),function(a){
var c=/^#[0-9a-f]{6}$/i.test(a.dataset.color||'')?a.dataset.color:'#19a1c8',l=(a.dataset.label||'').replace(/[<>"&]/g,'');
a.innerHTML=sc(a.dataset.scene||'dash',c,l)});
})();
