import { resolve } from "node:path";

import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  // Les variables dels fitxers .env NO arriben soles a aquest fitxer: `import.meta.env`
  // només existeix al codi del navegador. Aquí cal carregar-les explícitament, o un
  // VITE_API_TARGET posat a .env.local s'ignoraria en silenci.
  const env = loadEnv(mode, process.cwd());

  // Seguim l'API_PORT del .env de l'arrel, que és on es configura el backend. Així
  // qui hagi de canviar-lo (perquè ja té el 8000 ocupat) no l'ha de repetir aquí.
  const root = loadEnv(mode, resolve(process.cwd(), ".."), "API_PORT");
  const apiTarget = env.VITE_API_TARGET || `http://127.0.0.1:${root.API_PORT || 8000}`;

  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      // Reenviem /api al backend. Així el navegador només veu un origen (el de Vite)
      // i no hi ha ni CORS ni problemes de cookies entre 127.0.0.1 i localhost.
      proxy: {
        "/api": {
          target: apiTarget,
          changeOrigin: false,
        },
      },
    },
  };
});
