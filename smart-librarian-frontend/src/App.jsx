import { useState } from 'react'

function App() {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [imageLoading, setImageLoading] = useState(false)
  const [error, setError] = useState('')
  const [imageError, setImageError] = useState('')
  const [result, setResult] = useState(null)
  const [imageUrl, setImageUrl] = useState('')

  const handleRecommend = async () => {
    const query = text.trim()
    if (!query) {
      setError('Please enter a request first.')
      setResult(null)
      return
    }

    setLoading(true)
    setError('')
    setImageError('')

    try {
      const response = await fetch('http://localhost:8000/recommend', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
      })

      const data = await response.json()
      if (!response.ok) {
        throw new Error(data?.detail || 'Failed to get recommendation.')
      }

      setResult(data)
      setImageUrl('')
    } catch (err) {
      setResult(null)
      setImageUrl('')
      setError(err instanceof Error ? err.message : 'Unexpected error occurred.')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateImage = async () => {
    if (!result) {
      return
    }

    setImageLoading(true)
    setImageError('')

    try {
      const response = await fetch('http://localhost:8000/image', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: result.recommended_title,
          summary: result.detailed_summary,
        }),
      })

      const data = await response.json()
      if (!response.ok) {
        throw new Error(data?.detail || 'Failed to generate image.')
      }

      setImageUrl(data.image_url || '')
    } catch (err) {
      setImageUrl('')
      setImageError(err instanceof Error ? err.message : 'Unexpected image error occurred.')
    } finally {
      setImageLoading(false)
    }
  }

  return (
    <main style={{ maxWidth: 760, margin: '40px auto', padding: '0 16px', fontFamily: 'Arial, sans-serif' }}>
      <h1>Smart Librarian</h1>
      <p>Describe the kind of book you want, and get a recommendation from the backend.</p>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={5}
        placeholder="I want a book about friendship and magic"
        style={{ width: '100%', padding: 12, fontSize: 16, boxSizing: 'border-box' }}
      />

      <button
        onClick={handleRecommend}
        disabled={loading}
        style={{ marginTop: 12, padding: '10px 16px', fontSize: 16, cursor: loading ? 'not-allowed' : 'pointer' }}
      >
        {loading ? 'Loading...' : 'Recommend a Book'}
      </button>

      {error && (
        <p style={{ color: '#b00020', marginTop: 12 }}>{error}</p>
      )}

      {result && (
        <section style={{ marginTop: 24, border: '1px solid #ddd', borderRadius: 8, padding: 16 }}>
          <h2 style={{ marginTop: 0 }}>Recommended Title</h2>
          <p>{result.recommended_title}</p>

          <h3>Why It Matches</h3>
          <p>{result.why_it_matches}</p>

          <h3>Detailed Summary</h3>
          <p>{result.detailed_summary}</p>

          <button
            onClick={handleGenerateImage}
            disabled={imageLoading}
            style={{ marginTop: 12, padding: '10px 16px', fontSize: 16, cursor: imageLoading ? 'not-allowed' : 'pointer' }}
          >
            {imageLoading ? 'Generating image...' : 'Generate Image'}
          </button>

          {imageError && (
            <p style={{ color: '#b00020', marginTop: 12 }}>{imageError}</p>
          )}

          {imageUrl && (
            <div style={{ marginTop: 16 }}>
              <img
                src={imageUrl}
                alt={`Illustration inspired by ${result.recommended_title}`}
                style={{ width: '100%', maxWidth: 520, borderRadius: 8, border: '1px solid #ddd' }}
              />
            </div>
          )}
        </section>
      )}
    </main>
  )
}

export default App
