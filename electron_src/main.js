const electron = require('electron');
const { app, BrowserWindow, ipcMain } = electron;
const path = require('path');
const { spawn } = require('child_process');

console.log('----------------------------------------------------------------');
console.log('[DEBUG] Process ExecPath:', process.execPath);
console.log('[DEBUG] Process Versions:', process.versions);
console.log('[DEBUG] Electron require type:', typeof electron);
try {
    console.log('[DEBUG] Electron resolve:', require.resolve('electron'));
} catch (e) { console.log('[DEBUG] Electron resolve failed:', e.message); }

if (!app) {
    console.error("FATAL ERROR: 'app' is undefined.");
    console.error("Running Environment: " + (process.versions.electron ? "Electron" : "Node.js"));
    console.error("This script must be run within the Electron Runtime.");
    process.exit(1);
}

// Use ANGLE D3D11 backend - more stable on Windows while keeping WebGL working
app.commandLine.appendSwitch('use-angle', 'd3d11');
app.commandLine.appendSwitch('enable-features', 'Vulkan');
app.commandLine.appendSwitch('ignore-gpu-blocklist');

// Basic file logger for production debugging
const fs = require('fs');
const logFile = path.join(app.getPath('userData'), 'main_process_log.txt');

function logToFile(msg) {
    const time = new Date().toISOString();
    const logParams = [`[${time}] ${msg}\n`];
    try {
        fs.appendFileSync(logFile, logParams.join(' '));
    } catch (e) {
        // ignore
    }
}

// Override console logging
const originalLog = console.log;
const originalError = console.error;

console.log = (...args) => {
    logToFile('[INFO] ' + args.join(' '));
    try {
        originalLog(...args);
    } catch (e) {
        // Ignore EPIPE or other logging errors
    }
};

console.error = (...args) => {
    logToFile('[ERROR] ' + args.join(' '));
    try {
        originalError(...args);
    } catch (e) {
        // Ignore EPIPE or other logging errors
    }
};

console.log("----------------------------------------------------------------");
console.log("R.E.X Main Process Started");
console.log(`Log File: ${logFile}`);
console.log(`Resources Path: ${process.resourcesPath}`);

let mainWindow;
let minimalWindow;
let pythonProcess;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1920,
        height: 1080,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false, // For simple IPC/Socket.IO usage
        },
        backgroundColor: '#000000',
        frame: false, // Frameless for custom UI
        titleBarStyle: 'hidden',
        show: false, // Don't show until ready
    });

    // In dev, load Vite server. In prod, load index.html
    const isDev = !app.isPackaged;

    const loadFrontend = (retries = 3) => {
        const url = isDev ? 'http://127.0.0.1:5173' : null;
        const loadPromise = isDev
            ? mainWindow.loadURL(url)
            : mainWindow.loadFile(path.join(__dirname, '../dist-frontend/index.html'));

        loadPromise
            .then(() => {
                console.log('Frontend loaded successfully!');
                windowWasShown = true;
                mainWindow.show();
                if (isDev) {
                    mainWindow.webContents.openDevTools();
                }
            })
            .catch((err) => {
                console.error(`Failed to load frontend: ${err.message}`);
                if (retries > 0) {
                    console.log(`Retrying in 1 second... (${retries} retries left)`);
                    setTimeout(() => loadFrontend(retries - 1), 1000);
                } else {
                    console.error('Failed to load frontend after all retries. Keeping window open.');
                    windowWasShown = true;
                    mainWindow.show();
                }
            });
    };

    loadFrontend();

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

function createMinimalWindow() {
    minimalWindow = new BrowserWindow({
        width: 650,
        height: 70,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
        },
        transparent: true,
        frame: false,
        alwaysOnTop: true,
        resizable: false,
        skipTaskbar: true,
        show: false,
        hasShadow: false,
    });

    const isDev = !app.isPackaged;
    const url = isDev ? 'http://127.0.0.1:5173/minimal.html' : null;
    const loadPromise = isDev
        ? minimalWindow.loadURL(url)
        : minimalWindow.loadFile(path.join(__dirname, '../dist-frontend/minimal.html'));

    loadPromise.then(() => {
        console.log('Minimal window loaded successfully!');
        minimalWindow.show();
        if (isDev) {
            minimalWindow.webContents.openDevTools();
        }
    }).catch((err) => {
        console.error(`Failed to load minimal window: ${err.message}`);
    });

    minimalWindow.on('closed', () => {
        minimalWindow = null;
    });
}

