/* HBJ Novo — service worker (funciona 100% offline após o 1º acesso)
   Ao publicar mudança em hinos.json ou index.html, troque a VERSAO. */
var VERSAO = "hbj-2026-10-14-1";
var SHELL = [
  "./",
  "./index.html",
  "./hinos.json",
  "./manifest.webmanifest",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/icon-512-maskable.png",
  "./icons/apple-touch-icon.png",
  "./icons/favicon.png",
  "./icons/logo-circulo.png",
  "./icons/logo-promessa.png",
  "./icons/logo-promessa-escuro.png"
];
var FONTS = "https://fonts.googleapis.com/css2?family=Literata:ital,opsz,wght@0,7..72,400;0,7..72,600;1,7..72,400;1,7..72,500&family=Montserrat:wght@500;600;700&display=swap";

self.addEventListener("install", function(e){
  e.waitUntil(
    caches.open(VERSAO).then(function(c){
      return c.addAll(SHELL).then(function(){ return c.add(FONTS).catch(function(){}); });
    }).then(function(){ return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function(e){
  e.waitUntil(
    caches.keys().then(function(keys){
      return Promise.all(keys.filter(function(k){ return k !== VERSAO; }).map(function(k){ return caches.delete(k); }));
    }).then(function(){ return self.clients.claim(); })
  );
});

function putCache(req, res){
  var copy = res.clone();
  caches.open(VERSAO).then(function(c){ c.put(req, copy); });
  return res;
}

self.addEventListener("fetch", function(e){
  var req = e.request;
  if(req.method !== "GET") return;
  var url = new URL(req.url);
  var same = url.origin === location.origin;

  // Página e hinos: tenta a rede (pega atualização), cai pro cache sem internet.
  if(req.mode === "navigate" || (same && /\/(index\.html|hinos\.json)?$/.test(url.pathname))){
    var key = req.mode === "navigate" ? "./index.html" : req;
    e.respondWith(
      fetch(req).then(function(r){
        if(r && r.ok) putCache(key, r);
        return r;
      }).catch(function(){
        return caches.match(key, {ignoreSearch: true}).then(function(hit){ return hit || caches.match("./index.html"); });
      })
    );
    return;
  }

  // Ícones e fontes: cache primeiro.
  var cacheable = same || url.host === "fonts.googleapis.com" || url.host === "fonts.gstatic.com";
  if(!cacheable) return;
  e.respondWith(
    caches.match(req).then(function(hit){
      return hit || fetch(req).then(function(r){
        if(r && (r.ok || r.type === "opaque")) putCache(req, r);
        return r;
      });
    })
  );
});
