// scripts/check-i18n.js
const fs = require('fs');
const path = require('path');

const localesDir = path.resolve(__dirname, '../src/locales');
const requiredLanguages = ['en', 'hi', 'bn', 'mr', 'ta', 'te'];

function getKeys(obj, prefix = '') {
  let keys = [];
  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      keys = keys.concat(getKeys(value, fullKey));
    } else {
      keys.push(fullKey);
    }
  }
  return keys;
}

function getValue(obj, pathStr) {
  const parts = pathStr.split('.');
  let current = obj;
  for (const part of parts) {
    if (current === undefined || current === null) return undefined;
    current = current[part];
  }
  return current;
}

console.log('🔍 Checking i18n locale files completeness...');

const enPath = path.join(localesDir, 'en.json');
if (!fs.existsSync(enPath)) {
  console.error('❌ Base locale file en.json not found!');
  process.exit(1);
}

const enData = JSON.parse(fs.readFileSync(enPath, 'utf8'));
const enKeys = getKeys(enData);
console.log(`📋 Base locale (en.json) contains ${enKeys.length} total translation keys.`);

let totalErrors = 0;

for (const lang of requiredLanguages) {
  const filePath = path.join(localesDir, `${lang}.json`);
  if (!fs.existsSync(filePath)) {
    console.error(`❌ Locale file missing: ${lang}.json`);
    totalErrors++;
    continue;
  }

  let data;
  try {
    data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (err) {
    console.error(`❌ Error parsing JSON in ${lang}.json:`, err.message);
    totalErrors++;
    continue;
  }

  const missingKeys = [];
  const emptyKeys = [];

  for (const k of enKeys) {
    const val = getValue(data, k);
    if (val === undefined) {
      missingKeys.push(k);
    } else if (typeof val === 'string' && val.trim() === '') {
      emptyKeys.push(k);
    }
  }

  if (missingKeys.length > 0) {
    console.error(`❌ [${lang}] Missing ${missingKeys.length} key(s):`);
    missingKeys.slice(0, 10).forEach((k) => console.error(`    - ${k}`));
    if (missingKeys.length > 10) console.error(`    ... and ${missingKeys.length - 10} more`);
    totalErrors += missingKeys.length;
  }

  if (emptyKeys.length > 0) {
    console.error(`❌ [${lang}] Has ${emptyKeys.length} empty string key(s):`);
    emptyKeys.slice(0, 10).forEach((k) => console.error(`    - ${k}`));
    totalErrors += emptyKeys.length;
  }

  if (missingKeys.length === 0 && emptyKeys.length === 0) {
    console.log(`  ✓ [${lang}] 100% complete (${enKeys.length}/${enKeys.length} keys present)`);
  }
}

if (totalErrors > 0) {
  console.error(`\n❌ i18n check failed with ${totalErrors} total error(s).`);
  process.exit(1);
} else {
  console.log(`\n🎉 Success! All ${requiredLanguages.length} locales are fully synchronized with 0 missing keys.`);
  process.exit(0);
}
