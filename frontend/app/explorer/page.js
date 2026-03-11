'use client'

import { useEffect, useMemo, useState } from 'react'
import AutocompleteList from '../../components/AutocompleteList'
import FiltersBar from '../../components/FiltersBar'
import ResultCard from '../../components/ResultCard'
import SearchBar from '../../components/SearchBar'
import { useDebouncedValue } from '../../hooks/useDebouncedValue'
import { fetchGames, fetchSearch, getApiRuntimeConfig } from '../../lib/apiClient'

const API_KEY_STORAGE = 'tcg_api_key'
const PAGE_SIZE = 24

export default function ExplorerPage() {
  const [query, setQuery] = useState('')
  const [game, setGame] = useState('')
  const [resultType, setResultType] = useState('')
  const [offset, setOffset] = useState(0)

  const [apiKeyInput, setApiKeyInput] = useState('')
  const [apiKey, setApiKey] = useState('')

  const [games, setGames] = useState([])
  const [items, setItems] = useState([])
  const [totalEstimate, setTotalEstimate] = useState(0)
  const [loading, setLoading] = useState(false)
  const [loadingSuggestions, setLoadingSuggestions] = useState(false)
  const [suggestions, setSuggestions] = useState([])
  const [error, setError] = useState('')

  const debouncedQuery = useDebouncedValue(query, 350)
  const runtimeConfig = useMemo(() => getApiRuntimeConfig(), [])

  useEffect(() => {
    const stored = window.localStorage.getItem(API_KEY_STORAGE) || ''
    setApiKeyInput(stored)
    setApiKey(stored)
  }, [])

  useEffect(() => {
    if (!apiKey.trim()) return
    fetchGames(apiKey)
      .then((rows) => setGames(rows || []))
      .catch((requestError) => setError(`No se pudieron cargar juegos: ${requestError.message}`))
  }, [apiKey])

  useEffect(() => {
    if (!apiKey.trim()) return
    setLoading(true)
    setError('')

    fetchSearch({ q: debouncedQuery || 'a', game, type: resultType || undefined, limit: PAGE_SIZE, offset }, apiKey)
      .then((rows) => {
        setItems(rows || [])
        setTotalEstimate((rows || []).length < PAGE_SIZE ? offset + (rows || []).length : offset + PAGE_SIZE + 1)
      })
      .catch((requestError) => {
        setItems([])
        setError(`Error al consultar /search: ${requestError.message}`)
      })
      .finally(() => setLoading(false))
  }, [apiKey, debouncedQuery, game, resultType, offset])

  useEffect(() => {
    if (!apiKey.trim()) return
    if (!debouncedQuery || debouncedQuery.length < 2) {
      setSuggestions([])
      return
    }

    setLoadingSuggestions(true)
    fetchSearch({ q: debouncedQuery, game, type: resultType || undefined, limit: 8, offset: 0 }, apiKey)
      .then((rows) => setSuggestions(rows || []))
      .catch(() => setSuggestions([]))
      .finally(() => setLoadingSuggestions(false))
  }, [apiKey, debouncedQuery, game, resultType])

  function saveApiKey() {
    window.localStorage.setItem(API_KEY_STORAGE, apiKeyInput)
    setApiKey(apiKeyInput)
    setOffset(0)
  }

  function handleSearchChange(nextQuery) {
    setQuery(nextQuery)
    setOffset(0)
  }

  function clearSuggestions() {
    setSuggestions([])
  }

  return (
    <main className="mx-auto min-h-screen max-w-7xl p-6">
      <header className="mb-6">
        <h1 className="text-3xl font-bold text-slate-900">TCG Explorer</h1>
        <p className="text-sm text-slate-600">Buscador y catálogo visual conectado a la API real.</p>
      </header>

      <section className="mb-4 grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm md:grid-cols-[1fr_auto]">
        <label className="text-sm font-medium text-slate-700">X-API-Key
          <input type="password" value={apiKeyInput} onChange={(event) => setApiKeyInput(event.target.value)} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" placeholder="ak_..." />
        </label>
        <button onClick={saveApiKey} type="button" className="rounded-xl bg-slate-900 px-4 py-2 text-white">Guardar clave</button>
        <p className="text-xs text-slate-500 md:col-span-2">Base URL activa: <code>{runtimeConfig.baseUrl}</code></p>
      </section>

      <section className="mb-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="relative">
          <SearchBar value={query} onChange={handleSearchChange} />
          <AutocompleteList items={suggestions} loading={loadingSuggestions} query={query} onSelect={clearSuggestions} />
        </div>
        <div className="mt-4">
          <FiltersBar
            games={games}
            game={game}
            onGameChange={(value) => {
              setGame(value)
              setOffset(0)
            }}
            resultType={resultType}
            onResultTypeChange={(value) => {
              setResultType(value)
              setOffset(0)
            }}
          />
        </div>
      </section>

      {error && <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      {loading && <p className="mb-4 text-sm text-slate-600">Cargando resultados...</p>}

      {!loading && items.length === 0 && <p className="rounded-xl border border-slate-200 bg-white px-4 py-8 text-center text-slate-500">Sin resultados para estos filtros.</p>}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((item) => <ResultCard key={`${item.type}-${item.id}`} item={{ ...item, game_slug: game || 'n/a' }} />)}
      </section>

      <footer className="mt-6 flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4">
        <button
          type="button"
          onClick={() => setOffset((current) => Math.max(current - PAGE_SIZE, 0))}
          disabled={offset === 0 || loading}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:opacity-50"
        >
          Anterior
        </button>
        <p className="text-sm text-slate-600">Offset: {offset} · Mostrando: {items.length}</p>
        <button
          type="button"
          onClick={() => setOffset((current) => current + PAGE_SIZE)}
          disabled={loading || totalEstimate <= offset + PAGE_SIZE}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:opacity-50"
        >
          Siguiente
        </button>
      </footer>
    </main>
  )
}
