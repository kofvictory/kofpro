import { contextBridge, ipcRenderer } from 'electron'

// Minimal bridge for the floating コフ window:
// - setSize: grow/shrink the window when the chat panel opens/closes
// - dragStart/dragEnd: コフ本体のドラッグ移動 (movement itself is done in the
//   main process by following the OS cursor)
contextBridge.exposeInMainWorld('kofproFloating', {
  setSize: (width: number, height: number) =>
    ipcRenderer.send('floating:set-size', { width, height }),
  dragStart: () => ipcRenderer.send('floating:drag-start'),
  dragEnd: () => ipcRenderer.send('floating:drag-end'),
})
