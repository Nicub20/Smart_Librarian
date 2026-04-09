import { useState } from 'react'
import './App.css'

function App() {
  const [composerText, setComposerText] = useState('')
  const [messages, setMessages] = useState([])
  const [history, setHistory] = useState([])
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [mediaRecorder, setMediaRecorder] = useState(null)
  const [audioChunks, setAudioChunks] = useState([])
  const [transcriptionLanguage, setTranscriptionLanguage] = useState('Auto')
  const [transcribing, setTranscribing] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [transcriptionError, setTranscriptionError] = useState('')
  const [transcriptionInfo, setTranscriptionInfo] = useState('')
  const [chatTitle, setChatTitle] = useState('New conversation')

  const createId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`

  const clearAllAudioUrls = () => {
    messages.forEach((message) => {
      if (message.audioUrl && message.audioUrl.startsWith('blob:')) {
        URL.revokeObjectURL(message.audioUrl)
      }
    })
  }

  const startNewChat = () => {
    if (isRecording && mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop()
    }
    clearAllAudioUrls()
    setMessages([])
    setComposerText('')
    setError('')
    setTranscriptionError('')
    setTranscriptionInfo('')
    setChatTitle('New conversation')
  }

  const buildAudioText = (bookResult) => {
    const recommendedTitle = bookResult?.recommended_title || 'Unknown'
    const whyItMatches = bookResult?.why_it_matches || 'No explanation available.'
    const detailedSummary = bookResult?.detailed_summary || 'No detailed summary available.'

    return `Recommended title: ${recommendedTitle}. Why it matches: ${whyItMatches}. Detailed summary: ${detailedSummary}`
  }

  const updateMessageById = (id, updater) => {
    setMessages((prev) => prev.map((msg) => (msg.id === id ? updater(msg) : msg)))
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

      setComposerText(data?.transcript || '')
      setTranscriptionInfo('Transcript loaded into the request box.')
    } catch (err) {
      setTranscriptionInfo('')
      setTranscriptionError(err instanceof Error ? err.message : 'Unexpected transcription error occurred.')
    } finally {
      setTranscribing(false)
    }
  }

  const handleRecommend = async () => {
    const query = composerText.trim()
    if (!query) {
      setError('Please enter a request first.')
      return
    }

    setLoading(true)
    setError('')

    const userMessage = {
      id: createId(),
      role: 'user',
      content: query,
    }
    setMessages((prev) => [...prev, userMessage])
    setComposerText('')
    if (chatTitle === 'New conversation') {
      setChatTitle(query.slice(0, 44))
      setHistory((prev) => [query.slice(0, 60), ...prev].slice(0, 8))
    }

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

      const assistantMessage = {
        id: createId(),
        role: 'assistant',
        result: data,
        imageUrl: '',
        imageLoading: false,
        imageError: '',
        audioUrl: '',
        audioLoading: false,
        audioError: '',
      }
      setMessages((prev) => [...prev, assistantMessage])
    } catch (err) {
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

  const handleGenerateAudio = async (messageId) => {
    const message = messages.find((m) => m.id === messageId)
    if (!message?.result) {
      return
    }

    updateMessageById(messageId, (msg) => ({ ...msg, audioLoading: true, audioError: '' }))

    try {
      const combinedText = buildAudioText(message.result)
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

      updateMessageById(messageId, (msg) => {
        if (msg.audioUrl && msg.audioUrl.startsWith('blob:')) {
          URL.revokeObjectURL(msg.audioUrl)
        }
        return {
          ...msg,
          audioUrl: nextAudioUrl,
          audioError: '',
        }
      })
    } catch (err) {
      updateMessageById(messageId, (msg) => {
        if (msg.audioUrl && msg.audioUrl.startsWith('blob:')) {
          URL.revokeObjectURL(msg.audioUrl)
        }
        return {
          ...msg,
          audioUrl: '',
          audioError: err instanceof Error ? err.message : 'Unexpected audio error occurred.',
        }
      })
    } finally {
      updateMessageById(messageId, (msg) => ({ ...msg, audioLoading: false }))
    }
  }

  const handleGenerateImage = async (messageId) => {
    const message = messages.find((m) => m.id === messageId)
    if (!message?.result) {
      return
    }

    updateMessageById(messageId, (msg) => ({ ...msg, imageLoading: true, imageError: '' }))

    try {
      const response = await fetch('http://localhost:8000/image', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: message.result.recommended_title,
          summary: message.result.detailed_summary,
        }),
      })

      const data = await response.json()
      if (!response.ok) {
        throw new Error(data?.detail || 'Failed to generate image.')
      }

      updateMessageById(messageId, (msg) => ({ ...msg, imageUrl: data.image_url || '', imageError: '' }))
    } catch (err) {
      updateMessageById(messageId, (msg) => ({
        ...msg,
        imageUrl: '',
        imageError: err instanceof Error ? err.message : 'Unexpected image error occurred.',
      }))
    } finally {
      updateMessageById(messageId, (msg) => ({ ...msg, imageLoading: false }))
    }
  }

  return (
    <div className={`chat-app ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      <aside className="sidebar">
        <div className="sidebar-topbar">
          <button
            className="sidebar-toggle"
            type="button"
            onClick={() => setIsSidebarCollapsed((prev) => !prev)}
            aria-label={isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <span className="sidebar-toggle-bar" />
            <span className="sidebar-toggle-bar" />
            <span className="sidebar-toggle-bar" />
          </button>
        </div>

        <div className="sidebar-brand">
          <div className="sidebar-brand-row">
            <div className="sidebar-logo" aria-hidden="true">
              <span className="sidebar-logo-book" />
            </div>
            <div className="sidebar-brand-copy">
              <h1 className="sidebar-title">Smart Librarian</h1>
              <p className="sidebar-tagline">AI book discovery with voice, images, and audio.</p>
            </div>
          </div>
          <button className="btn btn-primary sidebar-new-chat" onClick={startNewChat} type="button">
            New Chat
          </button>
        </div>

        <section className="sidebar-card">
          <h3 className="section-title">Voice Mode</h3>

          <div className="field-row">
            <label className="field-label" htmlFor="voice-language">Language</label>
            <select
              className="select-input"
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

          <div className="button-row">
            <button
              className="btn btn-accent"
              onClick={handleStartRecording}
              disabled={isRecording || transcribing}
            >
              Start Recording
            </button>
            <button
              className="btn btn-ghost"
              onClick={handleStopRecording}
              disabled={!isRecording}
            >
              Stop Recording
            </button>
          </div>

          {isRecording && <p className="status-live">Recording...</p>}
          {!isRecording && transcribing && <p className="status-muted">Transcribing...</p>}
          {transcriptionError && <div className="alert alert-error">{transcriptionError}</div>}
          {transcriptionInfo && <div className="alert alert-success">{transcriptionInfo}</div>}
        </section>

        <section className="sidebar-card history-card">
          <h3 className="section-title">Recent Prompts</h3>
          {history.length === 0 ? (
            <p className="history-empty">No history yet.</p>
          ) : (
            <ul className="history-list">
              {history.map((item, idx) => (
                <li key={`${item}-${idx}`}>
                  <button className="history-item" onClick={() => setComposerText(item)}>
                    {item}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </aside>

      <main className="chat-main">
        <header className="chat-header">
          <h2>{chatTitle}</h2>
          <p>Ask for any book theme, genre, or style.</p>
        </header>

        <section className="chat-scroll">
          {messages.length === 0 && (
            <div className="empty-chat">
              <h3>Start your first recommendation</h3>
              <p>Type a request below or use Voice Mode from the sidebar.</p>
            </div>
          )}

          {messages.map((message) => (
            <article key={message.id} className={`message-row ${message.role}`}>
              <div className={`message-bubble ${message.role}`}>
                {message.role === 'user' ? (
                  <p className="message-text">{message.content}</p>
                ) : (
                  <div>
                    <h3 className="result-title">{message.result.recommended_title}</h3>

                    <h4 className="result-subtitle">Why it matches</h4>
                    <p className="result-text">{message.result.why_it_matches}</p>

                    <h4 className="result-subtitle">Detailed summary</h4>
                    <p className="result-text">{message.result.detailed_summary}</p>

                    <div className="button-row result-actions">
                      <button
                        className="btn btn-accent"
                        onClick={() => handleGenerateImage(message.id)}
                        disabled={message.imageLoading}
                      >
                        {message.imageLoading ? 'Generating image...' : 'Generate Image'}
                      </button>

                      <button
                        className="btn btn-ghost"
                        onClick={() => handleGenerateAudio(message.id)}
                        disabled={message.audioLoading}
                      >
                        {message.audioLoading ? 'Generating audio...' : 'Generate Audio'}
                      </button>
                    </div>

                    {message.imageError && <div className="alert alert-error">{message.imageError}</div>}
                    {message.audioError && <div className="alert alert-error">{message.audioError}</div>}

                    {message.imageUrl && (
                      <section className="media-card">
                        <h5 className="media-title">Suggested Book Cover</h5>
                        <img
                          className="result-image"
                          src={message.imageUrl}
                          alt={`Illustration inspired by ${message.result.recommended_title}`}
                        />
                      </section>
                    )}

                    {message.audioUrl && (
                      <section className="media-card">
                        <h5 className="media-title">Generated Audio</h5>
                        <audio className="result-audio" controls src={message.audioUrl}>
                          Your browser does not support the audio element.
                        </audio>
                      </section>
                    )}
                  </div>
                )}
              </div>
            </article>
          ))}
        </section>

        {error && <div className="alert alert-error chat-error">{error}</div>}

        <footer className="composer-wrap">
          <div className="composer-box">
            <textarea
              className="composer-input"
              value={composerText}
              onChange={(e) => setComposerText(e.target.value)}
              rows={2}
              placeholder="Ask for a recommendation, e.g. 'Recommend a book like Steve Jobs biography'"
            />
            <button
              className="btn btn-primary composer-send"
              onClick={handleRecommend}
              disabled={loading}
            >
              {loading ? 'Sending...' : 'Send'}
            </button>
          </div>
        </footer>
      </main>
    </div>
  )
}

export default App
