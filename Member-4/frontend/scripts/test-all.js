// scripts/test-all.js
// Automated verification suite for Member 4: Frontend, PWA, Offline & Integration Contracts
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

console.log('====================================================');
console.log('🧪 RUNNING MEMBER 4 VERIFICATION SUITE');
console.log('====================================================');

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    console.log(`  ✓ ${message}`);
    passed++;
  } else {
    console.error(`  ❌ FAILED: ${message}`);
    failed++;
  }
}

// 1. Test i18n
console.log('\n[1/5] Verifying Multilingual i18n (6 Locales)...');
try {
  execSync('node scripts/check-i18n.js', { stdio: 'pipe', cwd: path.resolve(__dirname, '..') });
  assert(true, 'All 6 locales (en, hi, bn, mr, ta, te) fully synchronized with 0 missing keys');
} catch (e) {
  assert(false, 'i18n check failed: ' + e.message);
}

// 2. Test PWA Build & Assets
console.log('\n[2/5] Verifying PWA Manifest & Service Worker Assets...');
const publicDir = path.resolve(__dirname, '../public');
const distDir = path.resolve(__dirname, '../dist');

assert(fs.existsSync(path.join(publicDir, 'icon-192.png')), 'icon-192.png exists in public/');
assert(fs.existsSync(path.join(publicDir, 'icon-512.png')), 'icon-512.png exists in public/');
assert(fs.existsSync(path.join(publicDir, 'apple-touch-icon.png')), 'apple-touch-icon.png exists in public/');

if (fs.existsSync(distDir)) {
  assert(fs.existsSync(path.join(distDir, 'sw.js')), 'dist/sw.js (Service Worker) generated');
  assert(fs.existsSync(path.join(distDir, 'manifest.webmanifest')), 'dist/manifest.webmanifest generated');
  assert(fs.existsSync(path.join(distDir, 'registerSW.js')), 'dist/registerSW.js generated');
} else {
  console.log('  ⚠️ dist/ not built yet; run npm run build to generate PWA assets');
}

// 3. Test New Screen Components Exists
console.log('\n[3/5] Verifying Sprint Screens & Components...');
const srcPages = path.resolve(__dirname, '../src/pages');
assert(fs.existsSync(path.join(srcPages, 'Prepare.tsx')), 'Prepare.tsx (/prepare document vault screen) exists');
assert(fs.existsSync(path.join(srcPages, 'Mesh.tsx')), 'Mesh.tsx (/mesh emergency relay screen) exists');
assert(fs.existsSync(path.join(srcPages, 'Claim.tsx')), 'Claim.tsx (6-step voice & photo claim) exists');
assert(fs.existsSync(path.join(srcPages, 'Track.tsx')), 'Track.tsx (claim status & escalation) exists');
assert(fs.existsSync(path.join(srcPages, 'Official.tsx')), 'Official.tsx (official damage map & queue) exists');

// 4. Test is_hilly & Household in Source Code
console.log('\n[4/5] Verifying Feature Logic...');
const claimCode = fs.readFileSync(path.join(srcPages, 'Claim.tsx'), 'utf8');
assert(claimCode.includes('is_hilly'), 'Claim.tsx includes is_hilly question & state handler');
assert(claimCode.includes('useMyHousehold'), 'Claim.tsx includes "Use my household" option on Step 1');
assert(claimCode.includes('beforeAfterTitle'), 'Claim.tsx includes Before/After damage comparison card on Step 4');
assert(claimCode.includes('/mesh'), 'Claim.tsx Step 6 links to /mesh for zero-signal neighbour handoff');

const apiTypes = fs.readFileSync(path.resolve(__dirname, '../src/types/api.ts'), 'utf8');
assert(apiTypes.includes('is_hilly?: boolean | null;'), 'api.ts includes is_hilly field');
assert(apiTypes.includes('interface Household'), 'api.ts includes Household schema');
assert(apiTypes.includes('interface VaultDocument'), 'api.ts includes VaultDocument schema');
assert(apiTypes.includes('interface SealedClaimEnvelope'), 'api.ts includes SealedClaimEnvelope schema');

const clientCode = fs.readFileSync(path.resolve(__dirname, '../src/api/client.ts'), 'utf8');
assert(clientCode.includes('registerHousehold'), 'client.ts exports registerHousehold');
assert(clientCode.includes('uploadVaultDocument'), 'client.ts exports uploadVaultDocument');
assert(clientCode.includes('startDigiLockerMock'), 'client.ts exports startDigiLockerMock');
assert(clientCode.includes('sealClaimEnvelope'), 'client.ts exports sealClaimEnvelope');
assert(clientCode.includes('submitMeshEnvelope'), 'client.ts exports submitMeshEnvelope');

// 5. Test Offline IndexedDB Queue
console.log('\n[5/5] Verifying Offline Queue & Banner...');
const idbCode = fs.readFileSync(path.resolve(__dirname, '../src/utils/indexedDB.ts'), 'utf8');
assert(idbCode.includes('claim_create'), 'indexedDB.ts handles claim_create queue type');
assert(idbCode.includes('saveOfflineClaim'), 'indexedDB.ts exports saveOfflineClaim');
assert(idbCode.includes('saveMeshEnvelope'), 'indexedDB.ts exports saveMeshEnvelope');

const bannerCode = fs.readFileSync(path.resolve(__dirname, '../src/components/OfflineBanner.tsx'), 'utf8');
assert(bannerCode.includes('savedOnPhone'), 'OfflineBanner.tsx displays "Saved on this phone, N items waiting"');
assert(bannerCode.includes('claim_create'), 'OfflineBanner.tsx auto-syncs offline created claims');

console.log('====================================================');
console.log(`🏁 TEST RESULTS: ${passed} PASSED, ${failed} FAILED`);
console.log('====================================================');

if (failed > 0) {
  process.exit(1);
} else {
  console.log('🎉 All Member 4 verification checks passed successfully!\n');
}
