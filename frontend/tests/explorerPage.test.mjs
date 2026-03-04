import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs/promises'

test('explorer page exposes core controls', async () => {
  const page = await fs.readFile(new URL('../app/explorer/page.js', import.meta.url), 'utf8')
  assert.match(page, /API Explorer/)
  assert.match(page, /type="password"/)
  assert.match(page, /\/api\/v1\/games/)
  assert.match(page, /\/api\/v1\/search/)
  assert.match(page, /Search/)
})
