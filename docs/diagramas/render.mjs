// Renderiza cada docs/diagramas/fuentes/*.mmd a docs/img/<nombre>.svg y .png
// con el tema común (tema.json).   Uso:  npm install   y luego   npm run render
// Opcional: npm run render -- 02_segmentar_hoja     (solo uno)
import { execFileSync } from "node:child_process";
import { mkdirSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const aqui = dirname(fileURLToPath(import.meta.url));
const fuentes = join(aqui, "fuentes");
const salida = resolve(aqui, "..", "img");
// se llama a node directamente (sin shell): así funcionan las rutas con espacios en Windows
const cli = join(aqui, "node_modules", "@mermaid-js", "mermaid-cli", "src", "cli.js");
const puppeteer = join(aqui, "puppeteer.json");
writeFileSync(puppeteer, JSON.stringify({ args: ["--no-sandbox"] }));
mkdirSync(salida, { recursive: true });

const solo = process.argv[2];
const archivos = readdirSync(fuentes).filter((f) => f.endsWith(".mmd") && (!solo || f.startsWith(solo)));
let fallos = 0;
for (const f of archivos) {
  const nombre = f.replace(/\.mmd$/, "");
  const antes = fallos;
  for (const ext of ["svg", "png"]) {
    const args = ["-i", join(fuentes, f), "-o", join(salida, `${nombre}.${ext}`),
      "-c", join(aqui, "tema.json"), "-p", puppeteer, "-b", "white", "-q"];
    if (ext === "png") args.push("-s", "2");
    try {
      execFileSync(process.execPath, [cli, ...args], { stdio: "pipe" });
    } catch (e) {
      fallos++;
      console.error(`ERROR en ${nombre}.${ext}:\n${e.stderr?.toString() || e.message}`);
    }
  }
  console.log(`${fallos === antes ? "ok   " : "FALLA"} ${nombre}`);
}
process.exit(fallos ? 1 : 0);
