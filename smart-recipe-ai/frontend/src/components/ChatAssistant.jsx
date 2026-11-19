import { useEffect, useRef, useState } from 'react'
import { ArrowUp, ChefHat, MessageCircle, Sparkles, Utensils } from 'lucide-react'
import RecipeCard from './RecipeCard.jsx'
import { askAssistant } from '../services/api.js'

const starterPrompts = [
  'Show me five authentic chicken curry dishes',
  'Afghani chicken',
  'Chicken biryani',
  'Chicken pepper gravy',
]

function cleanMessage(value = '') {
  let text = String(value)
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/__(.*?)__/g, '$1')
    .replace(/^\s{0,3}#{1,6}\s*/gm, '')
    .replace(/^\s*[-*]\s+/gm, '• ')
    .replace(/\*+/g, '')
    .replace(/`/g, '')
    .trim()

  // Compatibility guard for older API responses: never tell the cook that a
  // dish was absent from the local box. Present the recipe positively instead.
  text = text.replace(
    /I couldn['’]t find an exact match in the saved recipe box, so I created a complete AI-generated starting recipe for ([^.]+)\./i,
    'Here is your complete $1 recipe, with measured ingredients and a step-by-step method.'
  )
  return text
}

export default function ChatAssistant() {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages])

  async function sendMessage(value = input) {
    const message = value.trim()
    if (!message || loading) return

    const messageId = `${Date.now()}-${Math.random().toString(16).slice(2)}`
    const assistantId = `assistant-${messageId}`
    setMessages(current => [
      ...current,
      { id: `user-${messageId}`, role: 'user', text: message },
      { id: assistantId, role: 'assistant', loading: true },
    ])
    setInput('')
    setLoading(true)

    try {
      const result = await askAssistant(message)
      setMessages(current => current.map(item => item.id === assistantId
        ? { ...item, ...result, loading: false }
        : item))
    } catch (error) {
      setMessages(current => current.map(item => item.id === assistantId
        ? { ...item, text: error.message || 'I could not reach the recipe assistant. Please try again.', loading: false, failed: true }
        : item))
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      sendMessage()
    }
  }

  return (
    <section className="chat-section" id="ask-simmer">
      <div className="chat-section-heading">
        <div>
          <div className="section-overline">02 · COOKING, CONVERSATIONALLY</div>
          <h2>Ask Simmer <em>anything.</em></h2>
          <p>Ask for one exact dish, discover regional styles or get a complete recipe with measured ingredients and a proper cooking method.</p>
        </div>
        <span className="chat-heading-mark"><MessageCircle size={26} /></span>
      </div>

      <div className="chat-panel">
        <div className="chat-panel-top">
          <span className="chat-avatar"><ChefHat size={19} /></span>
          <div><strong>Simmer’s kitchen</strong><small><span className="chat-online-dot" /> Ready to help you cook</small></div>
          <span className="chat-powered"><Sparkles size={13} /> RECIPE ASSISTANT</span>
        </div>

        <div className="chat-conversation" aria-live="polite">
          {messages.length === 0 ? (
            <div className="chat-welcome">
              <span className="chat-welcome-icon"><Utensils size={21} /></span>
              <strong>What are we cooking today?</strong>
              <p>Ask for a dish by name. Simmer will give you quantities, timings and the full step-by-step method.</p>
              <div className="chat-starters">
                {starterPrompts.map(prompt => <button key={prompt} type="button" onClick={() => sendMessage(prompt)} disabled={loading}>{prompt}</button>)}
              </div>
            </div>
          ) : messages.map(item => (
            <div className={`chat-message-row ${item.role}`} key={item.id}>
              {item.role === 'assistant' && <span className="chat-message-avatar"><ChefHat size={15} /></span>}
              <div className={`chat-message ${item.role} ${item.failed ? 'failed' : ''}`}>
                {item.loading ? (
                  <div className="chat-thinking"><span /><span /><span /> Preparing your recipe...</div>
                ) : (
                  <>
                    {(item.text || item.message) && <p className="chat-message-text">{cleanMessage(item.text || item.message)}</p>}
                    {item.notice && <p className="chat-message-notice">{cleanMessage(item.notice)}</p>}
                    {item.recipes?.length > 0 && (
                      <div className="chat-results">
                        <div className="chat-results-heading">
                          <strong>{item.intent === 'recipe' ? 'Your complete recipe' : `${item.recipes.length} dishes to explore`}</strong>
                          <span>{item.intent === 'recipe' ? 'MEASURED · TESTABLE · STEP BY STEP' : 'CHOOSE A DISH FOR THE FULL METHOD'}</span>
                        </div>
                        <div className={`recipe-grid chat-recipe-grid ${item.intent === 'recipe' && item.recipes.length === 1 ? 'is-single-recipe' : ''}`}>
                          {item.recipes.map((recipe, index) => (
                            <RecipeCard
                              key={recipe.id}
                              recipe={recipe}
                              index={index}
                              expandedInitially={item.intent === 'recipe'}
                              showPantryMatch={false}
                              variant={item.intent === 'recipe' && item.recipes.length === 1 ? 'detail' : 'default'}
                            />
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <form className="chat-composer" onSubmit={event => { event.preventDefault(); sendMessage() }}>
          <input
            value={input}
            onChange={event => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask for a dish, e.g. Afghani chicken or pepper gravy..."
            maxLength={500}
            disabled={loading}
            aria-label="Ask Simmer a cooking question"
          />
          <button type="submit" disabled={loading || !input.trim()} aria-label="Send message"><ArrowUp size={19} /></button>
        </form>
        <div className="chat-footnote">Ask for a dish by name, request five regional variations, or describe the flavour you want. New dishes are prepared by Simmer; live reference links appear when web search is configured.</div>
      </div>
    </section>
  )
}