function startPythonBackend() {
    let scriptPath;
    let pythonExecutable;
    let args = [];

    const isDev = !app.isPackaged;

    if (isDev) {
        scriptPath = path.join(__dirname, '../backend/server.py');
        const venvPython = path.join(__dirname, '../venv/Scripts/python.exe');
        pythonExecutable = require('fs').existsSync(venvPython) ? venvPython : 'python';
        args = [scriptPath];
        console.log(`Starting Python backend (Dev): ${scriptPath} with ${pythonExecutable}`);
    } else {
        // Production: Executable should be in resources/backend/server/server.exe
        const exePath = path.join(process.resourcesPath, 'backend/server/server.exe');
        console.log(`Starting Python backend (Prod): ${exePath}`);

        if (require('fs').existsSync(exePath)) {
            pythonExecutable = exePath;
            args = [];
        } else {
            console.error(`Backend executable not found at: ${exePath}`);
            return;
        }
    }

    // In prod, this would be the executable.
    pythonProcess = spawn(pythonExecutable, args, {
        cwd: isDev ? path.join(__dirname, '../') : path.dirname(pythonExecutable),
    });

    pythonProcess.stdout.on('data', (data) => {
        console.log(`[Python]: ${data}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`[Python Error]: ${data}`);
    });
}

app.whenReady().then(() => {
    ipcMain.on('window-minimize', () => {
        if (mainWindow) mainWindow.minimize();
    });

    ipcMain.on('window-maximize', () => {
        if (mainWindow) {
            if (mainWindow.isMaximized()) {
                mainWindow.unmaximize();
            } else {
                mainWindow.maximize();
            }
        }
    });

    ipcMain.on('window-close', () => {
        if (mainWindow) mainWindow.close();
    });

    checkBackendPort(8000).then((isTaken) => {
        if (isTaken) {
            console.log('Port 8000 is taken. Assuming backend is already running manually.');
            waitForBackend().then(createWindow);
        } else {
            startPythonBackend();
            // Give it a moment to start, then wait for health check
            setTimeout(() => {
                waitForBackend().then(createWindow);
            }, 1000);
        }
    });

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
});

function checkBackendPort(port) {
    return new Promise((resolve) => {
        const net = require('net');
        const server = net.createServer();
        server.once('error', (err) => {
            if (err.code === 'EADDRINUSE') {
                resolve(true);
            } else {
                resolve(false);
            }
        });
        server.once('listening', () => {
            server.close();
            resolve(false);
        });
        server.listen(port);
    });
}

function waitForBackend() {
    return new Promise((resolve) => {
        const check = () => {
            const http = require('http');
            http.get('http://127.0.0.1:8000/status', (res) => {
                if (res.statusCode === 200) {
                    console.log('Backend is ready!');
                    resolve();
                } else {
                    console.log('Backend not ready, retrying...');
                    setTimeout(check, 1000);
                }
            }).on('error', (err) => {
                console.log('Waiting for backend...');
                setTimeout(check, 1000);
            });
        };
        check();
    });
}

let windowWasShown = false;

app.on('window-all-closed', () => {
    // Only quit if the window was actually shown at least once
    // This prevents quitting during startup if window creation fails
    if (process.platform !== 'darwin' && windowWasShown) {
        app.quit();
    } else if (!windowWasShown) {
        console.log('Window was never shown - keeping app alive to allow retries');
    }
});

// IPC Handlers for window switching
ipcMain.on('switch-to-minimal', () => {
    console.log('Switching to minimal mode...');
    if (mainWindow) {
        mainWindow.close();
        mainWindow = null;
    }
    if (!minimalWindow) {
        createMinimalWindow();
    }
});

ipcMain.on('switch-to-full', () => {
    console.log('Switching to full UI...');
    if (minimalWindow) {
        minimalWindow.close();
        minimalWindow = null;
    }
    if (!mainWindow) {
        createWindow();
    }
});

app.on('will-quit', () => {
    console.log('App closing... Killing Python backend.');
    if (pythonProcess) {
        // If it's a frozen exe, process.pid works the same.
        // Taskkill is robust on Windows.
        if (process.platform === 'win32') {
            try {
                const { execSync } = require('child_process');
                execSync(`taskkill /pid ${pythonProcess.pid} /f /t`);
            } catch (e) {
                console.error('Failed to kill python process:', e.message);
            }
        } else {
            pythonProcess.kill('SIGKILL');
        }
        pythonProcess = null;
    }
});
