// Interfaz mínima para el docente. Renderiza el informe en lenguaje natural.
const f = document.getElementById("f");
const $ = (id) => document.getElementById(id);

// mini-markdown -> HTML (títulos, negrita, listas, citas)
function md(src) {
  const esc = (s) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  const lines = esc(src).split("\n");
  let html = "", inList = false;
  for (let ln of lines) {
    ln = ln.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/_(.+?)_/g, "<em>$1</em>");
    if (/^### /.test(ln)) { if (inList) { html += "</ul>"; inList = false; } html += `<h3>${ln.slice(4)}</h3>`; }
    else if (/^## /.test(ln)) { html += `<h2>${ln.slice(3)}</h2>`; }
    else if (/^> /.test(ln)) { html += `<blockquote>${ln.slice(2)}</blockquote>`; }
    else if (/^- /.test(ln)) { if (!inList) { html += "<ul>"; inList = true; } html += `<li>${ln.slice(2)}</li>`; }
    else if (/^---/.test(ln)) { if (inList) { html += "</ul>"; inList = false; } html += "<hr/>"; }
    else { if (inList) { html += "</ul>"; inList = false; } if (ln.trim()) html += `<p>${ln}</p>`; }
  }
  if (inList) html += "</ul>";
  return html;
}

f.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(f);
  $("informe").hidden = $("panel").hidden = $("aviso").hidden = true;
  const btn = f.querySelector("button");
  btn.disabled = true; btn.textContent = "Evaluando…";
  try {
    const r = await fetch("/evaluar", { method: "POST", body: fd });
    if (!r.ok) throw new Error(await r.text());
    const data = await r.json();
    if (data.aviso_confianza) { $("aviso").textContent = data.aviso_confianza; $("aviso").hidden = false; }
    $("informe").innerHTML = md(data.informe_docente_md);
    $("informe").dataset.accion = data.accion;   // el CSS pinta un color por acción
    $("informe").hidden = false;
    $("panel-json").textContent = JSON.stringify(data.panel_tecnico, null, 2);
    $("panel").hidden = false;
  } catch (err) {
    $("aviso").textContent = "Error: " + err.message; $("aviso").hidden = false;
  } finally {
    btn.disabled = false; btn.textContent = "Evaluar";
  }
});
