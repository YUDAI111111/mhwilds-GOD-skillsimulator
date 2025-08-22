import { defineConfig } from 'vite';
export default defineConfig({
  // GitHub Pages のサブパスに対応。Actions から VITE_BASE=/<repo>/ を渡します。
  base: process.env.VITE_BASE || '/'
});
