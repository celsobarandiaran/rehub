/* El asistente: el mismo chat en la pantalla Asistente y en el botón flotante de todas las pantallas. Solo responde; no cambia datos. */
window.ReHubAsistente = (function () {
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function montar(o) {
    // o: {cuerpo, input, boton, sugeridas, pantalla, alTerminar}
    var cuerpo = o.cuerpo, input = o.input, boton = o.boton;
    function burbuja(texto, quien, extra) {
      var d = document.createElement("div");
      d.className = "burbuja " + quien;
      d.innerHTML = esc(texto).replace(/\n/g, "<br>") + (extra || "");
      cuerpo.appendChild(d);
      cuerpo.scrollTop = cuerpo.scrollHeight;
      return d;
    }
    function preguntar(texto) {
      texto = (texto || input.value).trim();
      if (!texto) return;
      input.value = "";
      burbuja(texto, "yo");
      var espera = burbuja("Mirando los datos…", "ia");
      boton.disabled = true;
      var fd = new FormData();
      fd.append("pregunta", texto);
      fd.append("pantalla", o.pantalla || "");
      fetch("/api/asistente", { method: "POST", body: fd }).then(function (r) { return r.json(); }).then(function (r) {
        espera.remove();
        if (r.error) { burbuja(r.error, "ia"); }
        else {
          burbuja(r.respuesta, "ia", '<div class="fuente">' + (r.sin_ia ? "Sin IA ahora mismo · " : "") + 'Fuente: <a href="' + esc(r.enlace) + '">' + esc(r.fuente_nombre) + ' → ver</a></div>');
        }
        boton.disabled = false;
        if (o.alTerminar) o.alTerminar(r);
      }).catch(function () { espera.textContent = "No se pudo preguntar (sin conexión)."; boton.disabled = false; });
    }
    boton.addEventListener("click", function () { preguntar(); });
    input.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); preguntar(); } });
    if (o.sugeridas) o.sugeridas.addEventListener("click", function (e) { if (e.target.tagName === "SPAN") preguntar(e.target.textContent); });
    return { preguntar: preguntar, burbuja: burbuja };
  }
  return { montar: montar };
})();
