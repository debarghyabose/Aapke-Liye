const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const artifactDir = 'C:\\Users\\AHELI JANA\\.gemini\\antigravity\\brain\\47a014b3-2a1b-4109-83de-7d79b0002a26';
const langs = ['en', 'ta', 'te', 'bn', 'hi', 'mr'];

for (const l of langs) {
  const outPath = path.join(artifactDir, `shot_${l}.png`);
  const tempProfile = `C:\\Users\\Public\\ch_tmp_${l}`;
  const url = `http://localhost:5173/?lng=${l}`;
  const args = [
    `"${chromePath}"`,
    '--headless=new',
    '--disable-gpu',
    `--user-data-dir="${tempProfile}"`,
    `--screenshot="${outPath}"`,
    '--window-size=1024,650',
    `"${url}"`
  ].join(' ');

  try {
    execSync(args, { timeout: 15000, stdio: 'inherit' });
    if (fs.existsSync(outPath)) {
      console.log(`Saved shot_${l}.png: ${fs.statSync(outPath).size} bytes`);
    } else {
      console.log(`Failed to create shot_${l}.png`);
    }
  } catch (err) {
    console.error(`Error for ${l}:`, err.message);
  }
}

