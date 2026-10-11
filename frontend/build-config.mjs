import { cp, mkdir, readdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const sourceDirectory = fileURLToPath(new URL('.', import.meta.url));
const publishDirectory = join(sourceDirectory, 'deploy-dist');
const frontendDirectory = join(publishDirectory, 'frontend');
const apiBaseUrl = (process.env.API_BASE_URL || '').replace(/\/+$/, '');

if (!apiBaseUrl && process.env.NODE_ENV === 'production') {
  throw new Error('Set API_BASE_URL to the HTTPS URL of the deployed Django API.');
}
if (apiBaseUrl) {
  const apiUrl = new URL(apiBaseUrl);
  if (apiUrl.protocol !== 'https:' || apiUrl.pathname !== '/' || apiUrl.search || apiUrl.hash) {
    throw new Error('API_BASE_URL must be the HTTPS origin of the production API, without a path.');
  }
}

await mkdir(frontendDirectory, { recursive: true });
for (const entry of await readdir(sourceDirectory)) {
  if (entry === 'deploy-dist' || entry === 'node_modules') continue;
  await cp(join(sourceDirectory, entry), join(frontendDirectory, entry), {
    recursive: true,
    force: true,
  });
}

await writeFile(
  join(frontendDirectory, 'js', 'deploy-config.js'),
  `window.SMART_EXPENSE_API_BASE_URL = ${JSON.stringify(`${apiBaseUrl}/api`)};\n`,
  'utf8',
);
await writeFile(
  join(publishDirectory, 'index.html'),
  '<!doctype html><html><head><meta http-equiv="refresh" content="0;url=/frontend/index.html"></head><body><script>location.replace("/frontend/index.html");</script></body></html>\n',
  'utf8',
);
