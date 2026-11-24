const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const artifactDir = 'C:\\Users\\AHELI JANA\\.gemini\\antigravity\\brain\\47a014b3-2a1b-4109-83de-7d79b0002a26';

const tests = [
  {
    name: 'screen_360_home',
    url: 'http://localhost:5173/',
    size: '360,780',
    mobile: true,
  },
  {
    name: 'screen_360_claim',
    url: 'http://localhost:5173/claim',
    size: '360,780',
    mobile: true,
  },
  {
    name: 'screen_768_home',
    url: 'http://localhost:5173/',
    size: '768,1024',
    mobile: false,
  },
  {
    name: 'screen_768_claim',
    url: 'http://localhost:5173/claim',
    size: '768,1024',
    mobile: false,
  },
  {
    name: 'screen_1280_home',
    url: 'http://localhost:5173/',
    size: '1280,800',
    mobile: false,
  },
  {
    name: 'screen_1280_claim',
    url: 'http://localhost:5173/claim',
    size: '1280,800',
    mobile: false,
  },
];

for (const t of tests) {
  const outPath = path.join(artifactDir, `${t.name}.png`);
  const rand = Math.floor(Math.random() * 100000);
  const tempProfile = `C:\\Users\\Public\\ch_resp_${rand}`;
  
  const args = [
    `"${chromePath}"`,
    '--headless=new',
    '--disable-gpu',
    '--hide-scrollbars',
    `--user-data-dir="${tempProfile}"`,
    `--screenshot="${outPath}"`,
    `--window-size=${t.size}`,
  ];

  if (t.mobile) {
    args.push('--enable-viewport');
    args.push('--user-agent="Mozilla/5.0 (Linux; Android 13; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36"');
  }

  args.push(`"${t.url}"`);

  try {
    execSync(args.join(' '), { timeout: 15000, stdio: 'inherit' });
    if (fs.existsSync(outPath)) {
      console.log(`✓ Saved ${t.name}.png: ${fs.statSync(outPath).size} bytes`);
    }
  } catch (err) {
    console.error(`Error for ${t.name}:`, err.message);
  }
}
