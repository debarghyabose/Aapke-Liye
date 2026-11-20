const http = require('http');
const { spawn } = require('child_process');

const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

const proc = spawn(chromePath, [
  '--headless=new',
  '--disable-gpu',
  '--remote-debugging-port=9222',
  '--window-size=360,780',
  '--user-data-dir=C:\\Users\\Public\\ch_cdp',
  'http://localhost:5173/'
]);

setTimeout(async () => {
  try {
    const listRes = await fetch('http://localhost:9222/json');
    const tabs = await listRes.json();
    const pageTab = tabs.find(t => t.type === 'page');
    if (!pageTab) {
      console.log('No page tab found');
      proc.kill();
      return;
    }
    
    // Connect to WebSocket
    const WebSocket = require('node:stream');
    // Using simple fetch to /json/version or evaluate via HTTP if supported
    console.log('Page tab found:', pageTab.webSocketDebuggerUrl);
  } catch (err) {
    console.error(err);
  } finally {
    proc.kill();
  }
}, 2000);

