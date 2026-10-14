(function(){
const store = window.__store = {};
const rid=()=>Math.random().toString(36).slice(2,12);
const clone=o=>o===undefined?o:JSON.parse(JSON.stringify(o));
const DEL = {__del:true};
const listeners=new Set();
function notify(){ setTimeout(()=>{ listeners.forEach(l=>l.q.get().then(l.cb)); },0); }
function applyUpd(old,upd){const n={...old};for(const k in upd){ if(upd[k]&&upd[k].__del) delete n[k]; else n[k]=clone(upd[k]); }return n;}
function colRef(path){return {
  doc(id){return docRef(path+'/'+(id||rid()));},
  where(f,op,v){return query(path).where(f,op,v);},
  orderBy(f,d){return query(path).orderBy(f,d);},
  get(){return query(path).get();},
  onSnapshot(cb,err){return query(path).onSnapshot(cb,err);}
};}
function docRef(path){const parts=path.split('/');return {id:parts[parts.length-1],path,
  collection(n){return colRef(path+'/'+n);},
  async get(){const d=store[path];return {exists:d!==undefined,id:this.id,data:()=>clone(d)};},
  async set(data,opt){store[path]=clone(data);notify();},
  async update(upd){if(store[path]===undefined) throw new Error('not-found '+path);store[path]=applyUpd(store[path],upd);notify();},
  async delete(){delete store[path];notify();}
};}
function query(path,filters=[],order=null,dir='asc'){return {
  where(f,op,v){return query(path,[...filters,[f,op,v]],order,dir);},
  orderBy(f,d){return query(path,filters,f,d||'asc');},
  onSnapshot(cb,err){const l={q:this,cb};listeners.add(l);setTimeout(()=>this.get().then(cb),0);return()=>listeners.delete(l);},
  async get(){
    const depth=path.split('/').length+1;
    let docs=Object.keys(store).filter(p=>p.startsWith(path+'/')&&p.split('/').length===depth).map(p=>({id:p.split('/').pop(),data:()=>clone(store[p]),_d:store[p]}));
    for(const [f,op,v] of filters){docs=docs.filter(d=>{const x=d._d[f];if(x===undefined)return false;return op=='=='?x===v:op=='>'?x>v:op=='>='?x>=v:op=='<'?x<v:x<=v;});}
    if(order){docs.sort((a,b)=>{const x=a._d[order],y=b._d[order];if(x===y)return a.id<b.id?-1:1;return (x<y?-1:1)*(dir==='desc'?-1:1);});}
    else docs.sort((a,b)=>a.id<b.id?-1:1);
    return {docs,empty:!docs.length,size:docs.length,forEach:f=>docs.forEach(f)};
  }};}
const fs={enablePersistence:async()=>{},waitForPendingWrites:async()=>{},runTransaction:async f=>f({get:r=>r.get(),set:(r,d,o)=>r.set(o&&o.merge?{...(store[r.path]||{}),...d}:d)}),collection:n=>colRef(n),batch(){const ops=[];return{
  set(r,d){ops.push(()=>r.set(d));return this;},update(r,d){ops.push(()=>r.update(d));return this;},delete(r){ops.push(()=>r.delete());return this;},
  async commit(){for(const o of ops) await o();}};}};
let cb=null;const user={uid:'u1',email:window.__EMAIL||'fede@x.com'};
const auth={currentUser:null,onAuthStateChanged(f){cb=f;setTimeout(()=>{auth.currentUser=user;f(user);},50);return()=>{};},
  signInWithEmailAndPassword:async()=>{},signOut:async()=>{}};
store['usuarios/u1']={rol:window.__ROLE||'admin',nombre:window.__NOMBRE||'Fede'};
store['clientas/c1']={nombre:'Lola',apellido:'Arana',telefono:'1111',dni:'14524331',direccion:'',createdAt:1,deudaARS:0,deudaUSD:0};
store['clientas/c2']={nombre:'Carola',apellido:'Cosentino',telefono:'2222',dni:'25189538',direccion:'',createdAt:2,deudaARS:0,deudaUSD:0};
window.firebase={initializeApp(){},auth:()=>auth,firestore:Object.assign(()=>fs,{FieldValue:{delete:()=>DEL}})};
})();
