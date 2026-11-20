const fs = require('fs');
const path = require('path');

function walk(dir) {
  const files = fs.readdirSync(dir);
  for (const f of files) {
    const p = path.join(dir, f);
    if (fs.statSync(p).isDirectory()) {
      walk(p);
    } else if (/\.(tsx|css)$/.test(f)) {
      const lines = fs.readFileSync(p, 'utf8').split('\n');
      lines.forEach((l, i) => {
        const m = l.match(/(width|minWidth|maxWidth|min-width):\s*['"]?(\d{3,4})px/);
        if (m && parseInt(m[2]) > 300) {
          console.log(`${p.split('src')[1]}:${i + 1}: ${l.trim()}`);
        }
      });
    }
  }
}

walk(path.join(__dirname, '..', 'src'));

