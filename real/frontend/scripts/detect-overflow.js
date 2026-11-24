const http = require('http');
const { execSync } = require('child_process');

let results = null;

const server = http.createServer((req, res) => {
  if (req.method === 'POST') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      results = JSON.parse(body);
      res.writeHead(200);
      res.end('OK');
    });
  } else {
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(`
      <!DOCTYPE html>
      <html><body>
      <iframe id="f" src="http://localhost:5173/" style="width:360px;height:780px;border:none;"></iframe>
      <script>
        setTimeout(() => {
          const doc = document.getElementById('f').contentDocument;
          const overflows = [];
          doc.querySelectorAll('*').forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.right > 361 || el.scrollWidth > 361) {
              overflows.push({
                tag: el.tagName,
                class: el.className,
                rectRight: Math.round(rect.right),
                sw: el.scrollWidth,
                text: (el.innerText || '').slice(0, 40).replace(/\\n/g, ' ')
              });
            }
          });
          fetch('http://localhost:8999', { method: 'POST', body: JSON.stringify(overflows) });
        }, 2000);
      </script>
      </body></html>
    `);
  }
});

server.listen(8999, () => {
  const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
  const cmd = `"${chromePath}" --headless=new --disable-gpu --user-data-dir="C:\\Users\\Public\\ch_diag" "http://localhost:8999"`;
  try {
    execSync(cmd, { timeout: 8000 });
  } catch (e) {}

  setTimeout(() => {
    if (results) {
      console.log('=== OVERFLOW ELEMENTS (count: ' + results.length + ') ===');
      results.forEach(r => console.log(r.tag + '.' + r.class + ' right=' + r.rectRight + ' sw=' + r.sw + ' | ' + r.text));
    } else {
      console.log('No results received');
    }
    server.close();
    process.exit(0);
  }, 1000);
});
