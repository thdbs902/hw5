import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The backend only allows this origin (CORS): http://localhost:5173
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
})
