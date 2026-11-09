/* Cliente REST y mashup OpenLayers, sin frameworks. */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const N = new Intl.NumberFormat('es-ES');
  let map = null, vectorSource = null, selectedId = null, searchOffset = 0;
  let lastFilters = {}, currentTotal = 0, issueOffset = 0, activeLoad = null;
  const PAGE_SIZE = 30;
  let searchSerial = 0, mapTimer = null, toastTimer = null;

  const esc = (x) => String(x ?? '').replace(/[&<>"']/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[s]));
  const urlParams = (params) => new URLSearchParams(Object.entries(params).filter(([, v]) => v !== '' && v != null));
  const get = async (path, params={}) => {
    const url = path + (Object.keys(params).length ? '?' + urlParams(params) : '');
    const res = await fetch(url);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `Error HTTP ${res.status}`);
    return data;
  };
  const toast = (msg, error=false) => {
    clearTimeout(toastTimer);
    $('toast').textContent = msg;
    $('toast').className = 'toast' + (error ? ' error' : '');
    $('toast').hidden = false;
    toastTimer = setTimeout(() => {$('toast').hidden = true;}, 4700);
  };
  const getFilters = () => ({
    q: $('q').value.trim(), municipio: $('municipio').value.trim(),
    provincia: $('provincia').value, ambito: $('ambito').value,
    fuente: $('fuente').value,
  });
  const mapBbox = () => {
    if (!map || !$('map-only').checked) return null;
    const bounds = map.getView().calculateExtent(map.getSize());
    const wgs = ol.proj.transformExtent(bounds, 'EPSG:3857', 'EPSG:4326');
    return [Math.max(-180,wgs[0]), Math.max(-90,wgs[1]), Math.min(180,wgs[2]),Math.min(90,wgs[3])].join(',');
  };
  const card = (e) => {
    const coords = e.longitud != null && e.latitud != null;
    const sourceName = {CV: 'Comunitat Valenciana', CAT: 'Catalunya', CAN: 'Canarias'}[e.fuente];
    const location = [e.localidad, e.provincia].filter(Boolean).join(' · ');
    const link = e.url ? `<a target="_blank" rel="noopener noreferrer" href="${esc(e.url)}">Web ↗</a>` : '';
    return `<article class="result-card" data-id="${esc(e.id_entidad)}">
      <span class="source ${esc(e.fuente)}">${esc(sourceName)}</span>
      <h3>${esc(e.nombre)}</h3>
      ${location ? `<p class="city">⌖ ${esc(location)}</p>` : ''}
      ${e.direccion ? `<p>${esc(e.direccion)}</p>` : ''}
      ${e.ambito ? `<span class="ambit">${esc(e.ambito.replaceAll('_',' '))}</span>` : ''}
      <div class="card-actions"><button data-detail="${esc(e.id_entidad)}" type="button">Ver detalles →</button>
      ${coords ? `<button data-focus="${esc(e.longitud)},${esc(e.latitud)}" type="button">Ver en el mapa</button>` : `<span class="muted-btn" title="La fuente no incluye coordenadas">Sin coordenadas</span>`}${link}</div>
    </article>`;
  };
  const renderResults = (payload, append=false) => {
    currentTotal = payload.total;
    $('result-total').textContent = N.format(payload.total);
    $('results-description').textContent = payload.total ? 'Organizaciones encontradas con tus filtros' : 'Prueba con otros filtros o ejecuta la carga de datos';
    if (append) $('results').insertAdjacentHTML('beforeend', payload.items.map(card).join(''));
    else $('results').innerHTML = payload.items.length ? payload.items.map(card).join('') : '<div class="blank">No hay entidades que cumplan estos filtros.</div>';
    const shown = Math.min(payload.total, payload.offset + payload.items.length);
    $('more').hidden = shown >= payload.total;
    $('results-count').textContent = payload.total ? `Mostrando ${N.format(shown)} de ${N.format(payload.total)}` : '';
  };
  const loadResults = async (append=false) => {
    const requestId = ++searchSerial;
    const bbox = mapBbox();
    const params = {...lastFilters, limit: PAGE_SIZE, offset: searchOffset};
    if (bbox) params.bbox = bbox;
    try {
      const data = await get('/api/entities',params);
      if (requestId === searchSerial) renderResults(data,append);
    } catch(e) {toast('No se pudieron consultar resultados: ' + e.message,true);}
  };
  const loadMap = async () => {
    if (!map) return;
    try {
      const ext = map.getView().calculateExtent(map.getSize());
      const bounds = ol.proj.transformExtent(ext,'EPSG:3857','EPSG:4326');
      const params = {...lastFilters,
        bbox: [Math.max(-180,bounds[0]),Math.max(-90,bounds[1]),Math.min(180,bounds[2]),Math.min(90,bounds[3])].join(',')};
      const data = await get('/api/map',params);
      const features = new ol.format.GeoJSON().readFeatures(data,{featureProjection:'EPSG:3857'});
      vectorSource.clear(); vectorSource.addFeatures(features);
      $('map-total').textContent = `${N.format(data.total_con_coordenadas)} ubicaciones`;
    } catch(e){toast('Error al consultar el mapa: '+e.message,true);}
  };
  const update = async () => {
    lastFilters = getFilters(); searchOffset=0;
    await Promise.all([loadResults(),loadMap()]);
  };
  const updateStats = async () => {
    const data = await get('/api/stats');
    $('stat-total').textContent = N.format(data.total);
    $('stat-geo').textContent = N.format(data.geolocalizadas);
    $('stat-sources').textContent = Object.values(data.fuentes).filter(x=>x>0).length + '/3';
    $('connection').innerHTML = '<i></i> Conectado';
    $('connection').classList.remove('error');
  };
  const updateMetadata = async () => {
    const data = await get('/api/metadata');
    const selectedProvince = $('provincia').value;
    const selectedAmbit = $('ambito').value;
    $('provincia').innerHTML = '<option value="">Todas las provincias</option>' + data.provincias.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');
    $('ambito').innerHTML = '<option value="">Todos los ámbitos</option>' + data.ambitos.map(x=>`<option value="${esc(x)}">${esc(x.replaceAll('_',' '))}</option>`).join('');
    $('provincia').value = selectedProvince;
    $('ambito').value = selectedAmbit;
  };
  const selectTab = (admin) => {
    $('tab-search').classList.toggle('active',!admin);
    $('tab-load').classList.toggle('active',admin);
    $('tab-search').setAttribute('aria-selected',String(!admin));
    $('tab-load').setAttribute('aria-selected',String(admin));
    $('search-panel').hidden = admin;
    $('load-panel').hidden = !admin;
    if (admin) history();
    if (map) setTimeout(()=>map.updateSize(),80);
  };
  const initializeMap = () => {
    if (typeof ol === 'undefined') {$('map-fallback').hidden=false;return;}
    vectorSource = new ol.source.Vector();
    const markerStyle = new ol.style.Style({
      image: new ol.style.Circle({radius:6,fill:new ol.style.Fill({color:'#2b7059'}),stroke:new ol.style.Stroke({color:'#fff',width:1.8})}),
    });
    map = new ol.Map({target:'map',layers:[new ol.layer.Tile({source:new ol.source.OSM()}), new ol.layer.Vector({source:vectorSource,style:markerStyle})],
      view:new ol.View({center:ol.proj.fromLonLat([-3.2,39.5]),zoom:6,minZoom:3,maxZoom:18}),
      });
    map.on('moveend',()=>{
      clearTimeout(mapTimer);
      mapTimer=setTimeout(()=>{
        loadMap();
        if ($('map-only').checked){searchOffset=0;loadResults();}
      },250);
    });
    map.on('singleclick', event=>{
      const feature = map.forEachFeatureAtPixel(event.pixel, f=>f);
      if (!feature) return;
      const id = feature.get('id_entidad');
      focusCard(id);
      const geometry = feature.getGeometry();
      map.getView().animate({center:geometry.getCoordinates(),zoom:Math.max(map.getView().getZoom(),10),duration:450});
    });
  };
  const focusCard = (id) => {
    const card = Array.from(document.querySelectorAll('.result-card')).find(x=>x.dataset.id===id);
    if (card) {card.scrollIntoView({behavior:'smooth',block:'nearest'});card.style.background='#edf7ec';setTimeout(()=>card.style.background='',1200);}
  };
  const detail = async (id) => {
    try {
      const e=await get('/api/entities/'+encodeURIComponent(id));
      const fields=[['Identificador',e.id_entidad],['Fuente',e.fuente],['Ámbito',e.ambito],['Dirección',e.direccion],
       ['Localidad',e.localidad],['Provincia',e.provincia],['Código postal',e.codigo_postal],['Descripción',e.descripcion],
       ['Contacto',e.contacto],['Coordenadas',e.longitud==null ? null : e.latitud+', '+e.longitud]];
      const message=fields.filter(([,v])=>v!=null).map(([k,v])=>k+': '+v).join('\n');
      // Diálogo nativo: seguro ante inyección HTML.
      alert(message || 'Sin detalles adicionales');
    } catch(e){toast('Error al abrir detalle: '+e.message,true);}
  };
  const history = async () => {
    try {
      const data = await get('/api/loads',{limit:12});
      $('load-history').innerHTML = data.items.length ? data.items.map(l=>`<button type="button" data-issues="${l.id}"><b>${esc(l.fuente)} · ${esc(l.fecha.slice(0,19).replace('T',' '))}</b><br>
        ${l.insertados} insertados · ${l.actualizados} actualizados · ${l.sin_cambios} sin cambios · ${l.incidencias} incidencias<br>Ver auditoría →</button>`).join('') : '<p class="muted">Todavía no hay cargas.</p>';
    } catch(e){$('load-history').textContent='No se pudo consultar historial: '+e.message;}
  };
  const showIssues = async (id, append=false) => {
    if (!append){activeLoad=id;issueOffset=0;}
    const data=await get(`/api/loads/${id}/issues`,{offset:issueOffset,limit:30});
    $('issue-section').hidden=false;
    $('issues-download').href = `/api/loads/${id}/issues.csv`;
    $('issue-count').textContent = '('+data.total+')';
    const html = data.items.map(x=>`<div class="issue-item"><b>${esc(x.entidad_id||'Sin ID')} · fila ${x.fila}</b><br>
      <span class="${x.gravedad==='reparacion'?'repair':x.gravedad==='error'?'error':''}">${esc(x.gravedad.toUpperCase())}</span> · ${esc(x.codigo)}<br>
      ${esc(x.descripcion)} ${x.original?`<small>· Origen: ${esc(x.original).slice(0,100)}</small>`:''}</div>`).join('');
    if (append)$('issues').insertAdjacentHTML('beforeend',html);
    else $('issues').innerHTML=html || '<p class="muted">Sin incidencias.</p>';
    issueOffset+=data.items.length;
    $('issues-next').hidden=issueOffset>=data.total;
  };
  const executeLoad = async () => {
    const selected=[['load-cv','CV'],['load-cat','CAT'],['load-can','CAN']].filter(([id])=>$(id).checked).map(([,s])=>s);
    if (!selected.length){toast('Selecciona al menos una fuente.',true);return;}
    $('load-btn').disabled=true;
    $('load-feedback').textContent='Extrayendo datos por HTTP y ejecutando mappings...';
    try {
      const response=await fetch('/api/load',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sources:selected})});
      const data=await response.json();
      if (!response.ok) throw new Error(data.detail||response.statusText);
      $('load-feedback').innerHTML=data.results.map(x=>x.status==='ok'
        ? `<b>${esc(x.source)} ✓</b> ${N.format(x.leidos)} leídos · ${x.insertados} nuevos · ${x.actualizados} actualizados · ${x.descartados} descartados · ${x.incidencias} incidencias (${x.reparaciones} reparaciones)<br>`
        : `<b>${esc(x.source)} ✗</b> ${esc(x.message)}<br>`).join('');
      if (data.status==='ok')toast('Carga ETL terminada correctamente');
      else toast('Una o varias fuentes no pudieron cargarse',true);
      await Promise.all([history(),updateStats(),updateMetadata(),update()]);
    }catch(e){$('load-feedback').textContent=e.message;toast('Error de carga: '+e.message,true);}
    finally{$('load-btn').disabled=false;}
  };
  $('search-form').addEventListener('submit',e=>{e.preventDefault();update();});
  $('reset').addEventListener('click',()=>{$('search-form').reset();update();});
  $('map-only').addEventListener('change',()=>{searchOffset=0;loadResults();});
  $('more').addEventListener('click',()=>{searchOffset+=PAGE_SIZE;loadResults(true);});
  $('tab-search').addEventListener('click',()=>selectTab(false));
  $('tab-load').addEventListener('click',()=>selectTab(true));
  $('load-btn').addEventListener('click',executeLoad);
  $('load-history').addEventListener('click',e=>{
    const el=e.target.closest('[data-issues]');if(el)showIssues(Number(el.dataset.issues)).catch(x=>toast(x.message,true));
  });
  $('issues-next').addEventListener('click',()=>{if(activeLoad)showIssues(activeLoad,true).catch(x=>toast(x.message,true));});
  $('results').addEventListener('click',e=>{
    const btn=e.target.closest('button');if(!btn)return;
    if(btn.dataset.detail)detail(btn.dataset.detail);
    else if(btn.dataset.focus && map){
      const [lon,lat]=btn.dataset.focus.split(',').map(Number);
      map.getView().animate({center:ol.proj.fromLonLat([lon,lat]),zoom:12,duration:500});
    }
  });
  $('map-reset').addEventListener('click',()=>map?.getView().animate({center:ol.proj.fromLonLat([-3.2,39.5]),zoom:6,duration:500}));
  (async()=>{
    initializeMap();
    try {await updateStats(); await updateMetadata(); await update();}
    catch(e){$('connection').innerHTML='<i></i> Sin conexión';$('connection').classList.add('error');toast('No se puede conectar con la API: '+e.message,true);}
  })();
})();
