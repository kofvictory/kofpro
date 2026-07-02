import { contextBridge, ipcRenderer } from 'electron'

// Minimal bridge for the floating コフ window: it asks the main process to
// resize its own window when the chat panel opens/closes. Nothing else is
// exposed to the renderer.
contextBridge.exposeInMainWorld('kofproFloating', {
  setSize: (width: number, height: number) =>
    ipcRenderer.send('floating:set-size', { width, height }),
})
