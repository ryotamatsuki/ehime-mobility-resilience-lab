const assert=require('node:assert/strict');
const fs=require('node:fs');
const {test}=require('node:test');
const html=fs.readFileSync('web/index.html','utf8');
test('Leaflet vendor JS is pinned',()=>{
  assert.match(html,/<script\b[^>]*src="https:\/\/unpkg\.com\/leaflet@1\.9\.4\/dist\/leaflet\.js"[^>]*integrity="sha384-[A-Za-z0-9+/=]+"[^>]*crossorigin="anonymous"/);
});
