const electron = require('electron');
console.log('Electron object keys:', Object.keys(electron));
if (electron.app) {
    console.log('App is defined');
    electron.app.quit();
} else {
    console.log('App is UNDEFINED');
}
