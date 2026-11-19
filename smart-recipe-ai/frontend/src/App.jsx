import { useState } from 'react'
import {
  ArrowDownRight,
  ArrowRight,
  ChefHat,
  CircleHelp,
  Leaf,
  Sparkles,
  Sprout,
  UtensilsCrossed,
} from 'lucide-react'
import IngredientInput from './components/IngredientInput.jsx'
import RecipeResults from './components/RecipeResults.jsx'
import ChatAssistant from './components/ChatAssistant.jsx'
import { getRecommendations } from './services/api.js'

export default function App() {
  const [recipes, setRecipes] = useState([])
  const [recommendation, setRecommendation] = useState('')
  const [recommendationNotice, setRecommendationNotice] = useState('')
  const [pantrySummary, setPantrySummary] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [searched, setSearched] = useState(false)
  const [activeIngredients, setActiveIngredients] = useState([])

  async function searchRecipes(ingredients) {
    setActiveIngredients(ingredients)
    setLoading(true)
    setError('')
    setRecipes([])
    setRecommendation('')
    setRecommendationNotice('')
    setPantrySummary(null)
    setSearched(true)

    try {
      const data = await getRecommendations(ingredients)
      setRecipes(data.recipes || [])
      setRecommendation(data.recommendation || '')
      setRecommendationNotice(data.notice || '')
      setPantrySummary(data.pantry_summary || null)
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-shell">
      <div className="announcement-bar">
        <span className="announcement-dot" />
        GOOD FOOD, LESS WASTE <span className="announcement-divider">/</span> YOUR KITCHEN, REIMAGINED
      </div>

      <header className="site-header">
        <a className="brand" href="#top" aria-label="Simmer home">
          <span className="brand-mark"><Sprout size={22} strokeWidth={2.1} /></span>
          <span className="brand-wordmark">simmer<span>.</span><small>THE EVERYDAY FOOD STUDIO</small></span>
        </a>

        <nav className="desktop-nav" aria-label="Main navigation">
          <a className="nav-link active" href="#discover">Discover</a>
          <a className="nav-link" href="#ask-simmer">Ask Simmer</a>
          <a className="nav-link" href="#how-it-works">How it works</a>
          <a className="nav-link" href="#pantry">Your pantry</a>
        </nav>

        <a className="header-cta" href="#pantry">Let's cook <ArrowRight size={15} /></a>
      </header>

      <main id="top">
        <section className="hero-section" id="discover">
          <div className="hero-copy">
            <div className="hero-eyebrow"><span className="eyebrow-line" /> A FRESH TAKE ON WHAT'S FOR DINNER</div>
            <h1>Good things<br />are <em>already</em><br />in your kitchen<span className="hero-period">.</span></h1>
            <p className="hero-description">A handful of ingredients. A little inspiration. Let your pantry lead the way to something delicious.</p>
            <a className="hero-link" href="#pantry">Find your next favourite <ArrowDownRight size={17} /></a>
            <div className="hero-proof">
              <div className="proof-avatars" aria-hidden="true"><span>✳</span><span>✦</span><span>↗</span></div>
              <div><strong>Cook with what you have.</strong><small>Less food waste, more happy plates.</small></div>
            </div>
          </div>

          <div className="hero-visual">
            <img
              className="hero-food-image"
              src="https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=1200&q=88"
              alt="A colourful, freshly prepared bowl of food"
            />
            <div className="hero-image-shade" />
            <div className="image-sticker"><Sparkles size={15} /> MADE FOR REAL LIFE</div>
            <div className="hero-image-caption">
              <span>THE DAILY SPECIAL</span>
              <strong>Simple ingredients.<br />Lovely surprises.</strong>
            </div>
            <div className="floating-note">
              <span className="floating-note-icon"><Leaf size={17} /></span>
              <span><strong>Make the most of it</strong><small>Every ingredient has potential.</small></span>
            </div>
          </div>
        </section>

        <ChatAssistant />

        <section className="pantry-section" id="pantry">
          <div className="section-intro">
            <div>
              <div className="section-overline">01 <span>·</span> START WITH YOUR PANTRY</div>
              <h2>What's on your <em>counter?</em></h2>
            </div>
            <p>No shopping list needed. Add a few things you already have and we'll do the delicious thinking.</p>
          </div>

          <IngredientInput onSearch={searchRecipes} loading={loading} />

          {error && (
            <div className="error-message" role="alert">
              <CircleHelp size={18} />
              <span>{error}</span>
            </div>
          )}

          {loading && (
            <div className="loading-state" aria-live="polite">
              <div className="loading-orbit"><span /><span /><span /></div>
              <div><strong>Looking for your next good meal...</strong><small>Matching ingredients with recipes in our kitchen library.</small></div>
            </div>
          )}

          {!loading && recipes.length > 0 && (
            <RecipeResults recipes={recipes} recommendation={recommendation} pantrySummary={pantrySummary} ingredients={activeIngredients} notice={recommendationNotice} />
          )}

          {!loading && searched && !error && recipes.length === 0 && (
            <div className="empty-state">
              <span className="empty-state-icon"><ChefHat size={24} /></span>
              <div><strong>Nothing simmering just yet.</strong><p>Try adding one more main ingredient or a staple such as onion, tomato or rice, and Simmer will broaden the suggestions.</p></div>
            </div>
          )}
        </section>

        {!searched && (
          <section className="inspiration-strip" aria-label="Recipe inspiration">
            <div className="strip-label"><span className="strip-spark">✳</span><span> A LITTLE FOOD FOR THOUGHT</span></div>
            <p>“The secret ingredient is always the one you already have.”</p>
            <span className="strip-credit">— THE SIMMER KITCHEN</span>
          </section>
        )}

        <section className="how-section" id="how-it-works">
          <div className="how-heading">
            <div className="section-overline">03 <span>·</span> THE SIMMER METHOD</div>
            <h2>From what's there<br />to <em>something wonderful.</em></h2>
          </div>
          <div className="how-steps">
            <article className="how-step">
              <span className="step-number">01</span>
              <div className="step-icon pantry-icon"><UtensilsCrossed size={21} /></div>
              <h3>Tell us what's in</h3>
              <p>Drop in the ingredients you have on hand. Big pantry or nearly-empty fridge, all welcome.</p>
            </article>
            <article className="how-step">
              <span className="step-number">02</span>
              <div className="step-icon match-icon"><Sparkles size={21} /></div>
              <h3>We'll find a match</h3>
              <p>Our recipe search finds dishes that make the most of your ingredients, not just keyword matches.</p>
            </article>
            <article className="how-step">
              <span className="step-number">03</span>
              <div className="step-icon cook-icon"><ChefHat size={21} /></div>
              <h3>Make something lovely</h3>
              <p>Choose an idea, see what else you'll need, and get cooking. It's as simple as that.</p>
            </article>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <a className="footer-brand" href="#top">simmer<span>.</span></a>
        <span>GOOD FOOD STARTS RIGHT WHERE YOU ARE.</span>
        <span className="footer-tech"><span className="footer-status" /> AN AI-POWERED KITCHEN COMPANION</span>
      </footer>
    </div>
  )
}
