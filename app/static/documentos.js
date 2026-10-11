/* Pantalla Documentos: calendario (día, periodo, mes, varios meses, año, todo), listas por tipo y comparación con Mercabarna. */
(function(){
  var NOMBRES=["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"];
  var CORTOS=["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"];
  var TIPOS_GASTO=["Mercado (compras sueltas)","Hielo y bebida","Reparaciones y mantenimiento","Material y menaje","Transporte y aparcamiento","Otros"];
  var DOCS=[],DIAS={},MERC={precios:{}},ANIO=2026;
  var $=function(i){return document.getElementById(i)};
  function eur(x){if(x===null||x===undefined)return "—";var s=x<0?"−":"",p=Math.abs(x).toFixed(2).split(".");return s+p[0].replace(/\B(?=(\d{3})+(?!\d))/g,".")+","+p[1]}
  function fFecha(s){if(!s)return "—";var p=s.split("-");return p[2]+"/"+p[1]}
  function iso(m,d){return ANIO+"-"+("0"+(m+1)).slice(-2)+"-"+("0"+d).slice(-2)}
  function esc(s){return String(s||"").replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})}

  /* ---------- calendario ---------- */
  var cal={modo:"mes",ini:null,fin:null,mesIni:9,mesFin:9,vista:9};
  function rango(){
    if(cal.modo==="todo")return ["0000-00-00","9999-99-99"];
    if(cal.modo==="anio")return [ANIO+"-01-01",ANIO+"-12-31"];
    if(cal.modo==="mes")return [iso(cal.mesIni,1),iso(cal.mesFin,31)];
    var a=cal.ini,b=cal.fin===null?cal.ini:cal.fin;return a<b?[a,b]:[b,a];
  }
  function enRango(f){var r=rango();return f&&f>=r[0]&&f<=r[1]}
  function pintaCal(){
    document.querySelector(".cal").classList.toggle("apagado",cal.modo==="todo");
    document.querySelectorAll("#calModo span").forEach(function(s){s.classList.toggle("on",s.dataset.m===cal.modo)});
    var r=rango();
    $("calMeses").innerHTML=CORTOS.map(function(c,i){
      var hay=Object.keys(DIAS).some(function(k){return k.slice(0,7)===iso(i,1).slice(0,7)}),dentro=cal.modo!=="todo"&&iso(i,31)>=r[0]&&iso(i,1)<=r[1];
      return '<span class="'+(hay?"hay ":"")+(cal.modo==="mes"&&dentro?"on ":"")+(cal.modo==="dia"&&dentro?"rango ":"")+(i===cal.vista?"vista":"")+'">'+c+'</span>'}).join("");
    var h=["L","M","X","J","V","S","D"].map(function(x){return '<div class="cab">'+x+'</div>'}).join("");
    var primero=(new Date(ANIO,cal.vista,1).getDay()+6)%7,total=new Date(ANIO,cal.vista+1,0).getDate();
    for(var i=0;i<primero;i++)h+='<div></div>';
    for(var d=1;d<=total;d++){var o=iso(cal.vista,d),dentro=cal.modo!=="todo"&&o>=r[0]&&o<=r[1],ext=cal.modo==="dia"&&(o===r[0]||o===r[1]);
      h+='<div class="d'+(DIAS[o]?" hay":"")+(ext?" on":(dentro?" rango":""))+'" data-d="'+d+'">'+d+'</div>'}
    $("calDias").innerHTML=h;
    $("calDias").style.display=cal.modo==="dia"?"":"none";  // calendario compacto: los días solo en el modo Día
    var t;
    if(cal.modo==="todo")t="Todo";else if(cal.modo==="anio")t=String(ANIO);
    else if(cal.modo==="mes")t=cal.mesIni===cal.mesFin?NOMBRES[cal.mesIni][0].toUpperCase()+NOMBRES[cal.mesIni].slice(1)+" "+ANIO:CORTOS[cal.mesIni]+" – "+CORTOS[cal.mesFin]+" "+ANIO;
    else t=r[0]===r[1]?fFecha(r[0])+"/"+ANIO:fFecha(r[0])+" – "+fFecha(r[1]);
    $("calTitulo").textContent=t;
    var n=DOCS.filter(function(x){return enRango(x.fecha)}).length;
    var pista=cal.modo==="dia"&&cal.fin===null?" Pulsa otro día (de este u otro mes) para elegir un periodo.":(cal.modo==="mes"&&cal.mesIni===cal.mesFin?" Pulsa otro mes para elegir varios.":"");
    $("calInfo").innerHTML="Mostrando <b>"+n+"</b> documentos."+pista;
    pintaLista();
  }
  $("calModo").addEventListener("click",function(e){var m=e.target.dataset.m;if(!m)return;cal.modo=m;if(m==="dia"){cal.ini=iso(cal.vista,1);cal.fin=null}if(m==="mes"){cal.mesIni=cal.mesFin=cal.vista}pintaCal()});
  $("calMeses").addEventListener("click",function(e){var i=CORTOS.indexOf(e.target.textContent);if(i<0)return;
    if(cal.modo==="dia"&&cal.fin===null){cal.vista=i;pintaCal();return}
    if(cal.modo==="mes"&&cal.mesIni===cal.mesFin&&i!==cal.mesIni){cal.mesFin=Math.max(i,cal.mesIni);cal.mesIni=Math.min(i,cal.mesIni)}else{cal.mesIni=cal.mesFin=i}
    cal.modo="mes";cal.vista=i;pintaCal()});
  $("calDias").addEventListener("click",function(e){var d=+e.target.dataset.d;if(!d)return;var o=iso(cal.vista,d);if(cal.modo==="dia"&&cal.fin===null&&o!==cal.ini)cal.fin=o;else{cal.ini=o;cal.fin=null}cal.modo="dia";pintaCal()});
  document.querySelectorAll(".cal .flecha").forEach(function(b,i){b.addEventListener("click",function(){cal.vista=Math.min(11,Math.max(0,cal.vista+(i?1:-1)));if(cal.modo==="mes"&&cal.mesIni===cal.mesFin)cal.mesIni=cal.mesFin=cal.vista;pintaCal()})});

  /* ---------- listas ---------- */
  // Todo arranca recogido: los dos bloques de facturas cerrados; cada proveedor se abre al pincharlo y las líneas al pinchar la factura.
  var st={tipo:"factura",orden:"grupo",abiertos:{},cerradas:{comida:true,local:true},sel:null};
  var CAT=[["comida","🍽️ Comida y bebida","cuenta para el coste de comida"],["local","🏠 Local y servicios","alquiler, luz, gas, seguros, limpieza…"]];
  function chipEstado(x){
    if(x.estado==="duplicada")return '<span class="chip c-dup">'+esc(x.motivo)+'</span>';
    if(x.estado==="revisar")return '<span class="chip c-rev">Revisar: '+esc(x.motivo)+'</span>';
    if(x.estado==="leyendo")return '<span class="chip c-est">La IA lo está leyendo…</span>';
    return '<span class="chip c-ok">Correcto</span>'}
  function chipPago(x){
    if(x.estado==="duplicada")return '<span class="chip c-dup">No pagar</span>';
    if(x.pagado)return '<span class="chip c-ok">Pagada '+fFecha(x.pagado)+'</span>';
    if(x.vence)return '<span class="chip c-rev">Pendiente · vence '+fFecha(x.vence)+'</span>';
    return '<span class="chip">—</span>'}
  function enlace(x,texto){return '<a href="/archivo/'+x.id+'" target="_blank">'+esc(texto)+'</a>'}
  var CFG={
    factura:{grupo:"Grupo y proveedor",clave:function(x){return x.proveedor||"Sin proveedor"},n:["factura","facturas"],cols:7,
      cab:'<tr><th>Archivo</th><th>Proveedor</th><th>Nº</th><th class="num">Base</th><th class="num">Total</th><th>Estado</th><th>Pago (banco)</th></tr>',
      fila:function(x,g){return '<tr data-id="'+x.id+'" class="fac'+(x.id===st.sel?' sel':'')+(g&&!st.abiertos[g]?' oculto':'')+'"><td>'+enlace(x,x.archivo)+'</td><td>'+esc(x.proveedor)+'</td><td>'+(x.numero?esc(x.numero):'<span class="chip c-rev">revisar</span>')+'</td><td class="num">'+eur(x.base)+'</td><td class="num"><b>'+eur(x.total)+'</b></td><td>'+chipEstado(x)+'</td><td>'+chipPago(x)+'</td></tr>'}},
    gasto:{grupo:"Tipo de gasto",clave:function(x){return x.categoria||"Otros"},claves:TIPOS_GASTO,n:["gasto","gastos"],cols:6,
      cab:'<tr><th>Archivo</th><th>Fecha</th><th>Dónde</th><th>Tipo</th><th class="num">Total</th><th>Estado</th></tr>',
      fila:function(x,g){return '<tr class="'+(g&&!st.abiertos[g]?'oculto':'')+'"><td>'+enlace(x,x.archivo)+'</td><td>'+fFecha(x.fecha)+'</td><td>'+esc((x.datos||{}).comercio||"")+'</td><td>'+esc(x.categoria)+'</td><td class="num"><b>'+eur(x.total)+'</b></td><td>'+chipEstado(x)+'</td></tr>'}},
    nomina:{grupo:"Empleado",clave:function(x){return (x.empleado||"").split(" (")[0]},n:["nómina","nóminas"],cols:6,
      cab:'<tr><th>Archivo</th><th>Empleado</th><th>Mes</th><th class="num">Bruto</th><th class="num">Neto</th><th class="num">Coste empresa</th></tr>',
      fila:function(x,g){var d=x.datos||{};return '<tr class="'+(g&&!st.abiertos[g]?'oculto':'')+'"><td>'+enlace(x,x.archivo)+'</td><td>'+esc(x.empleado)+'</td><td>'+(d.mes?NOMBRES[d.mes-1]:"—")+'</td><td class="num">'+eur(d.bruto)+'</td><td class="num">'+eur(d.neto)+'</td><td class="num"><b>'+eur(x.total)+'</b></td></tr>'}},
    cierre:{grupo:"Mes",clave:function(x){return x.fecha?NOMBRES[+x.fecha.slice(5,7)-1]:""},n:["cierre","cierres"],cols:4,
      cab:'<tr><th>Archivo</th><th>Día</th><th class="num">Ventas</th><th>Estado</th></tr>',
      fila:function(x,g){return '<tr class="'+(g&&!st.abiertos[g]?'oculto':'')+'"><td>'+enlace(x,x.archivo)+'</td><td>'+fFecha(x.fecha)+'</td><td class="num"><b>'+eur(x.total)+'</b></td><td>'+chipEstado(x)+'</td></tr>'}},
    otro:{grupo:null,n:["documento","documentos"],cols:4,sinOrden:true,
      cab:'<tr><th>Archivo</th><th>Fecha</th><th>Estado</th><th></th></tr>',
      fila:function(x){return '<tr><td>'+enlace(x,x.archivo)+'</td><td>'+fFecha(x.fecha)+'</td><td>'+chipEstado(x)+'</td><td><a href="/p/bandeja?id='+x.correo_id+'">✉ correo</a></td></tr>'}}
  };
  function pintaLista(){
    var C=CFG[st.tipo],q=$("buscar").value.toLowerCase().trim();
    document.querySelectorAll("#docTipo span").forEach(function(s){s.classList.toggle("on",s.dataset.t===st.tipo)});
    if(!C.grupo&&st.orden==="grupo")st.orden="fecha";
    document.querySelectorAll("#docOrden span").forEach(function(s){s.classList.toggle("on",s.dataset.o===st.orden)});
    $("docOrdenFila").style.display=C.sinOrden?"none":"flex";$("docOrdenGrupo").style.display=C.grupo?"":"none";$("docOrdenGrupo").textContent=C.grupo||"";
    var datos=DOCS.filter(function(x){return x.tipo===st.tipo&&enRango(x.fecha)&&(!q||JSON.stringify(x).toLowerCase().indexOf(q)>=0)});
    var total=datos.reduce(function(a,x){return a+(x.total||0)},0);
    $("docResumen").textContent=datos.length+" "+(datos.length===1?C.n[0]:C.n[1])+(st.tipo!=="otro"?" · "+eur(total)+" €":"");
    var revisar=DOCS.filter(function(x){return x.estado==="revisar"}).length,dup=DOCS.filter(function(x){return x.estado==="duplicada"}).length,pend=DOCS.filter(function(x){return x.tipo==="factura"&&!x.pagado&&x.vence&&x.estado!=="duplicada"}).length;
    $("chipsEstado").innerHTML='<span class="chip c-rev">'+revisar+' por revisar</span><span class="chip c-dup">'+dup+' duplicada'+(dup===1?"":"s")+'</span><span class="chip">'+pend+' pendientes de pago</span>';
    var h='<table class="resp">'+C.cab;
    if(!datos.length)h+='<tr><td colspan="'+C.cols+'" class="mut">No hay documentos de este tipo en estas fechas.</td></tr>';
    else if(st.orden==="grupo"&&C.grupo){
      var g={};datos.forEach(function(x){(g[C.clave(x)]=g[C.clave(x)]||[]).push(x)});
      var claves=(C.claves||Object.keys(g)).slice().sort(function(a,b){return sum(g[b])-sum(g[a])});
      var bloques=st.tipo==="factura"?CAT.map(function(c){return [c,claves.filter(function(k){return g[k]&&(g[k][0].grupo||"comida")===c[0]})]}):[[null,claves]];
      bloques.forEach(function(b){
        if(b[0]){var sub=b[1].reduce(function(a,k){return a+sum(g[k])},0),n=b[1].reduce(function(a,k){return a+g[k].length},0),cerrada=!!st.cerradas[b[0][0]];
          h+='<tr class="cat" data-cat="'+b[0][0]+'"><td colspan="'+(C.cols-1)+'">'+(cerrada?"▸":"▾")+' '+b[0][1]+' <span class="mut peq" style="font-weight:400">· '+n+' facturas · '+eur(sub)+' € · '+b[0][2]+'</span></td><td class="num">'+eur(sub)+' €</td></tr>';
          if(cerrada)return}
        b[1].forEach(function(k){var l=g[k]||[],ab=!!st.abiertos[k];
          h+='<tr class="grupo" data-k="'+esc(k)+'"><td colspan="'+(C.cols-1)+'"><span class="flechita">'+(l.length?(ab?"▾":"▸"):"")+'</span>'+esc(k)+' <span class="mut peq" style="font-weight:400">· '+l.length+" "+(l.length===1?C.n[0]:C.n[1])+' · '+eur(sum(l))+' €</span></td><td class="num">'+eur(sum(l))+' €</td></tr>';
          l.sort(function(a,b){return a.fecha<b.fecha?-1:1}).forEach(function(x){h+=C.fila(x,k)})});
      });
    }else{
      datos.sort(st.orden==="importe"?function(a,b){return (b.total||0)-(a.total||0)}:function(a,b){return a.fecha<b.fecha?1:-1});
      datos.forEach(function(x){h+=C.fila(x)});
    }
    $("docLista").innerHTML=h+'</table>';
    $("docLineas").style.display=st.tipo==="factura"&&st.sel?"block":"none";
    etiquetar();
  }
  function sum(l){return (l||[]).reduce(function(a,x){return a+(x.total||0)},0)}
  $("docTipo").addEventListener("click",function(e){var t=e.target.dataset.t;if(!t)return;st.tipo=t;st.orden="grupo";st.abiertos={};pintaLista()});
  $("docOrden").addEventListener("click",function(e){var o=e.target.dataset.o;if(!o)return;st.orden=o;pintaLista()});
  $("buscar").addEventListener("input",pintaLista);
  $("docLista").addEventListener("click",function(e){
    if(e.target.closest("a"))return;
    var c=e.target.closest("tr.cat");if(c){st.cerradas[c.dataset.cat]=!st.cerradas[c.dataset.cat];pintaLista();return}
    var f=e.target.closest("tr.fac");if(f){st.sel=+f.dataset.id;cmp.on=false;pintaLista();verFactura(st.sel);return}
    var g=e.target.closest("tr.grupo");if(!g)return;st.abiertos[g.dataset.k]=!st.abiertos[g.dataset.k];pintaLista()});

  /* ---------- líneas y comparación con Mercabarna ---------- */
  var cmp={on:false,datos:null,margen:0.60};
  function verFactura(id){fetch("/api/factura/"+id).then(function(r){return r.json()}).then(function(d){cmp.datos=d;pintaLineas()})}
  function pintaLineas(){
    var d=cmp.datos;if(!d)return;
    var sePuede=d.lineas.some(function(l){return MERC.precios[l.mercabarna]});
    $("cmpTitulo").textContent="Líneas de "+d.titulo+" (sin IVA)";
    $("cmpBtn").style.display=sePuede?"":"none";$("cmpBtn").textContent=cmp.on?"✕ Quitar comparación":"🔎 Comparar con Mercabarna";
    var on=cmp.on&&sePuede,h='<tr><th>Producto</th><th class="num">Cantidad</th><th class="num">Precio</th><th class="num">Importe</th>'+(on?'<th class="num">Mercabarna</th><th class="num">Diferencia</th><th class="num">En este pedido</th>':'')+'</tr>',ahorro=0;
    d.lineas.forEach(function(l){
      h+='<tr><td>'+esc(l.descripcion)+'</td><td class="num">'+(l.cantidad===null?"—":String(l.cantidad).replace(".",","))+' '+esc(l.unidad)+'</td><td class="num">'+eur(l.precio)+' €</td><td class="num">'+(l.precio!==null&&l.cantidad!==null?eur(l.precio*l.cantidad)+' €':"—")+'</td>';
      if(on){var m=MERC.precios[l.mercabarna];
        if(!m)h+='<td colspan="3" class="mut">No comparable: Mercabarna no tiene este producto</td>';
        else{var dif=l.precio/m.precio-1,raz=m.precio*(1+cmp.margen),ped=Math.max(0,(l.precio-raz)*l.cantidad);ahorro+=ped;
          var chip=dif<0?'<span class="chip c-fact">'+Math.round(dif*100)+' %</span>':'<span class="chip '+(l.precio<=raz?'c-ok':(dif>1?'c-dup':'c-rev'))+'">+'+Math.round(dif*100)+' %</span>';
          h+='<td class="num">'+enlaceMerc(l.mercabarna,eur(m.precio)+' €')+'</td><td class="num">'+chip+'</td><td class="num">'+(dif<0?'¿es fresco?':(ped?'<b style="color:var(--ok)">'+eur(ped)+' €</b>':'0 €'))+'</td>'}}
      h+='</tr>'});
    $("cmpTabla").innerHTML=h;etiquetar();
    $("cmpNota").innerHTML=!sePuede?"Ningún producto de esta factura está en Mercabarna (carne, bebida, local…).":(on?'Con un precio razonable (Mercabarna + 60 %) ahorrarías <b style="color:var(--ok)">'+eur(ahorro)+' €</b> en este pedido. Precios de Mercabarna: '+MERC.fecha+' (pincha el precio para verlo en su web).':"Pulsa Comparar con Mercabarna para ver cuánto cambiaría cada producto.");
  }
  $("cmpBtn").addEventListener("click",function(){cmp.on=!cmp.on;pintaLineas()});
  function enlaceMerc(cod,texto){return '<a href="#" class="merc" data-c="'+cod+'">'+texto+' ↗</a>'}
  document.addEventListener("click",function(e){
    var a=e.target.closest("a.merc");if(!a)return;e.preventDefault();var c=a.dataset.c,m=MERC.precios[c],f=document.createElement("form");
    f.method="post";f.target="_blank";f.action="https://www.mercabarna.es/serveis/es_estadistiques-productes/"+(m.sector==="2"?"?sector=2":"")+"#resultats";
    var v={sector:m.sector,grup:"",producte:c,arees:"0",origen:"",periode:"3","data-inici":"01-09-2026","data-final":"30-09-2026",exportField:"",generar:"Generar estadísticas"};
    Object.keys(v).forEach(function(k){var i=document.createElement("input");i.type="hidden";i.name=k;i.value=v[k];f.appendChild(i)});document.body.appendChild(f);f.submit();f.remove()});

  /* ---------- móvil: tablas como tarjetas ---------- */
  function etiquetar(){document.querySelectorAll("table.resp").forEach(function(t){var cab=[].map.call(t.querySelectorAll("tr:first-child th"),function(th){return th.textContent.trim()});
    [].forEach.call(t.querySelectorAll("tr"),function(tr){[].forEach.call(tr.children,function(td,i){if(td.tagName==="TD"&&!td.hasAttribute("colspan")&&cab[i]!==undefined)td.setAttribute("data-label",cab[i])})})})}

  Promise.all([fetch("/api/documentos").then(function(r){return r.json()}),fetch("/static/mercabarna.json").then(function(r){return r.json()})]).then(function(r){
    DOCS=r[0].documentos;DIAS=r[0].dias;MERC=r[1];
    var ultimo=Object.keys(DIAS).sort().pop();if(ultimo){ANIO=+ultimo.slice(0,4);cal.vista=cal.mesIni=cal.mesFin=+ultimo.slice(5,7)-1}
    pintaCal();
  });
})();
