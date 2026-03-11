import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs/promises'

test('explorer page includes search, filters and api key flow', async () => {
  const page = await fs.readFile(new URL('../app/explorer/page.js', import.meta.url), 'utf8')

  assert.match(page, /TCG Explorer/)
  assert.match(page, /X-API-Key/)
  assert.match(page, /fetchGames\(apiKey\)/)
  assert.match(page, /fetchSearch\(/)
  assert.match(page, /AutocompleteList/)
  assert.match(page, /FiltersBar/)
  assert.match(page, /ResultCard/)
  assert.match(page, /Cargando resultados/)
  assert.match(page, /Sin resultados para estos filtros/)
  assert.match(page, /window\.localStorage\.setItem\(API_KEY_STORAGE, apiKeyInput\)/)
})

test('api client uses env base url and X-API-Key support', async () => {
  const apiClient = await fs.readFile(new URL('../lib/apiClient.js', import.meta.url), 'utf8')

  assert.match(apiClient, /NEXT_PUBLIC_API_BASE_URL/)
  assert.match(apiClient, /NEXT_PUBLIC_API_KEY/)
  assert.match(apiClient, /X-API-Key/)
  assert.match(apiClient, /\/api\/v1\/search/)
  assert.match(apiClient, /\/api\/v1\/games/)
  assert.match(apiClient, /\/api\/v1\/cards\//)
  assert.match(apiClient, /\/api\/v1\/prints\//)
})
