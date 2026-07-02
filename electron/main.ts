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
const FLOAT_INITIAL = { width: 96, height: 96 }
const FLOAT_MARGIN = 16

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

// Always-on-top frameless mini window where コフ lives permanently.
// Survives minimizing (or even closing) the main window. Minimal scope:
// always-on-top + click to open the chat + drag to move (via CSS app-region).
// No transparency — a small rounded card reads fine on camera and avoids
// the transparent-window rabbit hole.
function createFloatingWindow(): void {
  const { workArea } = screen.getPrimaryDisplay()

  floatingWindow = new BrowserWindow({
    width: FLOAT_INITIAL.width,
    height: FLOAT_INITIAL.height,
    x: workArea.x + workArea.width - FLOAT_INITIAL.width - FLOAT_MARGIN,
    y: workArea.y + workArea.height - FLOAT_INITIAL.height - FLOAT_MARGIN,
    frame: false,
    alwaysOnTop: true,
    resizable: false,
    skipTaskbar: true,
    minimizable: false,
    maximizable: false,
    fullscreenable: false,
    backgroundColor: '#f9fafb',
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
  floatingWindow.on('closed', () => { floatingWindow = null })
}

// The floating window asks to be resized when the chat panel opens/closes.
// Keep the bottom-right corner anchored so コフ stays where the user put it.
ipcMain.on('floating:set-size', (_event, { width, height }: { width: number; height: number }) => {
  if (!floatingWindow) return
  const b = floatingWindow.getBounds()
  const bounds = {
    x: b.x + b.width - width,
    y: b.y + b.height - height,
    width,
    height,
  }
  // resizable:false blocks programmatic resize on some platforms — toggle it.
  floatingWindow.setResizable(true)
  floatingWindow.setBounds(bounds)
  floatingWindow.setResizable(false)
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
