import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: true,
        headers: {
          'ngrok-skip-browser-warning': 'true',
        },
        configure: (proxy) => {
          proxy.on('error', (err, _req, res) => {
            console.error('Vite proxy error:', err);
            if (res && !res.headersSent) {
              res.writeHead(502, {
                'Content-Type': 'application/json',
                'X-Proxy-Error': 'true',
              });
              res.end(
                JSON.stringify({
                  error: 'Proxy Error',
                  detail: `Proxy error forwarding to backend: ${err.message || 'Target unavailable'}`,
                })
              );
            }
          });
        },
      },
    },
  },
});
