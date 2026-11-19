import { Sparkles, ArrowDown, ChefHat, Check, Plus } from 'lucide-react'
import RecipeCard from './RecipeCard.jsx'

function cleanAssistantText(value = '') {
  return String(value)
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/__(.*?)__/g, '$1')
    .replace(/\*+/g, '')
    .replace(/^\s{0,3}#{1,6}\s*/gm, '')
    .replace(/^\s*[-*]\s+/gm, '• ')
    .trim()
}

export default function RecipeResults({ recipes = [], recommendation, pantrySummary, ingredients = [], notice = '' }) {
  const visibleRecipes = (Array.isArray(recipes) ? recipes : []).filter(
    recipe => recipe && typeof recipe.name === 'string' && recipe.name.trim().length > 0
  )

  return (
    <section className="results-container" aria-live="polite">
      <div className="results-intro">
        <div>
          <div className="section-overline">03 <span>·</span> FRESH FROM THE RECIPE BOX</div>
          <h2>Your next <em>good meal.</em></h2>
          <p>{pantrySummary?.primary_ingredient ? `Starting with ${pantrySummary.primary_ingredient}, we ranked dishes by how well they use your ingredients.` : `We checked all ${ingredients.length} ingredients in your basket and ranked the recipes around them.`}</p>
        </div>
        <span className="result-count"><b>{visibleRecipes.length}</b> {visibleRecipes.length === 1 ? 'IDEA' : 'IDEAS'} FOUND</span>
      </div>

      {(pantrySummary?.best_recipe || recommendation) && (
        <article className="ai-recommendation">
          <div className="ai-note-side"><span className="ai-note-icon"><Sparkles size={21} /></span><span className="ai-note-label">SIMMER’S<br />TOP PICK</span></div>
          <div className="ai-note-content">
            <div className="ai-label">A MATCH BASED ON YOUR ACTUAL INGREDIENTS</div>
            {pantrySummary?.best_recipe ? (
              <>
                <h3 className="pantry-pick-title">{pantrySummary.best_recipe}</h3>
                <p className="pantry-pick-copy">{pantrySummary.primary_ingredient ? `Built around ${pantrySummary.primary_ingredient}. ` : ''}Uses {pantrySummary.matched.length} of the {pantrySummary.input_count} ingredients you entered.</p>
                <div className="pantry-summary-groups">
                  {pantrySummary.matched.length > 0 && <div><span><Check size={13} /> IN THIS RECIPE</span><p>{pantrySummary.matched.join(' · ')}</p></div>}
                  {pantrySummary.unused.length > 0 && <div><span><ChefHat size={13} /> ALSO IN YOUR PANTRY</span><p>{pantrySummary.unused.join(' · ')} <small>— not needed for this dish</small></p></div>}
                  {pantrySummary.missing.length > 0 && <div><span><Plus size={13} /> YOU MAY NEED</span><p>{pantrySummary.missing.slice(0, 10).join(' · ')}{pantrySummary.missing.length > 10 ? ' · and more' : ''}</p></div>}
                </div>
              </>
            ) : (
              <div className="recommendation-text">{cleanAssistantText(recommendation)}</div>
            )}
            {notice && <p className="fallback-notice" role="status">{notice}</p>}
          </div>
          <div className="ai-note-decoration"><ChefHat size={84} strokeWidth={0.8} /></div>
        </article>
      )}

      <div className="recipe-list-heading"><div><span className="section-overline">THE SHORTLIST</span><h3>Made for your kitchen</h3></div><span className="scroll-hint">TAKE A LOOK <ArrowDown size={14} /></span></div>
      {visibleRecipes.length > 0 && (
          <div className={`recipe-grid ${visibleRecipes.length === 1 ? 'is-single-result' : ''}`}>
            {visibleRecipes.map((recipe, index) => (
              <RecipeCard
                key={recipe.id || `${recipe.name}-${index}`}
                recipe={recipe}
                index={index}
              />
            ))}
          </div>
        )}
    </section>
  )
}
