import { createServer } from "node:http";
import { createReadStream, statSync } from "node:fs";
import { join, extname, normalize } from "node:path";

const ROOT = "/srv/www";
const PORT = process.env.PORT || 80;

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript",
  ".css": "text/css",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".ico": "image/x-icon",
  ".json": "application/json",
  ".webmanifest": "application/manifest+json",
};

createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  let path = normalize(join(ROOT, url.pathname));

  if (!path.startsWith(ROOT)) {
    res.writeHead(403).end("Forbidden");
    return;
  }

  // Fallback SPA: if route is not real, serve just index.html
  let file = path;
  try {
    if (!statSync(path).isFile()) file = join(ROOT, "index.html");
  } catch {
    file = join(ROOT, "index.html");
  }

  const ext = extname(file);
  res.writeHead(200, {
    "Content-Type": MIME[ext] || "application/octet-stream",
    "Cache-Control": ext === ".html" ? "no-cache" : "public, max-age=31536000, immutable",
  });
  createReadStream(file).pipe(res);
}).listen(PORT, () => {
  console.log(`Serving ${ROOT} on :${PORT}`);
});
