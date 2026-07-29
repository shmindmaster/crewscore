import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, normalize, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(fileURLToPath(new URL("..", import.meta.url)));
const port = Number(process.env.CREWSCORE_STATIC_PORT || "41731");
const types = { ".css": "text/css; charset=utf-8", ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon" };
const server = createServer((request, response) => {
  const raw = decodeURIComponent(new URL(request.url, "http://localhost").pathname);
  const relative = normalize(raw === "/" ? "index.html" : raw.replace(/^\/+/, ""));
  let file = resolve(root, relative);
  if (!file.startsWith(root + sep) && file !== root) { response.writeHead(403).end("Forbidden"); return; }
  if (existsSync(file) && statSync(file).isDirectory()) file = resolve(file, "index.html");
  if (!existsSync(file) || !statSync(file).isFile()) { response.writeHead(404).end("Not found"); return; }
  response.writeHead(200, { "content-type": types[extname(file)] || "application/octet-stream", "cache-control": "no-store" });
  createReadStream(file).pipe(response);
});
server.listen(port, "127.0.0.1", () => console.log(`CrewScore static server: http://127.0.0.1:${port}`));
