import { defineConfig } from 'vite';
export default defineConfig({
  // GitHub Pages サブパスでも壊れないように base を注入
  base: process.env.VITE_BASE || '/'
});
