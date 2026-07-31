import { app, BrowserWindow, shell, ipcMain, screen } from 'electron'
import { spawn, ChildProcess } from 'child_process'
import * as path from 'path'
import * as http from 'http'

let mainWindow: BrowserWindow | null = null
let floatingWindow: BrowserWindow | null = null
let serverProcess: ChildProcess | null = null

const DEV_PORT = 3000
const PROD_PORT = 3721

// Initial (closed / avatar-only) size of the floating コフ window.
// Must match FLOAT_CLOSED in src/components/DesktopAgent.tsx.
const FLOAT_INITIAL = { width: 112, height: 112 }
const FLOAT_MARGIN = 16

// Set to false to fall back to the opaque card look if the transparent
// window misbehaves on some machine (known Electron escape hatch).
const FLOAT_TRANSPARENT = true

function isDev(): boolean {
  return !app.isPackaged
}

function getPort(): number {
  return isDev() ? DEV_PORT : PROD_PORT
}

function waitForServer(port: number, timeoutMs = 30000): Promise<void> {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeoutMs
    const check = () => {
      http
        .get(`http://localhost:${port}`, (res) => {
          // Any response means the server is up
          res.destroy()
          resolve()
        })
        .on('error', () => {
          if (Date.now() > deadline) {
            reject(new Error(`Server did not start within ${timeoutMs}ms`))
          } else {
            setTimeout(check, 500)
          }
        })
    }
    check()
  })
}

async function startProductionServer(): Promise<void> {
  // Next.js standalone server lives in resources/app/.next/standalone/server.js
  const serverJs = path.join(
    process.resourcesPath,
    'app',
    '.next',
    'standalone',
    'server.js'
  )

  serverProcess = spawn(process.execPath, [serverJs], {
    env: {
      ...process.env,
      PORT: String(PROD_PORT),
      NODE_ENV: 'production',
      HOSTNAME: '127.0.0.1',
    },
    stdio: 'pipe',
  })

  serverProcess.stdout?.on('data', (d: Buffer) => console.log('[next]', d.toString()))
  serverProcess.stderr?.on('data', (d: Buffer) => console.error('[next]', d.toString()))

  await waitForServer(PROD_PORT)
}

async function createWindow(): Promise<void> {
  mainWindow = new BrowserWindow({
    width: 960,
    height: 720,
    minWidth: 600,
    minHeight: 500,
    title: 'KofPro',
    backgroundColor: '#f9fafb',
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    },
  })

  // Open external links in the system browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  mainWindow.loadURL(`http://localhost:${getPort()}`)

  mainWindow.once('ready-to-show', () => mainWindow?.show())
  mainWindow.on('closed', () => { mainWindow = null })
}

// Push a window rect fully inside the work area of the nearest display.
// Fixes the first-launch clipping seen on scaled / multi-monitor setups
// and keeps the window reachable after drags and panel-open growth.
function clampToWorkArea(bounds: Electron.Rectangle): Electron.Rectangle {
  const wa = screen.getDisplayMatching(bounds).workArea
  return {
    width: bounds.width,
    height: bounds.height,
    x: Math.min(Math.max(bounds.x, wa.x), wa.x + wa.width - bounds.width),
    y: Math.min(Math.max(bounds.y, wa.y), wa.y + wa.height - bounds.height),
  }
}

// Always-on-top frameless transparent window where コフ lives permanently.
// Survives minimizing (or even closing) the main window. Only コフ and the
// bubble are visible — the rest of the window is transparent. To keep the
// invisible click-blocking area tiny, the window stays avatar-sized while
// closed and grows only while the chat panel is open. Click-through is
// intentionally NOT used (out of scope).
function createFloatingWindow(): void {
  const { workArea } = screen.getPrimaryDisplay()

  floatingWindow = new BrowserWindow({
    ...clampToWorkArea({
      width: FLOAT_INITIAL.width,
      height: FLOAT_INITIAL.height,
      x: workArea.x + workArea.width - FLOAT_INITIAL.width - FLOAT_MARGIN,
      y: workArea.y + workArea.height - FLOAT_INITIAL.height - FLOAT_MARGIN,
    }),
    frame: false,
    transparent: FLOAT_TRANSPARENT,
    alwaysOnTop: true,
    resizable: false,
    skipTaskbar: true,
    minimizable: false,
    maximizable: false,
    fullscreenable: false,
    hasShadow: false,
    backgroundColor: FLOAT_TRANSPARENT ? '#00000000' : '#f9fafb',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    },
  })

  floatingWindow.loadURL(`http://localhost:${getPort()}/floating`)
  floatingWindow.once('ready-to-show', () => floatingWindow?.show())
  floatingWindow.on('closed', () => {
    stopFloatingDrag()
    floatingWindow = null
  })
}

function setFloatingBounds(bounds: Electron.Rectangle): void {
  if (!floatingWindow) return
  // resizable:false blocks programmatic resize on some platforms — toggle it.
  floatingWindow.setResizable(true)
  floatingWindow.setBounds(clampToWorkArea(bounds))
  floatingWindow.setResizable(false)
}

// The floating window asks to be resized when the chat panel opens/closes.
// Keep the bottom-right corner anchored so コフ stays where the user put it.
ipcMain.on('floating:set-size', (_event, { width, height }: { width: number; height: number }) => {
  if (!floatingWindow) return
  const b = floatingWindow.getBounds()
  setFloatingBounds({
    x: b.x + b.width - width,
    y: b.y + b.height - height,
    width,
    height,
  })
})

// --- コフ本体のドラッグ移動 ---------------------------------------------
// The renderer only signals drag start/end; the actual movement is done here
// by polling the OS cursor. This avoids renderer/DIP coordinate mismatches
// and keeps working even if the cursor briefly outruns mousemove events
// (the window chases the cursor, so it never escapes).
let dragTimer: ReturnType<typeof setInterval> | null = null

function stopFloatingDrag(): void {
  if (dragTimer) {
    clearInterval(dragTimer)
    dragTimer = null
  }
}

ipcMain.on('floating:drag-start', () => {
  if (!floatingWindow || dragTimer) return
  const cursorStart = screen.getCursorScreenPoint()
  const [winX, winY] = floatingWindow.getPosition()

  dragTimer = setInterval(() => {
    if (!floatingWindow) return stopFloatingDrag()
    const c = screen.getCursorScreenPoint()
    floatingWindow.setPosition(winX + c.x - cursorStart.x, winY + c.y - cursorStart.y)
  }, 16)
})

ipcMain.on('floating:drag-end', () => {
  stopFloatingDrag()
  if (floatingWindow) {
    // Snap back inside the work area if dropped half off-screen.
    floatingWindow.setBounds(clampToWorkArea(floatingWindow.getBounds()))
  }
})

app.whenReady().then(async () => {
  if (!isDev()) {
    await startProductionServer()
  }
  await createWindow()
  createFloatingWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('will-quit', () => {
  serverProcess?.kill()
})
