const { execSync } = require('child_process');
const fs = require('fs');

const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

const html = `
<!DOCTYPE html>
<html>
<body>
<script>
window.location.href = 'http://localhost:5173/';
</script>
</body>
</html>
`;

// Let's run chrome with remote debugging or evaluate script in page
const script = `
const http = require('http');
const s = http.createServer((req, res) => {
  let b = '';
  req.on('data', c => b += c);
  req.on('end', () => {
    console.log('CLIENT DATA:', b);
    res.end('OK');
    process.exit(0);
  });
});
s.listen(9123);
`;
fs.writeFileSync('C:\\Users\\Public\\vp_server.js', script);

