import { app, BrowserWindow, shell } from 'electron'
import { spawn, ChildProcess } from 'child_process'
import * as path from 'path'
import * as http from 'http'

let mainWindow: BrowserWindow | null = null
let serverProcess: ChildProcess | null = null

const DEV_PORT = 3000
const PROD_PORT = 3721

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

app.whenReady().then(async () => {
  if (!isDev()) {
    await startProductionServer()
  }
  await createWindow()

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
