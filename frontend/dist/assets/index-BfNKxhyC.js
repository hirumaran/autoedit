(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const n of document.querySelectorAll('link[rel="modulepreload"]'))o(n);new MutationObserver(n=>{for(const r of n)if(r.type==="childList")for(const i of r.addedNodes)i.tagName==="LINK"&&i.rel==="modulepreload"&&o(i)}).observe(document,{childList:!0,subtree:!0});function s(n){const r={};return n.integrity&&(r.integrity=n.integrity),n.referrerPolicy&&(r.referrerPolicy=n.referrerPolicy),n.crossOrigin==="use-credentials"?r.credentials="include":n.crossOrigin==="anonymous"?r.credentials="omit":r.credentials="same-origin",r}function o(n){if(n.ep)return;n.ep=!0;const r=s(n);fetch(n.href,r)}})();/**
 * Anime.js - core - ESM
 * @version v4.4.1
 * @license MIT
 * @copyright 2026 - Julian Garnier
 */const We=typeof window<"u",Kt=We?window:null,St=We?document:null,F={OBJECT:0,ATTRIBUTE:1,CSS:2,TRANSFORM:3,CSS_VAR:4},L={NUMBER:0,UNIT:1,COLOR:2,COMPLEX:3},Ce={NONE:0,AUTO:1,FORCE:2},le={replace:0,none:1,blend:2},vs=Symbol(),Ct=Symbol(),$s=Symbol(),Jt=Symbol(),un=Symbol(),R=1e-11,is=1e12,pt=1e3,as=240,mt="",pn="var(",Us=(()=>{const e=new Map;return e.set("x","translateX"),e.set("y","translateY"),e.set("z","translateZ"),e})(),Yt=["perspective","translateX","translateY","translateZ","rotate","rotateX","rotateY","rotateZ","scale","scaleX","scaleY","scaleZ","skew","skewX","skewY"],mn=Yt.reduce((e,t)=>({...e,[t]:t+"("}),{}),Se=()=>{},fn=/\)\s*[-.\d]/,hn=/(^#([\da-f]{3}){1,2}$)|(^#([\da-f]{4}){1,2}$)/i,gn=/rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)/i,_n=/rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(-?\d+|-?\d*.\d+)\s*\)/i,yn=/hsl\(\s*(-?\d+|-?\d*.\d+)\s*,\s*(-?\d+|-?\d*.\d+)%\s*,\s*(-?\d+|-?\d*.\d+)%\s*\)/i,bn=/hsla\(\s*(-?\d+|-?\d*.\d+)\s*,\s*(-?\d+|-?\d*.\d+)%\s*,\s*(-?\d+|-?\d*.\d+)%\s*,\s*(-?\d+|-?\d*.\d+)\s*\)/i,xs=/[-+]?\d*\.?\d+(?:e[-+]?\d)?/gi,vn=/^([-+]?\d*\.?\d+(?:e[-+]?\d+)?)([a-z]+|%)$/i,xn=/([a-z])([A-Z])/g,Tn=/var\(\s*(--[\w-]+)(?:\s*,\s*([^)]+))?\s*\)/;/**
 * Anime.js - core - ESM
 * @version v4.4.1
 * @license MIT
 * @copyright 2026 - Julian Garnier
 */const Wt={id:null,keyframes:null,playbackEase:null,playbackRate:1,frameRate:as,loop:0,reversed:!1,alternate:!1,autoplay:!0,persist:!1,duration:pt,delay:0,loopDelay:0,ease:"out(2)",composition:le.replace,modifier:e=>e,onBegin:Se,onBeforeUpdate:Se,onUpdate:Se,onLoop:Se,onPause:Se,onComplete:Se,onRender:Se},En={root:St},ie={defaults:Wt,precision:4,timeScale:1,tickThreshold:200},Vs={version:"4.4.1",engine:null};We&&(Kt.AnimeJS||(Kt.AnimeJS=[]),Kt.AnimeJS.push(Vs));/**
 * Anime.js - core - ESM
 * @version v4.4.1
 * @license MIT
 * @copyright 2026 - Julian Garnier
 */const qs=e=>e.replace(xn,"$1-$2").toLowerCase(),He=(e,t)=>e.indexOf(t)===0,ft=Date.now,ht=Array.isArray,Qt=e=>e&&e.constructor===Object,Ln=e=>typeof e=="number"&&!isNaN(e),kt=e=>typeof e=="string",Nt=e=>typeof e=="function",$=e=>typeof e>"u",wt=e=>$(e)||e===null,Xs=e=>We&&e instanceof SVGElement,zs=e=>hn.test(e),Hs=e=>He(e,"rgb"),Ys=e=>He(e,"hsl"),wn=e=>zs(e)||(Hs(e)||Ys(e))&&(e[e.length-1]===")"||!fn.test(e)),Xt=e=>!ie.defaults.hasOwnProperty(e),In=["opacity","rotate","overflow","color"],Sn=(e,t)=>{if(In.includes(t))return!1;if(e.getAttribute(t)||t in e){if(t==="scale"){const s=e.parentNode;return s&&s.tagName==="filter"}return!0}},lt=Math.pow,Cn=Math.sqrt,kn=Math.sin,Nn=Math.cos,Bn=Math.floor,Rn=Math.asin,ds=Math.PI,Ts=Math.round,be=(e,t,s)=>e<t?t:e>s?s:e,z=(e,t)=>{if(t<0)return e;if(!t)return Ts(e);const s=10**t;return Ts(e*s)/s},Ze=(e,t,s)=>e+(t-e)*s,us=e=>e===1/0?is:e===-1/0?-is:e,It=e=>e<=R?R:us(z(e,11)),he=e=>ht(e)?[...e]:e,Dn=(e,t)=>{const s={...e};for(let o in t){const n=e[o];s[o]=$(n)?t[o]:n}return s},G=(e,t,s,o="_prev",n="_next")=>{let r=e._head,i=n;for(s&&(r=e._tail,i=o);r;){const d=r[i];t(r),r=d}},Lt=(e,t,s="_prev",o="_next")=>{const n=t[s],r=t[o];n?n[o]=r:e._head=r,r?r[s]=n:e._tail=n,t[s]=null,t[o]=null},dt=(e,t,s,o="_prev",n="_next")=>{let r=e._tail;for(;r&&s&&s(r,t);)r=r[o];const i=r?r[n]:e._head;r?r[n]=t:e._head=t,i?i[o]=t:e._tail=t,t[o]=r,t[n]=i};/**
 * Anime.js - core - ESM
 * @version v4.4.1
 * @license MIT
 * @copyright 2026 - Julian Garnier
 */const An=(e,t,s)=>{const o=e.style.transform;if(o){const n=e[Jt];let r=0;const i=o.length;let d;for(;r<i;){for(;r<i&&o.charCodeAt(r)===32;)r++;if(r>=i)break;const l=r;for(;r<i&&o.charCodeAt(r)!==40;)r++;if(r>=i)break;const m=o.substring(l,r);let h=1;const v=r+1;let _=-1,w=-1;for(r++;r<i&&h>0;){const V=o.charCodeAt(r);V===40?h++:V===41?h--:V===44&&h===1&&(_===-1?_=r:w===-1&&(w=r)),r++}const T=r-1;m==="translate"||m==="translate3d"?(_===-1?n.translateX=o.substring(v,T).trim():(n.translateX=o.substring(v,_).trim(),w===-1?n.translateY=o.substring(_+1,T).trim():(n.translateY=o.substring(_+1,w).trim(),n.translateZ=o.substring(w+1,T).trim())),d=o.substring(v,T)):m==="scale"||m==="scale3d"?_===-1?n.scale=o.substring(v,T).trim():(n.scaleX=o.substring(v,_).trim(),w===-1?n.scaleY=o.substring(_+1,T).trim():(n.scaleY=o.substring(_+1,w).trim(),n.scaleZ=o.substring(w+1,T).trim())):n[m]=o.substring(v,T)}if(t==="translate3d"&&d)return s&&(s[t]=d),d;const p=n[t];if(!$(p))return s&&(s[t]=p),p}return t==="translate3d"?"0px, 0px, 0px":t==="rotate3d"?"0, 0, 0, 0deg":He(t,"scale")?"1":He(t,"rotate")||He(t,"skew")?"0deg":"0px"},Ws=e=>{let t=mt;for(let s=0,o=Yt.length;s<o;s++){const n=Yt[s],r=e[n];if(r!==void 0){if(n==="translateX"){const i=e.translateY;if(i!==void 0){const d=e.translateZ;d!==void 0?(t+=`translate3d(${r},${i},${d}) `,s+=2):(t+=`translate(${r},${i}) `,s+=1);continue}}if(n==="scaleX"&&e.scale===void 0){const i=e.scaleY;if(i!==void 0){const d=e.scaleZ;d!==void 0?(t+=`scale3d(${r},${i},${d}) `,s+=2):(t+=`scale(${r},${i}) `,s+=1);continue}}t+=`${mn[n]}${r}) `}n==="rotateZ"&&e.rotate3d!==void 0&&(t+=`rotate3d(${e.rotate3d}) `)}return e.matrix!==void 0&&(t+=`matrix(${e.matrix}) `),e.matrix3d!==void 0&&(t+=`matrix3d(${e.matrix3d}) `),t};/**
 * Anime.js - core - ESM
 * @version v4.4.1
 * @license MIT
 * @copyright 2026 - Julian Garnier
 */const Pn=e=>{const t=gn.exec(e)||_n.exec(e),s=$(t[4])?1:+t[4];return[+t[1],+t[2],+t[3],s]},On=e=>{const t=e.length,s=t===4||t===5;return[+("0x"+e[1]+e[s?1:2]),+("0x"+e[s?2:3]+e[s?2:4]),+("0x"+e[s?3:5]+e[s?3:6]),t===5||t===9?+(+("0x"+e[s?4:7]+e[s?4:8])/255).toFixed(3):1]},es=(e,t,s)=>(s<0&&(s+=1),s>1&&(s-=1),s<1/6?e+(t-e)*6*s:s<1/2?t:s<2/3?e+(t-e)*(2/3-s)*6:e),Fn=e=>{const t=yn.exec(e)||bn.exec(e),s=+t[1]/360,o=+t[2]/100,n=+t[3]/100,r=$(t[4])?1:+t[4];let i,d,p;if(o===0)i=d=p=n;else{const l=n<.5?n*(1+o):n+o-n*o,m=2*n-l;i=z(es(m,l,s+1/3)*255,0),d=z(es(m,l,s)*255,0),p=z(es(m,l,s-1/3)*255,0)}return[i,d,p,r]},Mn=e=>Hs(e)?Pn(e):zs(e)?On(e):Ys(e)?Fn(e):[0,0,0,1];/**
 * Anime.js - core - ESM
 * @version v4.4.1
 * @license MIT
 * @copyright 2026 - Julian Garnier
 */const ae=(e,t)=>$(e)?t:e,Ve=(e,t,s,o,n,r)=>{let i;if(Nt(e))i=()=>{const d=e(t,s,o,r);return isNaN(+d)?d||0:+d};else if(kt(e)&&He(e,pn))i=()=>{var h;const d=e.match(Tn),p=d[1],l=d[2];let m=(h=getComputedStyle(t))==null?void 0:h.getPropertyValue(p);return(!m||m.trim()===mt)&&l&&(m=l.trim()),m||0};else return e;return n&&(n.func=i),i()},js=(e,t)=>e[Ct]?e[$s]&&Sn(e,t)?F.ATTRIBUTE:Yt.includes(t)||Us.get(t)?F.TRANSFORM:He(t,"--")?F.CSS_VAR:t in e.style?F.CSS:t in e?F.OBJECT:F.ATTRIBUTE:F.OBJECT,Es=(e,t,s)=>{const o=e.style[t];o&&s&&(s[t]=o);const n=o||getComputedStyle(e[un]||e).getPropertyValue(t);return n==="auto"?"0":n},Tt=(e,t,s,o)=>{const n=$(s)?js(e,t):s;if(n===F.OBJECT){const r=e[t];return r&&o&&(o[t]=r),r||0}if(n===F.ATTRIBUTE){const r=e.getAttribute(t);return r&&o&&(o[t]=r),r}return n===F.TRANSFORM?An(e,t,o):n===F.CSS_VAR?Es(e,t,o).trimStart():Es(e,t,o)},ts=(e,t,s)=>s==="-"?e-t:s==="+"?e+t:e*t,ps=()=>({t:L.NUMBER,n:0,u:null,o:null,d:null,s:null}),De=(e,t)=>{if(t.t=L.NUMBER,t.n=0,t.u=null,t.o=null,t.d=null,t.s=null,!e)return t;const s=+e;if(isNaN(s)){let o=e;o[1]==="="&&(t.o=o[0],o=o.slice(2));const n=o.includes(" ")?!1:vn.exec(o);if(n)return t.t=L.UNIT,t.n=+n[1],t.u=n[2],t;if(t.o)return t.n=+o,t;if(wn(o))return t.t=L.COLOR,t.d=Mn(o),t;{const r=o.match(xs);return t.t=L.COMPLEX,t.d=r?r.map(Number):[],t.s=o.split(xs)||[],t}}else return t.n=s,t},Ls=(e,t)=>(t.t=e._valueType,t.n=e._toNumber,t.u=e._unit,t.o=null,t.d=he(e._toNumbers),t.s=he(e._strings),t),Je=ps(),Js=(e,t,s)=>{const o=e._modifier,n=e._fromNumbers,r=e._toNumbers,i=z(be(o(Ze(n[0],r[0],t)),0,255),0),d=z(be(o(Ze(n[1],r[1],t)),0,255),0),p=z(be(o(Ze(n[2],r[2],t)),0,255),0),l=be(o(z(Ze(n[3],r[3],t),s)),0,1);if(e._composition!==le.none){const m=e._numbers;m[0]=i,m[1]=d,m[2]=p,m[3]=l}return`rgba(${i},${d},${p},${l})`},Gs=(e,t,s)=>{const o=e._modifier,n=e._fromNumbers,r=e._toNumbers,i=e._strings,d=e._composition!==le.none;let p=i[0];for(let l=0,m=r.length;l<m;l++){const h=o(z(Ze(n[l],r[l],t),s)),v=i[l+1];p+=`${v?h+v:h}`,d&&(e._numbers[l]=h)}return p};/**
 * Anime.js - core - ESM
 * @version v4.4.1
 * @license MIT
 * @copyright 2026 - Julian Garnier
 */const zt=(e,t,s,o,n)=>{const r=e.parent,i=e.duration,d=e.completed,p=e.iterationDuration,l=e.iterationCount,m=e._currentIteration,h=e._loopDelay,v=e._reversed,_=e._alternate,w=e._hasChildren,T=e._delay,V=e._currentTime,ce=T+p,B=t-T,A=be(V,-T,i),H=be(B,-T,i),Z=B-V,E=H>0,K=H>=i,q=i<=R,Y=n===Ce.FORCE;let ke=0,Ne=B,W=0;if(l>1){const we=~~(H/(p+(K?0:h)));e._currentIteration=be(we,0,l),K&&e._currentIteration--,ke=e._currentIteration%2,Ne=H%(p+h)||0}const Oe=v^(_&&ke),Fe=e._ease;let O=K?Oe?0:i:Oe?p-Ne:Ne;Fe&&(O=p*Fe(O/p)||0);const P=(r?r.backwards:B<V)?!Oe:!!Oe;if(e._currentTime=B,e._iterationTime=O,e.backwards=P,E&&!e.began?(e.began=!0,!s&&!(r&&(P||!r.began))&&e.onBegin(e)):B<=0&&(e.began=!1),!s&&!w&&E&&e._currentIteration!==m&&e.onLoop(e),Y||n===Ce.AUTO&&(t>=T&&t<=ce||t<=T&&A>T||t>=ce&&A!==i)||O>=ce&&A!==i||O<=T&&A>0||t<=A&&A===i&&d||K&&!d&&q){if(E&&(e.computeDeltaTime(A),s||e.onBeforeUpdate(e)),!w){const we=Y||(P?Z*-1:Z)>=ie.tickThreshold,_e=e._offset+(r?r._offset:0)+T+O;let y=e._head,I,j,de,ue,Q=0;for(;y;){const X=y._composition,D=y._currentTime,U=y._changeDuration,pe=y._absoluteStartTime+y._changeDuration,te=y._nextRep,ve=y._prevRep,se=X!==le.none;if((we||(D!==U||_e<=pe+(te?te._delay:0))&&(D!==0||_e>=y._absoluteStartTime))&&(!se||!y._isOverridden&&(!y._isOverlapped||_e<=pe)&&(!te||te._isOverridden||_e<=te._absoluteStartTime)&&(!ve||ve._isOverridden||_e>=ve._absoluteStartTime+ve._changeDuration+y._delay))){const Be=y._currentTime=be(O-y._startTime,0,U),xe=y._ease(Be/y._updateDuration),Ie=y._modifier,Te=y._valueType,J=y._tweenType,ne=J===F.OBJECT,oe=Te===L.NUMBER,ye=oe&&ne||xe===0||xe===1?-1:ie.precision;let M,me;if(oe?M=me=Ie(z(Ze(y._fromNumber,y._toNumber,xe),ye)):Te===L.UNIT?(me=Ie(z(Ze(y._fromNumber,y._toNumber,xe),ye)),M=`${me}${y._unit}`):Te===L.COLOR?M=Js(y,xe,ye):Te===L.COMPLEX&&(M=Gs(y,xe,ye)),se&&(y._number=me),!o&&X!==le.blend){const k=y.property;I=y.target,ne?I[k]=M:J===F.ATTRIBUTE?I.setAttribute(k,M):(j=I.style,J===F.TRANSFORM?(I!==de&&(de=I,ue=I[Jt]),ue[k]=M,Q=1):J===F.CSS?j[k]=M:J===F.CSS_VAR&&j.setProperty(k,M)),E&&(W=1)}else y._value=M}Q&&y._renderTransforms&&(j.transform=Ws(ue),Q=0),y=y._next}!s&&W&&e.onRender(e)}!s&&E&&e.onUpdate(e)}return r&&q?!s&&(r.began&&!P&&B>0&&!d||P&&B<=R&&d)&&(e.onComplete(e),e.completed=!P):E&&K?l===1/0?e._startTime+=e.duration:e._currentIteration>=l-1&&(e.paused=!0,!d&&!w&&(e.completed=!0,!s&&!(r&&(P||!r.began))&&(e.onComplete(e),e._resolve(e)))):e.completed=!1,W},ct=(e,t,s,o,n)=>{const r=e._currentIteration;if(zt(e,t,s,o,n),e._hasChildren){const i=e,d=i.backwards,p=o?t:i._iterationTime,l=ft();let m=0,h=!0;if(!o&&i._currentIteration!==r){const v=i.iterationDuration;G(i,_=>{if(!d)!_.completed&&!_.backwards&&_._currentTime<_.iterationDuration&&zt(_,v,s,1,Ce.FORCE),_.began=!1,_.completed=!1;else{const w=_.duration,T=_._offset+_._delay,V=T+w;!s&&w<=R&&(!T||V===v)&&_.onComplete(_)}}),s||i.onLoop(i)}G(i,v=>{const _=z((p-v._offset)*v._speed,12),w=v._fps<i._fps?v.requestTick(l):n;m+=zt(v,_,s,o,w),!v.completed&&h&&(h=!1)},d),!s&&m&&i.onRender(i),(h||d)&&i._currentTime>=i.duration&&(i.paused=!0,i.completed||(i.completed=!0,s||(i.onComplete(i),i._resolve(i))))}};/**
 * Anime.js - core - ESM
 * @version v4.4.1
 * @license MIT
 * @copyright 2026 - Julian Garnier
 */const ws={},$n=(e,t,s)=>{if(s===F.TRANSFORM){const o=Us.get(e);return o||e}else if(s===F.CSS||s===F.ATTRIBUTE&&Xs(t)&&e in t.style){const o=ws[e];if(o)return o;{const n=e&&qs(e);return ws[e]=n,n}}else return e},Zs=(e,t=!1)=>{if(e._hasChildren)G(e,s=>Zs(s,t),!0);else{const s=e;s.pause(),G(s,o=>{const n=o.property,r=o.target,i=o._tweenType,d=o._inlineValue,p=wt(d)||d===mt;if(i===F.OBJECT)!t&&!p&&(r[n]=d);else if(r[Ct])if(i===F.ATTRIBUTE)t||(p?r.removeAttribute(n):r.setAttribute(n,d));else{const l=r.style;if(i===F.TRANSFORM){const m=r[Jt];p?delete m[n]:m[n]=d,o._renderTransforms&&(Object.keys(m).length?l.transform=Ws(m):l.removeProperty("transform"))}else p?l.removeProperty(qs(n)):l[n]=d}r[Ct]&&s._tail===o&&s.targets.forEach(l=>{l.getAttribute&&l.getAttribute("style")===mt&&l.removeAttribute("style")})})}return e};/**
 * Anime.js - core - ESM
 * @version v4.4.1
 * @license MIT
 * @copyright 2026 - Julian Garnier
 */class Ks{constructor(t=0){this.deltaTime=0,this._currentTime=t,this._lastTickTime=t,this._startTime=t,this._lastTime=t,this._scheduledTime=0,this._frameDuration=pt/as,this._fps=as,this._speed=1,this._hasChildren=!1,this._head=null,this._tail=null}get fps(){return this._fps}set fps(t){const s=this._frameDuration,o=+t,n=o<R?R:o,r=pt/n;n>Wt.frameRate&&(Wt.frameRate=n),this._fps=n,this._frameDuration=r,this._scheduledTime+=r-s}get speed(){return this._speed}set speed(t){const s=+t;this._speed=s<R?R:s}requestTick(t){const s=this._scheduledTime;if(this._lastTickTime=t,t<s)return Ce.NONE;const o=this._frameDuration,n=t-s;return this._scheduledTime+=n<o?o:n,Ce.AUTO}computeDeltaTime(t){const s=t-this._lastTime;return this.deltaTime=s,this._lastTime=t,s}}/**
 * Anime.js - animation - ESM
 * @version v4.4.1
 * @license MIT
 * @copyright 2026 - Julian Garnier
 */const ut={animation:null,update:Se},Un=e=>{let t=ut.animation;return t||(t={duration:R,computeDeltaTime:Se,_offset:0,_delay:0,_head:null,_tail:null},ut.animation=t,ut.update=()=>{e.forEach(s=>{for(let o in s){const n=s[o],r=n._head;if(r){const i=r._valueType,d=i===L.COMPLEX||i===L.COLOR?he(r._fromNumbers):null;let p=r._fromNumber,l=n._tail;for(;l&&l!==r;){if(d)for(let m=0,h=l._numbers.length;m<h;m++)d[m]+=l._numbers[m];else p+=l._number;l=l._prevAdd}r._toNumber=p,r._toNumbers=d}}}),zt(t,1,1,0,Ce.FORCE)}),t};/**
 * Anime.js - engine - ESM
 * @version v4.4.1
 * @license MIT
 * @copyright 2026 - Julian Garnier
 */const Qs=We?requestAnimationFrame:setImmediate,Vn=We?cancelAnimationFrame:clearImmediate;class qn extends Ks{constructor(t){super(t),this.useDefaultMainLoop=!0,this.pauseOnDocumentHidden=!0,this.defaults=Wt,this.paused=!0,this.reqId=0}update(){const t=this._currentTime=ft();if(this.requestTick(t)){this.computeDeltaTime(t);const s=this._speed,o=this._fps;let n=this._head;for(;n;){const r=n._next;n.paused?(Lt(this,n),this._hasChildren=!!this._tail,n._running=!1,n.completed&&!n._cancelled&&n.cancel()):ct(n,(t-n._startTime)*n._speed*s,0,0,n._fps<o?n.requestTick(t):Ce.AUTO),n=r}ut.update()}}wake(){return this.useDefaultMainLoop&&!this.reqId&&(this.requestTick(ft()),this.reqId=Qs(en)),this}pause(){if(this.reqId)return this.paused=!0,Xn()}resume(){if(this.paused)return this.paused=!1,G(this,t=>t.resetTime()),this.wake()}get speed(){return this._speed*(ie.timeScale===1?1:pt)}set speed(t){this._speed=t*ie.timeScale,G(this,s=>s.speed=s._speed)}get timeUnit(){return ie.timeScale===1?"ms":"s"}set timeUnit(t){const o=t==="s",n=o?.001:1;if(ie.timeScale!==n){ie.timeScale=n,ie.tickThreshold=200*n;const r=o?.001:pt;this.defaults.duration*=r,this._speed*=r}}get precision(){return ie.precision}set precision(t){ie.precision=t}}const ge=(()=>{const e=new qn(ft());return We&&(Vs.engine=e,St.addEventListener("visibilitychange",()=>{e.pauseOnDocumentHidden&&(St.hidden?e.pause():e.resume())})),e})(),en=()=>{ge._head?(ge.reqId=Qs(en),ge.update()):ge.reqId=0},Xn=()=>(Vn(ge.reqId),ge.reqId=0,ge);/**
 * Anime.js - animation - ESM
 * @version v4.4.1
 * @license MIT
 * @copyright 2026 - Julian Garnier
 */const jt={_rep:new WeakMap,_add:new Map},ms=(e,t,s="_rep")=>{const o=jt[s];let n=o.get(e);return n||(n={},o.set(e,n)),n[t]?n[t]:n[t]={_head:null,_tail:null}},zn=(e,t)=>e._isOverridden||e._absoluteStartTime>t._absoluteStartTime,Ht=e=>{e._isOverlapped=1,e._isOverridden=1,e._changeDuration=R,e._currentTime=R},tn=(e,t)=>{const s=e._composition;if(s===le.replace){const o=e._absoluteStartTime;dt(t,e,zn,"_prevRep","_nextRep");const n=e._prevRep;if(n){const r=n.parent,i=n._absoluteStartTime+n._changeDuration;if(e.parent.id!==r.id&&r.iterationCount>1&&i+(r.duration-r.iterationDuration)>o){Ht(n);let l=n._prevRep;for(;l&&l.parent.id===r.id;)Ht(l),l=l._prevRep}const d=o-e._delay;if(i>d){const l=n._startTime,m=i-(l+n._updateDuration),h=z(d-m-l,12);n._changeDuration=h,n._currentTime=h,n._isOverlapped=1,h<R&&Ht(n)}let p=!0;if(G(r,l=>{l._isOverlapped||(p=!1)}),p){const l=r.parent;if(l){let m=!0;G(l,h=>{h!==r&&G(h,v=>{v._isOverlapped||(m=!1)})}),m&&l.cancel()}else r.cancel()}}}else if(s===le.blend){const o=ms(e.target,e.property,"_add"),n=Un(jt._add);let r=o._head;r||(r={...e},r._composition=le.replace,r._updateDuration=R,r._startTime=0,r._numbers=he(e._fromNumbers),r._number=0,r._next=null,r._prev=null,dt(o,r),dt(n,r));const i=e._toNumber;if(e._fromNumber=r._fromNumber-i,e._toNumber=0,e._numbers=he(e._fromNumbers),e._number=0,r._fromNumber=i,e._toNumbers){const d=he(e._toNumbers);d&&d.forEach((p,l)=>{e._fromNumbers[l]=r._fromNumbers[l]-p,e._toNumbers[l]=0}),r._fromNumbers=d}dt(o,e,null,"_prevAdd","_nextAdd")}return e},Hn=e=>{const t=e._composition;if(t!==le.none){const s=e.target,o=e.property,i=jt._rep.get(s)[o];if(Lt(i,e,"_prevRep","_nextRep"),t===le.blend){const d=jt._add,p=d.get(s);if(!p)return;const l=p[o],m=ut.animation;Lt(l,e,"_prevAdd","_nextAdd");const h=l._head;if(h&&h===l._tail){Lt(l,h,"_prevAdd","_nextAdd"),Lt(m,h);let v=!0;for(let _ in p)if(p[_]._head){v=!1;break}v&&d.delete(s)}}}return e};/**
 * Anime.js - timer - ESM
 * @version v4.4.1
 * @license MIT
 * @copyright 2026 - Julian Garnier
 */const Is=e=>(e.paused=!0,e.began=!1,e.completed=!1,e),ls=e=>(e._cancelled&&(e._hasChildren?G(e,ls):G(e,t=>{t._composition!==le.none&&tn(t,ms(t.target,t.property))}),e._cancelled=0),e);let Ss=0;const Yn=(e,t)=>e._priority>t._priority;class Wn extends Ks{constructor(t={},s=null,o=0){super(0),++Ss;const{id:n,delay:r,duration:i,reversed:d,alternate:p,loop:l,loopDelay:m,autoplay:h,frameRate:v,playbackRate:_,priority:w,onComplete:T,onLoop:V,onPause:ce,onBegin:B,onBeforeUpdate:A,onUpdate:H}=t,Z=s?0:ge._lastTickTime,E=s?s.defaults:ie.defaults,K=Nt(r)||$(r)?E.delay:+r,q=Nt(i)||$(i)?1/0:+i,Y=ae(l,E.loop),ke=ae(m,E.loopDelay);let Ne=Y===!0||Y===1/0||Y<0?1/0:Y+1,W=0;s?W=o:(ge.reqId||ge.requestTick(ft()),W=(ge._lastTickTime-ge._startTime)*ie.timeScale),this.id=$(n)?Ss:n,this.parent=s,this.duration=us((q+ke)*Ne-ke)||R,this.backwards=!1,this.paused=!0,this.began=!1,this.completed=!1,this.onBegin=B||E.onBegin,this.onBeforeUpdate=A||E.onBeforeUpdate,this.onUpdate=H||E.onUpdate,this.onLoop=V||E.onLoop,this.onPause=ce||E.onPause,this.onComplete=T||E.onComplete,this.iterationDuration=q,this.iterationCount=Ne,this._autoplay=s?!1:ae(h,E.autoplay),this._offset=W,this._delay=K,this._loopDelay=ke,this._iterationTime=0,this._currentIteration=0,this._resolve=Se,this._running=!1,this._reversed=+ae(d,E.reversed),this._reverse=this._reversed,this._cancelled=0,this._alternate=ae(p,E.alternate),this._prev=null,this._next=null,this._lastTickTime=Z,this._startTime=Z,this._lastTime=Z,this._fps=ae(v,E.frameRate),this._speed=ae(_,E.playbackRate),this._priority=+ae(w,1)}get cancelled(){return!!this._cancelled}set cancelled(t){t?this.cancel():this.reset(!0).play()}get currentTime(){return be(z(this._currentTime,ie.precision),-this._delay,this.duration)}set currentTime(t){const s=this.paused;this.pause().seek(+t),s||this.resume()}get iterationCurrentTime(){return be(z(this._iterationTime,ie.precision),0,this.iterationDuration)}set iterationCurrentTime(t){this.currentTime=this.iterationDuration*this._currentIteration+t}get progress(){return be(z(this._currentTime/this.duration,10),0,1)}set progress(t){this.currentTime=this.duration*t}get iterationProgress(){return be(z(this._iterationTime/this.iterationDuration,10),0,1)}set iterationProgress(t){const s=this.iterationDuration;this.currentTime=s*this._currentIteration+s*t}get currentIteration(){return this._currentIteration}set currentIteration(t){this.currentTime=this.iterationDuration*be(+t,0,this.iterationCount-1)}get reversed(){return!!this._reversed}set reversed(t){t?this.reverse():this.play()}get speed(){return super.speed}set speed(t){super.speed=t,this.resetTime()}reset(t=!1){return ls(this),this._reversed&&!this._reverse&&(this.reversed=!1),this._iterationTime=this.iterationDuration,ct(this,0,1,~~t,Ce.FORCE),Is(this),this._hasChildren&&G(this,Is),this}init(t=!1){this.fps=this._fps,this.speed=this._speed,!t&&this._hasChildren&&ct(this,this.duration,1,~~t,Ce.FORCE),this.reset(t);const s=this._autoplay;return s===!0?this.resume():s&&!$(s.linked)&&s.link(this),this}resetTime(){const t=1/(this._speed*ge._speed);return this._startTime=ft()-(this._currentTime+this._delay)*t,this}pause(){return this.paused?this:(this.paused=!0,this.onPause(this),this)}resume(){return this.paused?(this.paused=!1,this.duration<=R&&!this._hasChildren?ct(this,R,0,0,Ce.FORCE):(this._running||(dt(ge,this,Yn),ge._hasChildren=!0,this._running=!0),this.resetTime(),this._startTime-=12,ge.wake()),this):this}restart(){return this.reset().resume()}seek(t,s=0,o=0){ls(this),this.completed=!1;const n=this.paused;return this.paused=!0,ct(this,t+this._delay,~~s,~~o,Ce.AUTO),n?this:this.resume()}alternate(){const t=this._reversed,s=this.iterationCount,o=this.iterationDuration,n=s===1/0?Bn(is/o):s;return this._reversed=+(this._alternate&&!(n%2)?t:!t),s===1/0?this.iterationProgress=this._reversed?1-this.iterationProgress:this.iterationProgress:this.seek(o*n-this._currentTime),this.resetTime(),this}play(){return this._reversed&&this.alternate(),this.resume()}reverse(){return this._reversed||this.alternate(),this.resume()}cancel(){return this._hasChildren?G(this,t=>t.cancel(),!0):G(this,Hn),this._cancelled=1,this.pause()}stretch(t){const s=this.duration,o=It(t);if(s===o)return this;const n=t/s,r=t<=R;return this.duration=r?R:o,this.iterationDuration=r?R:It(this.iterationDuration*n),this._offset*=n,this._delay*=n,this._loopDelay*=n,this}revert(){ct(this,0,1,0,Ce.AUTO);const t=this._autoplay;return t&&t.linked&&t.linked===this&&t.revert(),this.cancel()}complete(t=0){return this.seek(this.duration,t).cancel()}then(t=Se){const s=this.then,o=()=>{this.then=null,t(this),this.then=s,this._resolve=Se};return new Promise(n=>(this._resolve=()=>n(o()),this.completed&&this._resolve(),this))}}/**
 * Anime.js - core - ESM
 * @version v4.4.1
 * @license MIT
 * @copyright 2026 - Julian Garnier
 */function Cs(e){const t=kt(e)?En.root.querySelectorAll(e):e;if(t instanceof NodeList||t instanceof HTMLCollection)return t}function jn(e){if(wt(e))return[];if(!We)return ht(e)&&e.flat(1/0)||[e];if(ht(e)){const s=e.flat(1/0),o=[];for(let n=0,r=s.length;n<r;n++){const i=s[n];if(!wt(i)){const d=Cs(i);if(d)for(let p=0,l=d.length;p<l;p++){const m=d[p];if(!wt(m)){let h=!1;for(let v=0,_=o.length;v<_;v++)if(o[v]===m){h=!0;break}h||o.push(m)}}else{let p=!1;for(let l=0,m=o.length;l<m;l++)if(o[l]===i){p=!0;break}p||o.push(i)}}}return o}const t=Cs(e);return t?Array.from(t):[e]}function Jn(e){const t=jn(e),s=t.length;if(s)for(let o=0;o<s;o++){const n=t[o];if(!n[vs]){n[vs]=!0;const r=Xs(n);(n.nodeType||r)&&(n[Ct]=!0,n[$s]=r,n[Jt]={})}}return t}/**
 * Anime.js - core - ESM
 * @version v4.4.1
 * @license MIT
 * @copyright 2026 - Julian Garnier
 */const ss={deg:1,rad:180/ds,turn:360},ks={},Ns=(e,t,s,o=!1)=>{const n=t.u,r=t.n;if(t.t===L.UNIT&&n===s)return t;const i=r+n+s,d=ks[i];if(!$(d)&&!o)t.n=d;else{let p;if(n in ss)p=r*ss[n]/ss[s];else{const m=e.cloneNode(),h=e.parentNode,v=h&&h!==St?h:St.body;v.appendChild(m);const _=m.style;_.width=100+n;const w=m.offsetWidth||100;_.width=100+s;const T=m.offsetWidth||100,V=w/T;v.removeChild(m),p=V*r}t.n=p,ks[i]=p}return t.t,L.UNIT,t.u=s,t};/**
 * Anime.js - easings - ESM
 * @version v4.4.1
 * @license MIT
 * @copyright 2026 - Julian Garnier
 */const Ye=e=>e;/**
 * Anime.js - easings - ESM
 * @version v4.4.1
 * @license MIT
 * @copyright 2026 - Julian Garnier
 */const Et=(e=1.68)=>t=>lt(t,+e),cs={in:e=>t=>e(t),out:e=>t=>1-e(1-t),inOut:e=>t=>t<.5?e(t*2)/2:1-e(t*-2+2)/2,outIn:e=>t=>t<.5?(1-e(1-t*2))/2:(e(t*2-1)+1)/2},Gn=ds/2,Bs=ds*2,Rs={[mt]:Et,Quad:Et(2),Cubic:Et(3),Quart:Et(4),Quint:Et(5),Sine:e=>1-Nn(e*Gn),Circ:e=>1-Cn(1-e*e),Expo:e=>e?lt(2,10*e-10):0,Bounce:e=>{let t,s=4;for(;e<((t=lt(2,--s))-1)/11;);return 1/lt(4,3-s)-7.5625*lt((t*3-2)/22-e,2)},Back:(e=1.7)=>t=>(+e+1)*t*t*t-+e*t*t,Elastic:(e=1,t=.3)=>{const s=be(+e,1,10),o=be(+t,R,2),n=o/Bs*Rn(1/s),r=Bs/o;return i=>i===0||i===1?i:-s*lt(2,-10*(1-i))*kn((1-i-n)*r)}},ns=(()=>{const e={linear:Ye,none:Ye};for(let t in cs)for(let s in Rs){const o=Rs[s],n=cs[t];e[t+s]=s===mt||s==="Back"||s==="Elastic"?(r,i)=>n(o(r,i)):n(o)}return e})(),$t={linear:Ye,none:Ye},Zn=e=>{if($t[e])return $t[e];if(e.indexOf("(")<=-1){const s=cs[e]||e.includes("Back")||e.includes("Elastic")?ns[e]():ns[e];return s?$t[e]=s:Ye}else{const t=e.slice(0,-1).split("("),s=ns[t[0]];return s?$t[e]=s(...t[1].split(",")):Ye}},Ds=["steps(","irregular(","linear(","cubicBezier("],As=e=>{if(kt(e)){for(let s=0,o=Ds.length;s<o;s++)if(He(e,Ds[s]))return console.warn(`String syntax for \`ease: "${e}"\` has been removed from the core and replaced by importing and passing the easing function directly: \`ease: ${e}\``),Ye}return Nt(e)?e:kt(e)?Zn(e):Ye};/**
 * Anime.js - animation - ESM
 * @version v4.4.1
 * @license MIT
 * @copyright 2026 - Julian Garnier
 */const b=ps(),x=ps(),it={},Ut={func:null},os={func:null},Vt=[null],at=[null,null],qt={to:null};let Kn=0,Ps=0,ze,Pe;const Qn=(e,t)=>{const s={};if(ht(e)){const o=[].concat(...e.map(n=>Object.keys(n))).filter(Xt);for(let n=0,r=o.length;n<r;n++){const i=o[n],d=e.map(p=>{const l={};for(let m in p){const h=p[m];Xt(m)?m===i&&(l.to=h):l[m]=h}return l});s[i]=d}}else{const o=ae(t.duration,ie.defaults.duration);Object.keys(e).map(r=>({o:parseFloat(r)/100,p:e[r]})).sort((r,i)=>r.o-i.o).forEach(r=>{const i=r.o,d=r.p;for(let p in d)if(Xt(p)){let l=s[p];l||(l=s[p]=[]);const m=i*o;let h=l.length,v=l[h-1];const _={to:d[p]};let w=0;for(let T=0;T<h;T++)w+=l[T].duration;h===1&&(_.from=v.to),d.ease&&(_.ease=d.ease),_.duration=m-(h?w:0),l.push(_)}return r});for(let r in s){const i=s[r];let d;for(let p=0,l=i.length;p<l;p++){const m=i[p],h=m.ease;m.ease=d||void 0,d=h}i[0].duration||i.shift()}}return s};class eo extends Wn{constructor(t,s,o,n,r=!1,i=0,d){super(s,o,n),++Ps;const p=Jn(t),l=p.length,m=s.keyframes,h=m?Dn(Qn(m,s),s):s,{id:v,delay:_,duration:w,ease:T,playbackEase:V,modifier:ce,composition:B,onRender:A}=h,H=o?o.defaults:ie.defaults,Z=ae(T,H.ease),E=ae(V,H.playbackEase),K=E?As(E):null,q=!$(Z.ease),Y=q?Z.ease:ae(T,K?"linear":H.ease),ke=q?Z.settlingDuration:ae(w,H.duration),Ne=ae(_,H.delay),W=ce||H.modifier,Oe=$(B)&&l>=pt?le.none:$(B)?H.composition:B,Fe=this._offset+(o?o._offset:0);q&&(Z.parent=this);let O=NaN,P=NaN,we=0,_e=0;for(let y=0;y<l;y++){const I=p[y],j=i||y,de=d||p;let ue=NaN,Q=NaN;for(let X in h)if(Xt(X)){const D=js(I,X),U=$n(X,I,D);let pe=h[X];const te=ht(pe);if(r&&!te&&(at[0]=pe,at[1]=pe,pe=at),te){const Te=pe.length,J=!Qt(pe[0]);Te===2&&J?(qt.to=pe,Vt[0]=qt,ze=Vt):Te>2&&J?(ze=[],pe.forEach((ne,oe)=>{oe?oe===1?(at[1]=ne,ze.push(at)):ze.push(ne):at[0]=ne})):ze=pe}else Vt[0]=pe,ze=Vt;let ve=null,se=null,Be=NaN,xe=0,Ie=0;for(let Te=ze.length;Ie<Te;Ie++){const J=ze[Ie];Qt(J)?Pe=J:(qt.to=J,Pe=qt),Ut.func=null,os.func=null;const ne=Ve(ae(Pe.composition,Oe),I,j,de,null,null),oe=Ln(ne)?ne:le[ne];!ve&&oe!==le.none&&(ve=ms(I,U));const ye=ve?ve._tail:null,M=o&&ye&&ye.parent.parent===o?ye:se,me=Ve(Pe.to,I,j,de,Ut,M);let k;Qt(me)&&!$(me.to)?(Pe=me,k=me.to):k=me;const Ke=Ve(Pe.from,I,j,de,null,M),gt=Pe.ease||Y,Qe=Ve(gt,I,j,de,null,M),Le=Nt(Qe)||kt(Qe)?Qe:gt,et=!$(Le)&&!$(Le.ease),Ae=et?Le.ease:Le,Bt=et?Le.settlingDuration:Ve(ae(Pe.duration,Te>1?Ve(ke,I,j,de,null,M)/Te:ke),I,j,de,null,M),tt=Ve(ae(Pe.delay,Ie?0:Ne),I,j,de,null,M),qe=Pe.modifier||W,st=!$(Ke),_t=!$(k),je=ht(k),Gt=je||st&&_t,Me=se?xe+tt:tt,yt=z(Fe+Me,12);!_e&&(st||je)&&(_e=1);let Ee=se;if(oe!==le.none){let C=ve._head;for(;C&&!C._isOverridden&&C._absoluteStartTime<=yt;)if(Ee=C,C=C._nextRep,C&&C._absoluteStartTime>=yt)for(;C;)Ht(C),C=C._nextRep}if(Gt){De(je?Ve(k[0],I,j,de,os,M):Ke,b),De(je?Ve(k[1],I,j,de,Ut,M):k,x);const C=Tt(I,U,D,it);b.t===L.NUMBER&&(Ee?Ee._valueType===L.UNIT&&(b.t=L.UNIT,b.u=Ee._unit):(De(C,Je),Je.t===L.UNIT&&(b.t=L.UNIT,b.u=Je.u)))}else _t?De(k,x):se?Ls(se,x):De(o&&Ee&&Ee.parent.parent===o?Ee._value:Tt(I,U,D,it),x),st?De(Ke,b):se?Ls(se,b):De(o&&Ee&&Ee.parent.parent===o?Ee._value:Tt(I,U,D,it),b);if(b.o&&(b.n=ts(Ee?Ee._toNumber:De(Tt(I,U,D,it),Je).n,b.n,b.o)),x.o&&(x.n=ts(b.n,x.n,x.o)),b.t!==x.t){if(b.t===L.COMPLEX||x.t===L.COMPLEX){const C=b.t===L.COMPLEX?b:x,ee=b.t===L.COMPLEX?x:b;ee.t=L.COMPLEX,ee.s=he(C.s),ee.d=C.d.map(()=>ee.n)}else if(b.t===L.UNIT||x.t===L.UNIT){const C=b.t===L.UNIT?b:x,ee=b.t===L.UNIT?x:b;ee.t=L.UNIT,ee.u=C.u}else if(b.t===L.COLOR||x.t===L.COLOR){const C=b.t===L.COLOR?b:x,ee=b.t===L.COLOR?x:b;ee.t=L.COLOR,ee.s=C.s,ee.d=[0,0,0,1]}}if(b.u!==x.u){let C=x.u?b:x;C=Ns(I,C,x.u?x.u:b.u,!1)}if(x.d&&b.d&&x.d.length!==b.d.length){const C=b.d.length>x.d.length?b:x,ee=C===b?x:b;ee.d=C.d.map((Dt,vt)=>$(ee.d[vt])?0:ee.d[vt]),ee.s=he(C.s)}const nt=z(+Bt||R,12);let Rt=it[U];wt(Rt)||(it[U]=null);const re={parent:this,id:Kn++,property:U,target:I,_value:null,_toFunc:Ut.func,_fromFunc:os.func,_ease:As(Ae),_fromNumbers:he(b.d),_toNumbers:he(x.d),_strings:he(x.s),_fromNumber:b.n,_toNumber:x.n,_numbers:he(b.d),_number:b.n,_unit:x.u,_modifier:qe,_currentTime:0,_startTime:Me,_delay:+tt,_updateDuration:nt,_changeDuration:nt,_absoluteStartTime:yt,_tweenType:D,_valueType:x.t,_composition:oe,_isOverlapped:0,_isOverridden:0,_renderTransforms:0,_inlineValue:Rt,_prevRep:null,_nextRep:null,_prevAdd:null,_nextAdd:null,_prev:null,_next:null};oe!==le.none&&tn(re,ve);const bt=re._valueType;bt===L.COMPLEX?re._value=Gs(re,1,-1):bt===L.COLOR?re._value=Js(re,1,-1):bt===L.UNIT?re._value=`${qe(re._toNumber)}${re._unit}`:re._value=qe(re._toNumber),isNaN(Be)&&(Be=re._startTime),xe=z(Me+nt,12),se=re,we++,dt(this,re)}(isNaN(P)||Be<P)&&(P=Be),(isNaN(O)||xe>O)&&(O=xe),D===F.TRANSFORM&&(ue=we-Ie,Q=we)}if(!isNaN(ue)){let X=0;G(this,D=>{X>=ue&&X<Q&&(D._renderTransforms=1,D._composition===le.blend&&G(ut.animation,U=>{U.id===D.id&&(U._renderTransforms=1)})),X++})}}l||console.warn("No target found. Make sure the element you're trying to animate is accessible before creating your animation."),P?(G(this,y=>{y._startTime-y._delay||(y._delay-=P),y._startTime-=P}),O-=P):P=0,O||(O=R,this.iterationCount=0),this.targets=p,this.id=$(v)?Ps:v,this.duration=O===R?R:us((O+this._loopDelay)*this.iterationCount-this._loopDelay)||R,this.onRender=A||H.onRender,this._ease=K,this._delay=P,this.iterationDuration=O,!this._autoplay&&_e&&this.onRender(this)}stretch(t){const s=this.duration;if(s===It(t))return this;const o=t/s;return G(this,n=>{n._updateDuration=It(n._updateDuration*o),n._changeDuration=It(n._changeDuration*o),n._currentTime*=o,n._startTime*=o,n._absoluteStartTime*=o}),super.stretch(t)}refresh(){return G(this,t=>{const s=t._toFunc,o=t._fromFunc;(s||o)&&(o?(De(o(),b),b.u!==t._unit&&t.target[Ct]&&Ns(t.target,b,t._unit,!0),t._fromNumbers=he(b.d),t._fromNumber=b.n):s&&(De(Tt(t.target,t.property,t._tweenType),Je),t._fromNumbers=he(Je.d),t._fromNumber=Je.n),s&&(De(s(),x),t._toNumbers=he(x.d),t._strings=he(x.s),t._toNumber=x.o?ts(t._fromNumber,x.n,x.o):x.n))}),this.duration===R&&this.restart(),this}revert(){return super.revert(),Zs(this)}then(t){return super.then(t)}}const Ge=(e,t)=>new eo(e,t,null,0,!1).init(),Os="talos-loader-styles";function sn(){if(document.getElementById(Os))return;const e=document.createElement("style");e.id=Os,e.textContent=`
    .talos-loader {
      --talos-bg: #050505;
      --talos-panel: #09090b;
      --talos-line: rgba(244, 224, 77, 0.34);
      --talos-line-soft: rgba(244, 224, 77, 0.12);
      --talos-gold: #f4e04d;
      --talos-text: #ededed;
      --talos-muted: #6b7280;
      position: fixed;
      inset: 0;
      width: 100vw;
      height: 100vh;
      overflow: hidden;
      background:
        radial-gradient(circle at 50% 47%, rgba(244, 224, 77, 0.13), transparent 33%),
        radial-gradient(circle at 18% 18%, rgba(255, 255, 255, 0.055), transparent 24%),
        #050505;
      color: var(--talos-text);
      z-index: 50;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      isolation: isolate;
    }

    .talos-loader::before {
      content: "";
      position: absolute;
      inset: 0;
      opacity: 0.085;
      background-image:
        linear-gradient(rgba(255,255,255,0.42) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.42) 1px, transparent 1px);
      background-size: 44px 44px;
      mask-image: radial-gradient(circle at center, black 0 42%, transparent 78%);
      pointer-events: none;
    }

    .talos-loader::after {
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.045), transparent 13%, transparent 86%, rgba(244,224,77,0.08)),
        repeating-linear-gradient(180deg, rgba(255,255,255,0.025) 0 1px, transparent 1px 4px);
      mix-blend-mode: screen;
      opacity: 0.32;
      pointer-events: none;
    }

    .talos-loader__shell {
      position: relative;
      z-index: 3;
      min-height: 100%;
      display: grid;
      place-items: center;
      padding: 104px 24px 72px;
    }

    .talos-loader__system {
      width: min(620px, 88vw);
      display: grid;
      justify-items: center;
      gap: 18px;
      transform: translateY(8px);
    }

    .talos-loader__preview {
      position: relative;
      width: clamp(190px, 22vw, 278px);
      aspect-ratio: 9 / 16;
      overflow: hidden;
      border: 1px solid rgba(244, 224, 77, 0.36);
      border-radius: 8px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.08), transparent 16%),
        radial-gradient(circle at 50% 32%, rgba(244, 224, 77, 0.18), transparent 42%),
        #070707;
      box-shadow:
        0 0 0 1px rgba(255,255,255,0.045) inset,
        0 24px 90px rgba(0,0,0,0.74),
        0 0 70px rgba(244, 224, 77, 0.13);
    }

    .talos-loader__preview::before {
      content: "";
      position: absolute;
      inset: 0;
      background-image:
        linear-gradient(rgba(255,255,255,0.06) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.06) 1px, transparent 1px);
      background-size: 33.333% 25%;
      opacity: 0.7;
      z-index: 1;
    }

    .talos-loader__preview::after {
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(90deg, rgba(0,0,0,0.76), transparent 18%, transparent 82%, rgba(0,0,0,0.76)),
        linear-gradient(180deg, rgba(0,0,0,0.68), transparent 20%, transparent 74%, rgba(0,0,0,0.72));
      z-index: 5;
      pointer-events: none;
    }

    .talos-loader__strip {
      position: absolute;
      left: -18%;
      width: 136%;
      height: 12.5%;
      border-block: 1px solid rgba(255,255,255,0.055);
      background:
        linear-gradient(90deg, transparent 0 6%, rgba(255,255,255,0.075) 12%, rgba(244,224,77,0.17) 44%, rgba(255,255,255,0.08) 68%, transparent 96%),
        linear-gradient(180deg, rgba(255,255,255,0.04), rgba(0,0,0,0.16));
      opacity: 0.78;
      transform: skewX(-8deg);
      animation: talos-strip-drift 3.6s cubic-bezier(.4,0,.2,1) infinite;
      z-index: 2;
    }

    .talos-loader__strip:nth-child(even) {
      animation-direction: reverse;
      opacity: 0.48;
    }

    .talos-loader__strip:nth-child(1) { top: 6%; animation-delay: -0.3s; }
    .talos-loader__strip:nth-child(2) { top: 20%; animation-delay: -1.1s; }
    .talos-loader__strip:nth-child(3) { top: 34%; animation-delay: -0.7s; }
    .talos-loader__strip:nth-child(4) { top: 48%; animation-delay: -1.8s; }
    .talos-loader__strip:nth-child(5) { top: 62%; animation-delay: -1.3s; }
    .talos-loader__strip:nth-child(6) { top: 76%; animation-delay: -2.4s; }

    .talos-loader__subject {
      position: absolute;
      inset: 22% 22% 19%;
      border-radius: 999px 999px 14px 14px;
      background:
        radial-gradient(circle at 50% 18%, rgba(237,237,237,0.78) 0 8%, transparent 8.6%),
        linear-gradient(180deg, transparent 0 19%, rgba(237,237,237,0.1) 19.5% 43%, transparent 44%),
        linear-gradient(145deg, rgba(244,224,77,0.18), rgba(255,255,255,0.035));
      border: 1px solid rgba(244,224,77,0.18);
      filter: blur(0.2px);
      opacity: 0.64;
      z-index: 3;
      animation: talos-subject-pulse 2.4s ease-in-out infinite;
    }

    .talos-loader__scan {
      position: absolute;
      left: -18%;
      right: -18%;
      height: 23%;
      top: -24%;
      background:
        linear-gradient(180deg, transparent, rgba(244,224,77,0.08) 32%, rgba(244,224,77,0.38) 50%, rgba(244,224,77,0.08) 68%, transparent);
      filter: blur(0.2px);
      transform: rotate(-6deg);
      animation: talos-scan 2.8s cubic-bezier(.45,0,.2,1) infinite;
      z-index: 4;
    }

    .talos-loader__playhead {
      position: absolute;
      top: 0;
      bottom: 0;
      width: 1px;
      left: 50%;
      background: linear-gradient(180deg, transparent, rgba(244,224,77,0.84), transparent);
      box-shadow: 0 0 18px rgba(244,224,77,0.42);
      opacity: 0.74;
      z-index: 6;
      animation: talos-playhead 3.8s ease-in-out infinite;
    }

    .talos-loader__corner {
      position: absolute;
      width: 26px;
      height: 26px;
      z-index: 7;
      border-color: rgba(244, 224, 77, 0.86);
      filter: drop-shadow(0 0 8px rgba(244,224,77,0.24));
    }

    .talos-loader__corner--tl { top: 14px; left: 14px; border-top: 1px solid; border-left: 1px solid; }
    .talos-loader__corner--tr { top: 14px; right: 14px; border-top: 1px solid; border-right: 1px solid; }
    .talos-loader__corner--bl { bottom: 14px; left: 14px; border-bottom: 1px solid; border-left: 1px solid; }
    .talos-loader__corner--br { bottom: 14px; right: 14px; border-bottom: 1px solid; border-right: 1px solid; }

    .talos-loader__status {
      width: min(560px, 84vw);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 11px;
      letter-spacing: 0.18em;
      color: rgba(237,237,237,0.88);
      text-transform: uppercase;
    }

    .talos-loader__status strong {
      color: var(--talos-gold);
      font-weight: 700;
    }

    .talos-loader__timeline {
      position: relative;
      width: min(560px, 84vw);
      height: 54px;
      display: grid;
      grid-template-columns: 1.3fr 0.55fr 0.95fr 0.7fr 1.15fr;
      gap: 7px;
      align-items: center;
      padding: 0 1px;
    }

    .talos-loader__clip {
      position: relative;
      height: 26px;
      overflow: hidden;
      border: 1px solid rgba(244,224,77,0.18);
      border-radius: 4px;
      background:
        linear-gradient(90deg, rgba(244,224,77,0.32), rgba(255,255,255,0.09), rgba(244,224,77,0.14)),
        #0b0b0b;
      box-shadow: 0 0 18px rgba(244,224,77,0.055) inset;
    }

    .talos-loader__clip::after {
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(90deg, transparent, rgba(255,255,255,0.18), transparent);
      transform: translateX(-120%);
      animation: talos-clip-shine 2.9s ease-in-out infinite;
      animation-delay: inherit;
    }

    .talos-loader__timeline-head {
      position: absolute;
      top: 2px;
      bottom: 2px;
      width: 1px;
      left: 0;
      background: var(--talos-gold);
      box-shadow: 0 0 18px rgba(244,224,77,0.6);
      animation: talos-timeline-head 3.1s linear infinite;
    }

    .talos-loader__wave {
      width: min(360px, 74vw);
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
    }

    .talos-loader__bar {
      width: 3px;
      height: var(--h);
      min-height: 7px;
      border-radius: 999px;
      background: linear-gradient(180deg, rgba(244,224,77,0.95), rgba(244,224,77,0.16));
      opacity: 0.78;
      transform-origin: center;
      animation: talos-wave 1.05s ease-in-out infinite;
      animation-delay: var(--d);
    }

    .talos-loader__meter {
      position: fixed;
      right: 32px;
      bottom: 30px;
      z-index: 4;
      display: grid;
      gap: 6px;
      justify-items: end;
      font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 10px;
      letter-spacing: 0.24em;
      color: rgba(107,114,128,0.95);
      text-transform: uppercase;
    }

    .talos-loader__meter-line {
      width: 126px;
      height: 1px;
      overflow: hidden;
      background: rgba(255,255,255,0.08);
    }

    .talos-loader__meter-line::before {
      content: "";
      display: block;
      width: 38%;
      height: 100%;
      background: var(--talos-gold);
      box-shadow: 0 0 16px rgba(244,224,77,0.72);
      animation: talos-meter 1.7s ease-in-out infinite;
    }

    .talos-loader__flash {
      position: absolute;
      inset: -20%;
      z-index: 12;
      pointer-events: none;
      background: radial-gradient(circle at center, rgba(244,224,77,0.82), rgba(244,224,77,0.08) 24%, transparent 52%);
      opacity: 0;
      transform: scale(0.45);
    }

    @keyframes talos-strip-drift {
      0%, 100% { transform: translateX(-10%) skewX(-8deg); }
      50% { transform: translateX(10%) skewX(-8deg); }
    }

    @keyframes talos-subject-pulse {
      0%, 100% { opacity: 0.48; transform: scale(0.985); }
      50% { opacity: 0.72; transform: scale(1.015); }
    }

    @keyframes talos-scan {
      0% { transform: translateY(0) rotate(-6deg); opacity: 0; }
      12% { opacity: 1; }
      76% { opacity: 1; }
      100% { transform: translateY(620%) rotate(-6deg); opacity: 0; }
    }

    @keyframes talos-playhead {
      0%, 100% { transform: translateX(-74px); opacity: 0.35; }
      50% { transform: translateX(74px); opacity: 0.86; }
    }

    @keyframes talos-clip-shine {
      0%, 25% { transform: translateX(-120%); }
      70%, 100% { transform: translateX(120%); }
    }

    @keyframes talos-timeline-head {
      from { left: 0; }
      to { left: 100%; }
    }

    @keyframes talos-wave {
      0%, 100% { transform: scaleY(0.55); opacity: 0.38; }
      50% { transform: scaleY(1.18); opacity: 0.95; }
    }

    @keyframes talos-meter {
      0%, 100% { transform: translateX(-105%); }
      50% { transform: translateX(265%); }
    }

    @media (max-width: 640px) {
      .talos-loader__shell {
        padding-top: 88px;
      }

      .talos-loader__status {
        font-size: 9px;
        letter-spacing: 0.12em;
      }

      .talos-loader__meter {
        right: 20px;
        bottom: 20px;
      }
    }

    @media (prefers-reduced-motion: reduce) {
      .talos-loader *,
      .talos-loader *::before,
      .talos-loader *::after {
        animation-duration: 0.001ms !important;
        animation-iteration-count: 1 !important;
      }
    }
  `,document.head.appendChild(e)}function nn(){return[11,24,16,30,18,34,22,38,17,29,14,33,20,36,18,27,12,31,16,25,10,22].map((t,s)=>{const o=document.createElement("span");return o.className="talos-loader__bar",o.style.setProperty("--h",`${t}px`),o.style.setProperty("--d",`${s*-.055}s`),o})}function Fs(e){sn();const t=document.createElement("div");t.className="talos-loader",t.setAttribute("role","status"),t.setAttribute("aria-live","polite"),t.setAttribute("aria-label","Processing video");const s=document.createElement("div");s.className="talos-loader__shell";const o=document.createElement("div");o.className="talos-loader__system";const n=document.createElement("div");n.className="talos-loader__preview";for(let B=0;B<6;B++){const A=document.createElement("span");A.className="talos-loader__strip",n.appendChild(A)}const r=document.createElement("span");r.className="talos-loader__subject";const i=document.createElement("span");i.className="talos-loader__scan";const d=document.createElement("span");d.className="talos-loader__playhead",n.append(r,i,d),["tl","tr","bl","br"].forEach(B=>{const A=document.createElement("span");A.className=`talos-loader__corner talos-loader__corner--${B}`,n.appendChild(A)});const p=document.createElement("div");p.className="talos-loader__status",p.innerHTML="<span>Rendering <strong>cut</strong></span><span>AI pass 04</span>";const l=document.createElement("div");l.className="talos-loader__timeline";for(let B=0;B<5;B++){const A=document.createElement("span");A.className="talos-loader__clip",A.style.animationDelay=`${B*.18}s`,l.appendChild(A)}const m=document.createElement("span");m.className="talos-loader__timeline-head",l.appendChild(m);const h=document.createElement("div");h.className="talos-loader__wave",nn().forEach(B=>h.appendChild(B)),o.append(n,p,l,h),s.appendChild(o);const v=document.createElement("div");v.className="talos-loader__meter",v.innerHTML='<span>Compositing</span><span class="talos-loader__meter-line"></span>';const _=document.createElement("span");_.className="talos-loader__flash",t.append(s,v,_),e.appendChild(t);const w=Ge(o,{opacity:[0,1],translateY:[18,0],scale:[.98,1],duration:720,ease:"easeOutCubic"}),T=Ge(n,{boxShadow:["0 0 0 1px rgba(255,255,255,0.045) inset, 0 24px 90px rgba(0,0,0,0.74), 0 0 54px rgba(244,224,77,0.09)","0 0 0 1px rgba(255,255,255,0.065) inset, 0 24px 90px rgba(0,0,0,0.74), 0 0 92px rgba(244,224,77,0.19)","0 0 0 1px rgba(255,255,255,0.045) inset, 0 24px 90px rgba(0,0,0,0.74), 0 0 54px rgba(244,224,77,0.09)"],duration:2600,loop:!0,ease:"easeInOutSine"}),V={finished:!1},ce={root:t,complete(){V.finished||(V.finished=!0,w.pause(),T.pause(),Ge(_,{opacity:[0,.65,0],scale:[.45,1.35],duration:620,ease:"easeOutExpo"}),Ge(o,{opacity:[1,0],translateY:[0,-18],scale:[1,1.03],duration:420,ease:"easeInCubic"}),Ge(t,{opacity:[1,0],duration:560,delay:220,ease:"easeOutCubic",onComplete:()=>ce.destroy()}))},destroy(){w&&w.pause(),T&&T.pause(),t&&t.parentNode&&t.parentNode.removeChild(t)}};return ce}function Ms(e,t="compact"){sn();const s=t==="compact"?80:120,o=document.createElement("div");o.style.cssText=[`width:${s}px`,`height:${s}px`,"position:relative","display:grid","place-items:center"].join(";");const n=document.createElement("div");n.style.cssText=[`width:${Math.round(s*.62)}px`,`height:${Math.round(s*.62)}px`,"border-radius:8px","border:1px solid rgba(244,224,77,0.34)","background:linear-gradient(135deg, rgba(244,224,77,0.16), rgba(255,255,255,0.03))","box-shadow:0 0 32px rgba(244,224,77,0.12)"].join(";");const r=document.createElement("span");r.style.cssText=["position:absolute","inset:0","border-radius:50%","border:1px solid rgba(244,224,77,0.16)","border-top-color:#f4e04d","filter:drop-shadow(0 0 10px rgba(244,224,77,0.35))"].join(";");const i=document.createElement("div");i.style.cssText=["position:absolute","display:flex","align-items:center","gap:3px"].join(";"),nn().slice(4,14).forEach(l=>i.appendChild(l)),o.append(n,r,i),e.appendChild(o);const d=Ge(r,{rotate:360,duration:1200,loop:!0,ease:"linear"}),p=Ge(n,{scale:[.96,1.04,.96],duration:1600,loop:!0,ease:"easeInOutSine"});return{svg:o,anim:{pause(){d.pause(),p.pause()}}}}function rs(e){if(e){if(e.destroy){e.destroy();return}e.anim&&e.anim.pause(),e.svg&&e.svg.parentNode&&e.svg.parentNode.removeChild(e.svg)}}document.addEventListener("DOMContentLoaded",()=>{const e=document.getElementById("file-input"),t=document.getElementById("upload-container"),s=document.getElementById("processing-container"),o=document.getElementById("processing-loader"),n=document.getElementById("audio-initial-loader"),r=document.getElementById("progress-bar"),i=document.getElementById("progress-text"),d=document.getElementById("bill-popup"),p=document.getElementById("bill-popup-content"),l=document.getElementById("close-popup"),m=document.getElementById("popup-action-btn"),h=document.getElementById("distortion-controls"),v=document.getElementById("toggle-controls"),_=document.getElementById("controls-content"),w=document.getElementById("controls-chevron"),T=document.getElementById("cipher-triangle-btn"),V=document.getElementById("result-container"),ce=document.getElementById("result-video"),B=document.getElementById("download-btn"),A=document.getElementById("reset-btn"),H=document.getElementById("caption-overlay"),Z=document.getElementById("prompt-search"),E=document.getElementById("error-text");let K="sleek",q=null,Y=null,ke="",Ne="Make this video engaging for social media",W=null,Oe=null,Fe="tiktok",O="short",P="9:16",we="1080x1920",_e=0,y=!1,I=null,j=null,de="fit_blur";const ue={active:["active","border-[#F4E04D]","bg-[#F4E04D]/10","text-[#F4E04D]"],inactive:["border-[#333]","text-gray-400"]},Q=document.getElementById("add-music-toggle"),X=document.getElementById("music-options"),D=document.getElementById("music-select"),U=document.getElementById("selected-music-name"),pe=document.getElementById("music-upload"),te=document.getElementById("music-volume"),ve=document.getElementById("volume-display");lucide.createIcons(),C(),ee(),cn(),_s();let se=null;if(n){Ms(n,"compact");const a=document.createElement("p");a.className="text-gray-400 font-bold text-sm uppercase tracking-widest",a.textContent="Waking up the library...",n.appendChild(a)}const Be={active:["active","bg-[color:var(--text-primary)]","text-black"],inactive:["text-[color:var(--text-secondary)]","hover:text-white"]};document.querySelectorAll(".platform-btn").forEach(a=>{a.addEventListener("click",()=>{document.querySelectorAll(".platform-btn").forEach(f=>{f.classList.remove(...Be.active),f.classList.add(...Be.inactive)}),a.classList.remove(...Be.inactive),a.classList.add(...Be.active),Fe=a.dataset.platform,P=a.dataset.aspect,we=a.dataset.res;const c=document.getElementById("platform-aspect-meta");c&&(c.textContent=`${P} · ${we.replace("x","×")}`)})}),document.querySelectorAll(".format-btn").forEach(a=>{a.addEventListener("click",()=>{document.querySelectorAll(".format-btn").forEach(f=>{f.classList.remove("active","bg-[color:var(--text-primary)]","text-black"),f.classList.add("text-[color:var(--text-secondary)]","hover:text-white")}),a.classList.remove("text-[color:var(--text-secondary)]","hover:text-white"),a.classList.add("active","bg-[color:var(--text-primary)]","text-black"),O=a.dataset.format;const c=document.getElementById("format-hint");c&&(c.textContent=O==="short"?"Optimized for ≤60s clips":"Full-length video export")})});const xe=document.getElementById("toggle-advanced"),Ie=document.getElementById("advanced-content"),Te=document.getElementById("advanced-chevron");xe&&Ie&&xe.addEventListener("click",()=>{Ie.classList.toggle("hidden"),Te&&(Te.style.transform=Ie.classList.contains("hidden")?"rotate(0deg)":"rotate(180deg)"),lucide.createIcons()});const J=document.getElementById("btn-rotate"),ne=document.getElementById("rotation-indicator");J&&J.addEventListener("click",()=>{_e=(_e+90)%360,_e===0?(ne==null||ne.classList.add("hidden"),J.classList.remove("border-[#F4E04D]","text-[#F4E04D]","bg-[#F4E04D]/10"),J.classList.add("border-[#333]","text-gray-400","bg-[#111]")):(ne&&(ne.classList.remove("hidden"),ne.textContent=_e+"°"),J.classList.remove("border-[#333]","text-gray-400","bg-[#111]"),J.classList.add("border-[#F4E04D]","text-[#F4E04D]","bg-[#F4E04D]/10"))});const oe=document.getElementById("btn-flip"),ye=document.getElementById("flip-indicator");oe&&oe.addEventListener("click",()=>{y=!y,y?(ye==null||ye.classList.remove("hidden"),oe.classList.remove("border-[#333]","text-gray-400","bg-[#111]"),oe.classList.add("border-[#F4E04D]","text-[#F4E04D]","bg-[#F4E04D]/10")):(ye==null||ye.classList.add("hidden"),oe.classList.remove("border-[#F4E04D]","text-[#F4E04D]","bg-[#F4E04D]/10"),oe.classList.add("border-[#333]","text-gray-400","bg-[#111]"))});const M=document.getElementById("btn-crop"),me=document.getElementById("crop-presets");M&&me&&M.addEventListener("click",()=>{var a;me.classList.toggle("hidden"),(a=document.getElementById("custom-aspect-input"))==null||a.classList.add("hidden")}),document.querySelectorAll(".crop-preset-btn").forEach(a=>{a.addEventListener("click",()=>{document.querySelectorAll(".crop-preset-btn").forEach(c=>{c.classList.remove("border-[#F4E04D]","bg-[#F4E04D]/10","text-[#F4E04D]"),c.classList.add("border-[#333]","text-gray-400")}),a.classList.remove("border-[#333]","text-gray-400"),a.classList.add("border-[#F4E04D]","bg-[#F4E04D]/10","text-[#F4E04D]"),j=a.dataset.crop,j==="auto"&&(j=P)})}),document.querySelectorAll(".framing-mode-btn").forEach(a=>{a.addEventListener("click",()=>{document.querySelectorAll(".framing-mode-btn").forEach(c=>{c.classList.remove("border-[#F4E04D]","bg-[#F4E04D]/10","text-[#F4E04D]"),c.classList.add("border-[#333]","text-gray-400")}),a.classList.remove("border-[#333]","text-gray-400"),a.classList.add("border-[#F4E04D]","bg-[#F4E04D]/10","text-[#F4E04D]"),de=a.dataset.framingMode||"fit_blur"})});const k=document.getElementById("btn-custom-aspect"),Ke=document.getElementById("custom-aspect-input");k&&Ke&&k.addEventListener("click",()=>{Ke.classList.toggle("hidden"),me==null||me.classList.add("hidden")});const gt=document.getElementById("apply-aspect");gt&&gt.addEventListener("click",()=>{var f,u;const a=parseInt(((f=document.getElementById("aspect-w"))==null?void 0:f.value)||"9"),c=parseInt(((u=document.getElementById("aspect-h"))==null?void 0:u.value)||"16");a>0&&c>0&&(I={w:a,h:c},k==null||k.classList.remove("border-[#333]","text-gray-400","bg-[#111]"),k==null||k.classList.add("border-[#F4E04D]","text-[#F4E04D]","bg-[#F4E04D]/10"))});const Qe=document.getElementById("reset-aspect");Qe&&Qe.addEventListener("click",()=>{I=null;const a=document.getElementById("aspect-w"),c=document.getElementById("aspect-h");a&&(a.value="9"),c&&(c.value="16"),k==null||k.classList.remove("border-[#F4E04D]","text-[#F4E04D]","bg-[#F4E04D]/10"),k==null||k.classList.add("border-[#333]","text-gray-400","bg-[#111]")}),v&&v.addEventListener("click",()=>{_.classList.toggle("hidden"),_.classList.contains("hidden")?w&&(w.style.transform="rotate(0deg)"):w&&(w.style.transform="rotate(180deg)")}),document.querySelectorAll(".style-btn").forEach(a=>{a.addEventListener("click",()=>nt(a.dataset.style))}),T&&T.addEventListener("click",()=>{Rt(!1)}),l&&l.addEventListener("click",re),m&&m.addEventListener("click",re),A&&A.addEventListener("click",()=>{location.reload()}),console.log("Music elements check:",{toggle:!!Q,options:!!X,select:!!D}),Q?Q.addEventListener("change",()=>{console.log("Music toggle clicked, checked:",Q.checked),X&&(Q.checked?(X.classList.remove("hidden"),et()):X.classList.add("hidden"))}):console.warn("addMusicToggle element not found!"),te&&ve&&te.addEventListener("input",()=>{ve.textContent=te.value+"%"}),D&&D.addEventListener("change",async()=>{W=D.value||null,W&&Oe&&console.log("Loading waveform for",W)});const Le=document.getElementById("preview-audio-edit-btn");Le&&Le.addEventListener("click",async()=>{if(!Y||!W){alert("Please upload a video and select music first.");return}const a=Le.innerText;Le.innerText="⏳ GENERATING...",Le.disabled=!0;try{const f=await(await fetch("/api/preview",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({video_id:Y,audio_track_id:W,volume_level:parseInt((te==null?void 0:te.value)||30)/100})})).json();if(f.success&&f.output_path){const u=`/api/download/${f.output_path.split("/").pop()}`;window.open(u,"_blank","width=480,height=854")}else alert("Preview failed: "+(f.error||"Unknown"))}catch(c){console.error(c),alert("Preview error")}finally{Le.innerText=a,Le.disabled=!1}}),pe&&pe.addEventListener("change",async a=>{if(a.target.files&&a.target.files[0]){const c=a.target.files[0],f=new FormData;f.append("file",c);try{const g=await(await fetch("/api/music/upload",{method:"POST",body:f})).json();g.success&&(await et(),D.value=g.track_id,W=g.track_id,U&&(U.innerText=c.name),alert("Music uploaded successfully!"))}catch(u){console.error("Music upload failed:",u)}}});async function et(){try{const c=await(await fetch("/api/music")).json();D&&(D.innerHTML='<option value="">-- No music selected --</option>',(c.tracks||c.music||[]).forEach(u=>{const g=document.createElement("option");g.value=u.id||u.filename||u.track_id,g.textContent=u.title||u.name||u.filename,D.appendChild(g)}))}catch(a){console.error("Failed to load music:",a)}}e&&e.addEventListener("change",async a=>{if(a.target.files&&a.target.files[0]){const c=a.target.files[0];if(!await bt()){E&&(E.classList.remove("hidden"),E.innerText="Error: backend is not reachable (check server on port 8000).");return}t.classList.add("hidden"),h.classList.add("hidden");const u=document.getElementById("platform-format-selector");u&&u.classList.add("hidden"),s.classList.remove("hidden"),o&&(se=Fs(o)),E&&(E.classList.add("hidden"),E.innerText="");try{const g=new FormData;g.append("file",c);const N=await(await fetch("/api/upload",{method:"POST",body:g})).json();if(!N.success)throw new Error(N.message);const fe=N.video_id;Y=fe,Ae(20,"UPLOADING REALITY...");const Re=document.getElementById("trim-toggle").checked,xt=document.getElementById("burn-subs-toggle").checked,Pt=((Z==null?void 0:Z.value)||"").trim();Ne=Pt||Ne;const $e=await(await fetch("/api/process",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({video_id:fe,style_preset:K,add_subtitles:xt,trim_boring_parts:Re,user_prompt:Pt||void 0,platform:Fe,format:O,aspect_ratio:P,resolution:we})})).json();if(!$e.success)throw new Error($e.message);je(fe)}catch(g){console.error(g),E?(E.classList.remove("hidden"),E.innerText=`Error: ${g.message}`):(alert("CHAOS ERROR: "+g.message),location.reload())}}}),ce&&ce.addEventListener("timeupdate",()=>{q&&Ee(ce.currentTime)});function Ae(a,c){r&&(r.style.width=`${a}%`),i&&c&&(i.innerText=c)}const Bt=document.getElementById("review-container"),tt=document.getElementById("review-summary"),qe=document.getElementById("review-cuts"),st=document.getElementById("review-transcript"),_t=document.getElementById("confirm-render-btn");document.querySelectorAll(".review-style-btn").forEach(a=>{a.addEventListener("click",()=>{K=(a.dataset.style||"sleek").toLowerCase(),document.querySelectorAll(".review-style-btn").forEach(c=>{c.classList.remove(...ue.active),c.classList.add(...ue.inactive),c.dataset.style===K&&(c.classList.add(...ue.active),c.classList.remove(...ue.inactive))})})});async function je(a){let c=0;const f=60,u=setInterval(async()=>{try{if(c++,c>f){clearInterval(u),Me("Processing timed out. Please try again.");return}const g=await fetch(`/api/download/status/${a}`);if(!g.ok){clearInterval(u),Me(`Processing failed: server returned ${g.status}`);return}const S=await g.json();if(S.status==="analyzed")clearInterval(u),Ae(50,"ANALYSIS COMPLETE"),rs(se),s.classList.add("hidden"),Bt.classList.remove("hidden"),Gt(a);else if(S.status==="completed")clearInterval(u),Ae(100,"REALITY ALTERED"),yt(S);else if(S.status==="error")clearInterval(u),Me(`Processing failed: ${S.error||"Unknown error"}`);else if(S.status==="not_found")Ae(10,"STARTING...");else{const N=S.progress||0,fe=(S.status||"processing").toString().replace(/_/g," ").toUpperCase();Ae(N,`${fe}...`)}}catch(g){console.error(g),clearInterval(u),Me(`Status check failed: ${g.message}`)}},1e3)}async function Gt(a){var S,N;const c=document.getElementById("review-platform-label"),f=document.getElementById("review-aspect-label"),u=document.getElementById("review-format-label"),g=document.getElementById("review-framing-label");c&&(c.textContent=Fe.toUpperCase().replace("-"," ")),f&&(f.textContent=I?`${I.w}:${I.h}`:P),u&&(u.textContent=O.toUpperCase()),g&&(g.textContent=de==="smart_crop"?"SMART CROP":"FIT + BLUR"),lucide.createIcons();try{const Re=await(await fetch(`/api/analysis/${a}`)).json(),xt=Re.ai_analysis.overall_score||5,Pt=xt>=7?"#22c55e":xt>=5?"#eab308":"#ef4444";tt.innerHTML=`
                <div class="flex items-center gap-3 mb-2">
                    <span class="text-2xl font-bold" style="color: ${Pt}">${xt}/10</span>
                    <span class="text-gray-400 text-sm">Viewer Retention Score</span>
                </div>
                <p class="text-gray-300">${Re.ai_analysis.summary||"No summary available."}</p>
            `,st.value=Re.transcript||"",ke=Re.transcript||"",qe.innerHTML="";const Zt=Re.ai_analysis.suggested_cuts||[];if(Zt.length===0)qe.innerHTML='<p class="text-green-500 text-sm">✅ Video looks great! No boring segments detected.</p>';else{const $e=document.createElement("p");$e.className="text-xs text-gray-500 mb-2",$e.innerText="Check segments you want to REMOVE:",qe.appendChild($e),Zt.forEach((Xe,ys)=>{const Ot=Xe.retention_score||5,dn=Ot>=7?"#22c55e":Ot>=5?"#eab308":"#ef4444",Ft=(Xe.recommendation||(Ot<=4?"cut":"keep"))==="cut",Ue=document.createElement("div");Ue.className=`flex items-start gap-3 p-3 rounded border ${Ft?"bg-red-950/30 border-red-800":"bg-[#0a0a0a] border-[#222]"}`,Ue.innerHTML=`
                        <input type="checkbox" id="cut-${ys}" class="cut-checkbox mt-1 w-5 h-5 cursor-pointer" 
                            data-start="${Xe.start}" data-end="${Xe.end}" ${Ft?"checked":""}>
                        <div class="flex-1">
                            <div class="flex items-center gap-2 mb-1">
                                <span class="font-bold" style="color: ${dn}">${Ot}/10</span>
                                <label for="cut-${ys}" class="text-sm font-semibold text-white cursor-pointer">
                                    ${Xe.start}s - ${Xe.end}s
                                </label>
                                <span class="text-xs px-2 py-0.5 rounded ${Ft?"bg-red-800 text-red-200":"bg-green-800 text-green-200"}">
                                    ${Ft?"CUT":"KEEP"}
                                </span>
                            </div>
                            <p class="text-xs text-gray-400">${Xe.reason||Xe.description||"No reason provided"}</p>
                        </div>
                    `;const bs=Ue.querySelector("input");bs.addEventListener("change",()=>{const Mt=Ue.querySelector("span:last-of-type");bs.checked?(Ue.classList.remove("bg-[#0a0a0a]","border-[#222]"),Ue.classList.add("bg-red-950/30","border-red-800"),Mt.className="text-xs px-2 py-0.5 rounded bg-red-800 text-red-200",Mt.innerText="CUT"):(Ue.classList.remove("bg-red-950/30","border-red-800"),Ue.classList.add("bg-[#0a0a0a]","border-[#222]"),Mt.className="text-xs px-2 py-0.5 rounded bg-green-800 text-green-200",Mt.innerText="KEEP")}),qe.appendChild(Ue)})}if(window.currentVideoDuration=((S=Re.phase_one_metadata)==null?void 0:S.duration)||((N=Re.analysis)==null?void 0:N.duration)||0,Re.ai_suggested_music){const $e=Re.ai_suggested_music;W=$e.id,U&&(U.innerText=`AI PICKED: ${$e.title}`),Q&&(Q.checked=!0),X&&X.classList.remove("hidden")}}catch(fe){console.error(fe),tt.innerText="Error loading analysis."}}function Me(a){rs(se),E&&(E.classList.remove("hidden"),E.innerText=a),Ae(100,"ERROR")}function yt(a){E&&E.classList.add("hidden"),a.captions_url&&fetch(a.captions_url).then(c=>c.json()).then(c=>{q=c,q!=null&&q.stylePreset&&nt(q.stylePreset)}).catch(c=>console.error(c)),setTimeout(()=>{rs(se),s.classList.add("hidden"),V.classList.remove("hidden"),ce.src=a.output_url,B.href=`/api/download/${a.output_url.split("/").pop()}`,ce.play().catch(c=>console.log("Auto-play prevented"))},500)}_t&&(_t.onclick=async()=>{if(!Y)return;const a=[];document.querySelectorAll(".cut-checkbox:checked").forEach(N=>{a.push({start:parseFloat(N.dataset.start),end:parseFloat(N.dataset.end)})});const c=window.currentVideoDuration||99999;a.sort((N,fe)=>N.start-fe.start);const f=[];let u=0;a.forEach(N=>{N.start>u&&f.push({start:u,end:N.start}),u=Math.max(u,N.end)}),u<c&&f.push({start:u,end:c});const g=a.length>0?f:[];st.value;const S=document.getElementById("burn-subs-toggle").checked;console.log("burnSubs toggle value:",S,document.getElementById("burn-subs-toggle")),Bt.classList.add("hidden"),s.classList.remove("hidden"),o&&(se=Fs(o)),Ae(50,"RENDERING REALITY..."),je(Y);try{const fe=await(await fetch("/api/render",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({video_id:Y,custom_segments:g,style_preset:K,add_subtitles:S,add_music:Q?Q.checked:!1,music_file:W,music_volume:te?parseInt(te.value,10)/100:.3,platform:Fe,format:O,aspect_ratio:I?`${I.w}:${I.h}`:j||P,resolution:we,rotation:_e,flip_horizontal:y,framing_mode:de})})).json();if(!fe.success)throw new Error(fe.message)}catch(N){console.error(N),Me(N.message)}});function Ee(a){if(!H||!q||!q.captions)return;const c=(q.stylePreset||K||"sleek").toLowerCase(),f=q.captions.find(u=>a>=u.start&&a<=u.end);if(H.innerHTML="",f){const u=document.createElement("div");u.className=`caption-line style-${c}`,u.style.position="absolute",u.style.bottom="10%",u.style.textAlign="center",u.style.width="100%",u.style.pointerEvents="none",u.style.textShadow="0 2px 4px rgba(0,0,0,0.8)",c==="sleek"?(u.style.fontFamily="'Inter', sans-serif",u.style.fontWeight="800",u.style.fontSize="24px",u.style.color="white"):c==="minimal"?(u.style.fontFamily="'JetBrains Mono', monospace",u.style.fontSize="18px",u.style.background="rgba(0,0,0,0.7)",u.style.padding="4px 8px",u.style.borderRadius="4px"):c==="meme"?(u.style.fontFamily="Impact, sans-serif",u.style.fontSize="32px",u.style.color="white",u.style.webkitTextStroke="2px black",u.style.textTransform="uppercase"):c==="neon"&&(u.style.fontFamily="'Courier New', monospace",u.style.fontSize="24px",u.style.color="#F4E04D",u.style.textShadow="0 0 10px #F4E04D");const g=Array.isArray(f.words)?f.words:[];g.length>0&&g.forEach(S=>{const N=document.createElement("span");N.textContent=(S.text||S.word||"")+" ",a>=S.start&&a<=S.end?(N.style.opacity="1",c==="sleek"&&(N.style.color="#F4E04D")):N.style.opacity=c==="minimal"?"0.5":"1",u.appendChild(N)}),u.innerHTML||(u.textContent=f.text),H.appendChild(u)}}function nt(a){K=(a||"sleek").toLowerCase(),document.querySelectorAll(".style-btn").forEach(c=>{c.classList.remove(...ue.active),c.classList.add(...ue.inactive),c.dataset.style===K&&(c.classList.add(...ue.active),c.classList.remove(...ue.inactive))})}function Rt(a=!1,c=null){d.classList.remove("hidden");const f=d.querySelector("h2"),u=d.querySelector("p"),g=document.getElementById("popup-action-btn");a?(f.innerText="REALITY IS AN ILLUSION!",u.innerText="Your video has been processed. The universe is a hologram. Buy gold!",g&&(g.innerText="CLOSE")):(f.innerText="I'M WATCHING YOU!",u.innerText="Remember: trust no one! Not even your video editor!",g&&(g.innerText="CLOSE")),setTimeout(()=>{d.classList.remove("opacity-0"),p.classList.remove("scale-90","opacity-0","translate-y-10"),p.classList.add("scale-100","opacity-100","translate-y-0")},50)}function re(){d.classList.add("opacity-0"),p.classList.remove("scale-100","opacity-100","translate-y-0"),p.classList.add("scale-90","opacity-0","translate-y-10"),setTimeout(()=>{d.classList.add("hidden")},300)}async function bt(){try{return(await fetch("/api",{method:"GET"})).ok}catch(a){return console.error("Health check failed",a),!1}}function C(){const a="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+";function c(f){const u=f.getAttribute("data-text");let g=0,S=null;clearInterval(f.dataset.intervalId),S=setInterval(()=>{f.innerText=u.split("").map((N,fe)=>fe<g?u[fe]:a[Math.floor(Math.random()*a.length)]).join(""),g>=u.length&&clearInterval(S),g+=1/3},30),f.dataset.intervalId=S}document.querySelectorAll(".glitch-text").forEach(f=>{c(f),setInterval(()=>{Math.random()>.9&&c(f)},5e3)})}function ee(){const a=document.getElementById("bill-bg"),c=document.getElementById("bill-eye-bg");t&&a&&(t.addEventListener("mouseenter",()=>{a.classList.remove("opacity-0"),a.classList.add("opacity-100")}),t.addEventListener("mouseleave",()=>{a.classList.remove("opacity-100"),a.classList.add("opacity-0")})),window.addEventListener("mousemove",f=>{const u=f.clientX/window.innerWidth*20-10,g=f.clientY/window.innerHeight*20-10;c&&(c.style.transform=`translate(calc(-50% + ${u}px), calc(-50% + ${g}px))`)})}const Dt=document.getElementById("audio-library-modal"),vt=document.getElementById("open-audio-library"),fs=document.getElementById("close-audio-library"),ot=document.getElementById("audio-list-container"),rt=document.getElementById("music-search-input"),hs=document.getElementById("music-search-btn"),on=document.getElementById("playing-track-indicator");document.getElementById("playing-track-name");const gs=document.getElementById("stop-preview");vt&&vt.addEventListener("click",a=>{a.preventDefault(),Dt.classList.remove("hidden"),rn()}),fs&&fs.addEventListener("click",()=>{Dt.classList.add("hidden")}),hs&&hs.addEventListener("click",()=>At(rt.value)),rt&&rt.addEventListener("keypress",a=>{a.key==="Enter"&&At(rt.value)}),document.querySelectorAll(".playlist-card").forEach(a=>{a.addEventListener("click",()=>{const c=a.dataset.query;rt&&(rt.value=c),At(c)})});async function rn(){const a=((Z==null?void 0:Z.value)||"").trim();At(a||"trending tiktok viral")}async function At(a){if(!a)return;ot.innerHTML=`
            <tr>
                <td colspan="6" class="py-20 text-center">
                    <div id="music-search-loader" class="flex flex-col items-center gap-4"></div>
                </td>
            </tr>
        `;const c=document.getElementById("music-search-loader");if(c){Ms(c,"compact");const f=document.createElement("p");f.className="text-gray-400 font-bold text-sm uppercase tracking-widest",f.textContent="Searching the sound waves...",c.appendChild(f)}try{const u=await(await fetch("/api/music/agent/recommend",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({prompt:a,video_id:Y})})).json();u.success&&u.tracks.length>0?an(u.tracks):ot.innerHTML=`<tr><td colspan="6" class="py-20 text-center text-gray-500 font-bold">No tracks found for "${a}"</td></tr>`}catch(f){console.error("Search failed:",f),ot.innerHTML='<tr><td colspan="6" class="py-20 text-center text-red-500 font-bold">Error searching music</td></tr>'}}function an(a){ot.innerHTML="",a.forEach(c=>{const f=document.createElement("tr");f.className="p-4 border-b border-gray-50 hover:bg-gray-50 transition-colors group";const u=Math.floor(c.duration/60),g=Math.floor(c.duration%60).toString().padStart(2,"0"),S=`${u}:${g}`;f.innerHTML=`
                <td class="px-4 py-4">
                    <div class="flex items-center gap-4">
                        <div class="relative w-12 h-12 rounded bg-black flex-shrink-0 overflow-hidden">
                            <img src="${c.thumbnail_url||"https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=100&h=100&fit=crop"}" class="w-full h-full object-cover">
                        </div>
                        <div class="flex flex-col">
                            <span class="font-bold text-sm line-clamp-1">${c.title}</span>
                            <span class="text-xs font-bold text-red-500 uppercase tracking-tighter mt-1 group-hover:block transition-all">Use in Project Editor</span>
                        </div>
                    </div>
                </td>
                <td class="px-4 py-4"></td>
                <td class="px-4 py-4 text-sm font-bold text-gray-400">${c.artist}</td>
                <td class="px-4 py-4 text-sm font-bold text-gray-500">${S}</td>
                <td class="px-4 py-4">
                    <div class="flex gap-2">
                        <i data-lucide="video" class="w-4 h-4 text-gray-400"></i>
                        <i data-lucide="music" class="w-4 h-4 text-gray-400"></i>
                    </div>
                </td>
                <td class="px-4 py-4 text-right">
                    <button class="use-music-btn bg-black text-white px-5 py-2 rounded-full text-xs font-bold hover:bg-gray-800 transition-colors" data-id="${c.id}" data-title="${c.title}">
                        USE
                    </button>
                </td>
            `,f.querySelector(".use-music-btn").addEventListener("click",()=>{ln(c)}),ot.appendChild(f)}),lucide.createIcons()}async function ln(a){const c=a.id,f=ot.querySelector(`button[data-id="${c}"]`),u=f.innerText;f.innerText="SELECTING...",f.disabled=!0;try{const S=await(await fetch("/api/music/agent/select",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({track_id:c,video_id:Y})})).json();S.success&&(await et(),D&&(D.value=S.filename,W=S.filename,U&&(U.innerText=a.title||S.filename)),Q&&(Q.checked=!0),X&&X.classList.remove("hidden"),Dt.classList.add("hidden"),console.log("Selected track:",S.filename))}catch(g){console.error("Selection failed:",g),f.innerText="ERROR",setTimeout(()=>{f.innerText=u,f.disabled=!1},2e3)}}gs&&gs.addEventListener("click",()=>{on.classList.add("hidden")});function cn(){if(document.getElementById("timeline-container"))try{Oe=WaveSurfer.create({container:"#timeline-container",waveColor:"#4b5563",progressColor:"#F4E04D",cursorColor:"#F4E04D",barWidth:2,barRadius:3,cursorWidth:1,height:80,barGap:3})}catch(a){console.warn("Wavesurfer init failed",a)}}function _s(){const c=`${window.location.protocol==="https:"?"wss":"ws"}://${window.location.host}/ws/progress`;try{const f=new WebSocket(c);f.onopen=()=>{console.log("🔌 Progress WebSocket connected")},f.onmessage=u=>{try{const g=JSON.parse(u.data);g.video_id===Y&&Ae(g.progress,g.message)}catch(g){console.warn("WS message parse error",g)}},f.onclose=()=>{console.log("🔌 Progress WebSocket closed, reconnecting in 5s..."),setTimeout(_s,5e3)},f.onerror=u=>{console.warn("WebSocket error:",u)}}catch(f){console.warn("WebSocket init failed:",f)}}});
