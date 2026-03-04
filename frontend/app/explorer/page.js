'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'

const STORAGE_KEY = 'api_explorer_key'

export default function ExplorerPage() {
  const [apiKey, setApiKey] = useState('')
  const [games, setGames] = useState([])
  const [game, setGame] = useState('')
  const [query, setQuery] = useState('')
  const [loadingGames, setLoadingGames] = useState(false)
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState('')
  const [results, setResults] = useState([])

  useEffect(() => {
    const storedKey = window.localStorage.getItem(STORAGE_KEY)
    if (storedKey) {
      setApiKey(storedKey)
    }
  }, [])

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, apiKey)
  }, [apiKey])

  const trimmedApiKey = useMemo(() => apiKey.trim(), [apiKey])

  useEffect(() => {
    async function loadGames() {
      setLoadingGames(true)
      setError('')
      try {
        const response = await fetch('/api/v1/games', {
          headers: {
            ...(trimmedApiKey ? { 'X-API-Key': trimmedApiKey } : {}),
          },
        })

        const payload = await response.json().catch(() => ({}))
        if (!response.ok) {
          setGames([])
          setGame('')
          setError(payload?.error || `Error loading games (${response.status})`)
          return
        }

        const gameList = Array.isArray(payload) ? payload : payload?.items || []
        setGames(gameList)
        setGame((currentGame) => {
          if (currentGame && gameList.includes(currentGame)) {
            return currentGame
          }
          return gameList[0] || ''
        })
      } catch (loadError) {
        setGames([])
        setGame('')
        setError(loadError instanceof Error ? loadError.message : String(loadError))
      } finally {
        setLoadingGames(false)
      }
    }

    loadGames()
  }, [trimmedApiKey])

  async function handleSearch(event) {
    event.preventDefault()
    setSearching(true)
    setError('')
    setResults([])

    try {
      const params = new URLSearchParams()
      if (query.trim()) params.set('q', query.trim())
      if (game) params.set('game', game)

      const response = await fetch(`/api/v1/search?${params.toString()}`, {
        headers: {
          ...(trimmedApiKey ? { 'X-API-Key': trimmedApiKey } : {}),
        },
      })
      const payload = await response.json().catch(() => ({}))

      if (!response.ok) {
        setError(payload?.error || `Search failed (${response.status})`)
        return
      }

      const rawItems = Array.isArray(payload) ? payload : payload?.items || []
      const simplified = rawItems.map((item) => ({
        type: item?.type ?? null,
        title: item?.title ?? null,
        subtitle: item?.subtitle ?? null,
        set_code: item?.set_code ?? null,
        collector_number: item?.collector_number ?? null,
        primary_image_url: item?.primary_image_url ?? null,
      }))
      setResults(simplified)
    } catch (searchError) {
      setError(searchError instanceof Error ? searchError.message : String(searchError))
    } finally {
      setSearching(false)
    }
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-4xl flex-col gap-4 p-6">
      <h1 className="text-3xl font-bold">API Explorer</h1>
      <p className="text-sm opacity-80">
        Quick frontend for testing <code>/api/v1</code> endpoints with <code>X-API-Key</code>.
      </p>
      <p className="text-sm opacity-80">
        Public health check: <Link className="underline" href="/api/health">/api/health</Link>
      </p>

      {error && (
        <div className="rounded border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <form onSubmit={handleSearch} className="grid grid-cols-1 gap-3 rounded border p-4 md:grid-cols-2">
        <label className="flex flex-col gap-1 md:col-span-2">
          API Key
          <input
            type="password"
            className="rounded border px-3 py-2"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            placeholder="ak_..."
          />
        </label>

        <label className="flex flex-col gap-1">
          Game
          <select
            className="rounded border px-3 py-2"
            value={game}
            onChange={(event) => setGame(event.target.value)}
            disabled={loadingGames || games.length === 0}
          >
            {games.length === 0 && <option value="">No games available</option>}
            {games.map((gameOption) => (
              <option key={gameOption} value={gameOption}>
                {gameOption}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1">
          Query (q)
          <input
            className="rounded border px-3 py-2"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="pikachu"
          />
        </label>

        <div className="md:col-span-2">
          <button
            type="submit"
            className="rounded bg-black px-4 py-2 text-white disabled:opacity-50"
            disabled={searching || loadingGames}
          >
            {searching ? 'Searching...' : 'Search'}
          </button>
        </div>
      </form>

      <section className="rounded border p-4">
        <h2 className="mb-3 text-lg font-semibold">Results</h2>
        <pre className="overflow-x-auto rounded bg-gray-100 p-3 text-xs">
          {JSON.stringify(results, null, 2)}
        </pre>
      </section>
    </main>
  )
}
