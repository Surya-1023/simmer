const API_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
const REQUEST_TIMEOUT_MS = 60_000

export async function getRecommendations(ingredients) {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  try {
    const response = await fetch(`${API_URL}/api/recommend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ingredients }),
      signal: controller.signal,
    })

    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      throw new Error(data.detail || 'Could not get recommendations. Please try again.')
    }
    return data
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('The request took too long. Please try again.')
    }
    if (error instanceof TypeError) {
      throw new Error('Cannot reach the recipe server. Make sure FastAPI is running on port 8000.')
    }
    throw error
  } finally {
    window.clearTimeout(timeoutId)
  }
}


export async function askAssistant(message) {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  try {
    const response = await fetch(`${API_URL}/api/assistant`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
      signal: controller.signal,
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      throw new Error(data.detail || 'Could not answer your cooking question. Please try again.')
    }
    return data
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('The request took too long. Please try again.')
    }
    if (error instanceof TypeError) {
      throw new Error('Cannot reach Simmer. Make sure the FastAPI backend is running on port 8000.')
    }
    throw error
  } finally {
    window.clearTimeout(timeoutId)
  }
}
