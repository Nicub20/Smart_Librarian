import { useState } from 'react'

function App() {
  const [text, setText] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [mediaRecorder, setMediaRecorder] = useState(null)
  const [audioChunks, setAudioChunks] = useState([])
  const [transcriptionLanguage, setTranscriptionLanguage] = useState('Auto')
  const [transcribing, setTranscribing] = useState(false)
  const [loading, setLoading] = useState(false)
  const [imageLoading, setImageLoading] = useState(false)
  const [audioLoading, setAudioLoading] = useState(false)
  const [error, setError] = useState('')
  const [transcriptionError, setTranscriptionError] = useState('')
  const [transcriptionInfo, setTranscriptionInfo] = useState('')
  const [imageError, setImageError] = useState('')
  const [audioError, setAudioError] = useState('')
  const [result, setResult] = useState(null)
  const [imageUrl, setImageUrl] = useState('')
  const [audioUrl, setAudioUrl] = useState('')

  const clearAudioUrl = () => {
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl)
    }
    setAudioUrl('')
  }

  const buildAudioText = (bookResult) => {
    const recommendedTitle = bookResult?.recommended_title || 'Unknown'
    const whyItMatches = bookResult?.why_it_matches || 'No explanation available.'
    const detailedSummary = bookResult?.detailed_summary || 'No detailed summary available.'

    return `Recommended title: ${recommendedTitle}. Why it matches: ${whyItMatches}. Detailed summary: ${detailedSummary}`
  }

  const transcribeRecordedAudio = async (chunks, mimeType) => {
    setTranscribing(true)
    setTranscriptionError('')
    setTranscriptionInfo('')

    try {
      if (!chunks.length) {
        throw new Error('No audio captured. Please try recording again.')
      }

      const audioBlob = new Blob(chunks, { type: mimeType || 'audio/webm' })
      const formData = new FormData()
      formData.append('audio_file', audioBlob, 'recording.webm')

      const languageMap = {
        Auto: null,
        English: 'en',
        Romanian: 'ro',
      }
      const languageCode = languageMap[transcriptionLanguage]
      if (languageCode) {
        formData.append('language', languageCode)
      }

      const response = await fetch('http://localhost:8000/stt', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()
      if (!response.ok) {
        throw new Error(data?.detail || 'Failed to transcribe audio.')
      }

      setText(data?.transcript || '')
      setTranscriptionInfo('Transcript loaded into the request box.')
    } catch (err) {
      setTranscriptionInfo('')
      setTranscriptionError(err instanceof Error ? err.message : 'Unexpected transcription error occurred.')
    } finally {
      setTranscribing(false)
    }
  }

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
    setAudioError('')

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
      clearAudioUrl()
    } catch (err) {
      setResult(null)
      setImageUrl('')
      clearAudioUrl()
      setError(err instanceof Error ? err.message : 'Unexpected error occurred.')
    } finally {
      setLoading(false)
    }
  }

  const handleStartRecording = async () => {
    if (isRecording) {
      return
    }

    setTranscriptionError('')
    setTranscriptionInfo('')

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      const localChunks = []

      setAudioChunks([])

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          localChunks.push(event.data)
          setAudioChunks((prev) => [...prev, event.data])
        }
      }

      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop())
        setIsRecording(false)
        await transcribeRecordedAudio(localChunks, recorder.mimeType)
        setAudioChunks([])
        setMediaRecorder(null)
      }

      recorder.start()
      setMediaRecorder(recorder)
      setIsRecording(true)
    } catch (err) {
      setTranscriptionInfo('')
      setTranscriptionError(err instanceof Error ? err.message : 'Could not access microphone.')
    }
  }

  const handleStopRecording = () => {
    if (!mediaRecorder || mediaRecorder.state === 'inactive') {
      return
    }

    mediaRecorder.stop()
    setIsRecording(false)
  }

  const handleGenerateAudio = async () => {
    if (!result) {
      return
    }

    setAudioLoading(true)
    setAudioError('')

    try {
      const combinedText = buildAudioText(result)
      const response = await fetch('http://localhost:8000/tts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: combinedText,
        }),
      })

      if (!response.ok) {
        let message = 'Failed to generate audio.'
        try {
          const data = await response.json()
          message = data?.detail || message
        } catch {
          // Keep default message if response is not JSON.
        }
        throw new Error(message)
      }

      const blob = await response.blob()
      const nextAudioUrl = URL.createObjectURL(blob)
      clearAudioUrl()
      setAudioUrl(nextAudioUrl)
    } catch (err) {
      clearAudioUrl()
      setAudioError(err instanceof Error ? err.message : 'Unexpected audio error occurred.')
    } finally {
      setAudioLoading(false)
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

      <section style={{ marginBottom: 16, border: '1px solid #ddd', borderRadius: 8, padding: 12 }}>
        <h3 style={{ marginTop: 0 }}>Voice Mode</h3>

        <div style={{ marginTop: 8 }}>
          <label htmlFor="voice-language" style={{ marginRight: 8 }}>Language:</label>
          <select
            id="voice-language"
            value={transcriptionLanguage}
            onChange={(e) => setTranscriptionLanguage(e.target.value)}
            disabled={isRecording || transcribing}
          >
            <option>Auto</option>
            <option>English</option>
            <option>Romanian</option>
          </select>
        </div>

        <button
          onClick={handleStartRecording}
          disabled={isRecording || transcribing}
          style={{ marginTop: 10, padding: '8px 14px', fontSize: 14, cursor: (isRecording || transcribing) ? 'not-allowed' : 'pointer' }}
        >
          Start Recording
        </button>

        <button
          onClick={handleStopRecording}
          disabled={!isRecording}
          style={{ marginTop: 10, marginLeft: 8, padding: '8px 14px', fontSize: 14, cursor: !isRecording ? 'not-allowed' : 'pointer' }}
        >
          Stop Recording
        </button>

        {isRecording && (
          <p style={{ color: '#0b5', marginTop: 10 }}>Recording...</p>
        )}

        {!isRecording && transcribing && (
          <p style={{ marginTop: 10 }}>Transcribing...</p>
        )}

        {transcriptionError && (
          <p style={{ color: '#b00020', marginTop: 10 }}>{transcriptionError}</p>
        )}

        {transcriptionInfo && (
          <p style={{ color: '#1f7a1f', marginTop: 10 }}>{transcriptionInfo}</p>
        )}
      </section>

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

          <button
            onClick={handleGenerateAudio}
            disabled={audioLoading}
            style={{ marginTop: 12, marginLeft: 8, padding: '10px 16px', fontSize: 16, cursor: audioLoading ? 'not-allowed' : 'pointer' }}
          >
            {audioLoading ? 'Generating audio...' : 'Generate Audio'}
          </button>

          {imageError && (
            <p style={{ color: '#b00020', marginTop: 12 }}>{imageError}</p>
          )}

          {audioError && (
            <p style={{ color: '#b00020', marginTop: 12 }}>{audioError}</p>
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

          {audioUrl && (
            <div style={{ marginTop: 16 }}>
              <audio controls src={audioUrl} style={{ width: '100%' }}>
                Your browser does not support the audio element.
              </audio>
            </div>
          )}
        </section>
      )}
    </main>
  )
}

export default App
