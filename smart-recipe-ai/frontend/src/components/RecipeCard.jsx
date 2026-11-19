import { useState } from 'react'
import {
  ArrowUpRight,
  Check,
  ChefHat,
  ChevronDown,
  Clock3,
  CookingPot,
  ExternalLink,
  Plus,
  Users,
} from 'lucide-react'

const recipeImages = {
  'Chicken Biryani': 'https://images.unsplash.com/photo-1563379091339-03246963d96c?auto=format&fit=crop&w=1000&q=85',
  'Tomato Rice': 'https://images.unsplash.com/photo-1512058564366-18510be2db19?auto=format&fit=crop&w=1000&q=85',
  'Everyday Chicken Curry': 'https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=1000&q=85',
  'Tamil Nadu Village Chicken Curry': 'https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=1000&q=85',
  'Chettinad Chicken Curry': 'https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=1000&q=85',
  'Kongu Chicken Kulambu': 'https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=1000&q=85',
  'Chicken Pepper Gravy': 'https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=1000&q=85',
  'Country Chicken Kulambu': 'https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=1000&q=85',
  'Vegetable Fried Rice': 'https://images.unsplash.com/photo-1512058564366-18510be2db19?auto=format&fit=crop&w=1000&q=85',
  'Masala Dosa': 'https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=1000&q=85',
  'Garlic Chicken': 'https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?auto=format&fit=crop&w=1000&q=85',
  'Paneer Butter Masala': 'https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=1000&q=85',
}

function safeSourceUrl(value) {
  try {
    const url = new URL(value)
    return ['http:', 'https:'].includes(url.protocol) ? url.href : null
  } catch {
    return null
  }
}

export default function RecipeCard({
  recipe,
  index = 0,
  expandedInitially = false,
  showPantryMatch = true,
  variant = 'default',
}) {
  const [expanded, setExpanded] = useState(expandedInitially)
  const [imageFailed, setImageFailed] = useState(false)
  const matched = recipe.matched_ingredients || []
  const missing = recipe.missing_ingredients || []
  // Never display an unrelated stock photo for a generated/new dish.
  const image = recipe.ai_generated ? null : (recipe.image_url || recipeImages[recipe.name] || null)
  const ingredientDetails = recipe.ingredient_details?.length
    ? recipe.ingredient_details
    : (recipe.ingredients || []).map(name => ({ name, quantity: 'Quantity as required' }))
  const sourceLabel = recipe.source_type === 'web'
    ? 'Web references'
    : recipe.ai_generated
      ? 'Simmer-created'
      : (recipe.meal_type || 'Simmer kitchen')

  return (
    <article className={`recipe-card ${index === 0 ? 'recipe-card-featured' : ''} ${expanded ? 'is-expanded' : ''} ${variant === 'detail' ? 'recipe-card-detail' : ''}`}>
      <div className="recipe-image-wrap">
        {image && !imageFailed ? (
          <img src={image} alt={`${recipe.name} prepared dish`} loading="lazy" onError={() => setImageFailed(true)} />
        ) : (
          <div className="recipe-image-fallback" aria-label={`Illustration placeholder for ${recipe.name}`}>
            <span className="recipe-fallback-orbit"><CookingPot size={37} strokeWidth={1.25} /></span>
            <span>{recipe.region || recipe.cuisine || 'FROM SIMMER’S KITCHEN'}</span>
            <strong>{recipe.name}</strong>
            <small>Recipe details inside</small>
          </div>
        )}
        <span className="recipe-image-index">{String(index + 1).padStart(2, '0')}</span>
        {showPantryMatch && matched.length > 0 && (
          <span className="recipe-match"><span className="match-spark">✳</span> {matched.length} pantry {matched.length === 1 ? 'item' : 'items'}</span>
        )}
      </div>

      <div className="recipe-card-content">
        <div className="recipe-card-meta-top">
          <span className="recipe-cuisine">{recipe.region || recipe.cuisine}</span>
          <span className="meal-type">{sourceLabel}</span>
        </div>
        <h3>{recipe.name}</h3>
        {recipe.description && <p className="recipe-description">{recipe.description}</p>}
        <div className="recipe-details">
          <span><Clock3 size={14} /> {recipe.prep_time ?? '—'} min prep</span>
          <span><CookingPot size={14} /> {recipe.cooking_time} min cook</span>
          <span><ChefHat size={14} /> {recipe.difficulty}</span>
          {recipe.servings && <span><Users size={14} /> Serves {recipe.servings}</span>}
        </div>

        {showPantryMatch && (
          <div className="recipe-ingredient-groups">
            <div className="recipe-ingredient-group">
              <span className="ingredient-group-label have-label"><Check size={12} /> YOU HAVE</span>
              <div className="recipe-ingredient-pills">
                {matched.length ? matched.slice(0, 5).map(item => <span className="have-pill" key={item}>{item}</span>) : <span className="muted-pill">No direct matches</span>}
                {matched.length > 5 && <span className="muted-pill">+{matched.length - 5}</span>}
              </div>
            </div>
            <div className="recipe-ingredient-group">
              <span className="ingredient-group-label need-label"><Plus size={12} /> STILL NEEDED</span>
              <div className="recipe-ingredient-pills">
                {missing.length ? missing.slice(0, 5).map(item => <span className="need-pill" key={item}>{item}</span>) : <span className="muted-pill">You’re all set</span>}
                {missing.length > 5 && <span className="muted-pill">+{missing.length - 5}</span>}
              </div>
            </div>
          </div>
        )}

        <button className={`recipe-expand ${expanded ? 'expanded' : ''}`} onClick={() => setExpanded(value => !value)} aria-expanded={expanded}>
          <span>{expanded ? 'Close full recipe' : 'View full recipe'} <ArrowUpRight size={14} /></span>
          <ChevronDown size={16} />
        </button>

        {expanded && (
          <div className="recipe-instructions">
            <div className="recipe-detail-summary">
              <span><Users size={14} /> Serves {recipe.servings || 4}</span>
              <span><Clock3 size={14} /> Prep {recipe.prep_time ?? '—'} min</span>
              <span><CookingPot size={14} /> Cook {recipe.cooking_time} min</span>
            </div>
            <div className="instructions-heading"><Check size={15} /> INGREDIENTS WITH MEASUREMENTS</div>
            <ul className="measured-ingredients">
              {ingredientDetails.map((item, itemIndex) => (
                <li key={`${recipe.id}-ingredient-${itemIndex}`}>
                  <span className="measured-quantity">{item.quantity}</span>
                  <span><strong>{item.name}</strong>{item.note ? <small>{item.note}</small> : null}</span>
                </li>
              ))}
            </ul>
            <div className="instructions-heading method-heading"><CookingPot size={15} /> STEP-BY-STEP METHOD</div>
            <ol>
              {(recipe.instructions || []).map((step, stepIndex) => <li key={`${recipe.id}-${stepIndex}`}><span>{String(stepIndex + 1).padStart(2, '0')}</span><p>{step}</p></li>)}
            </ol>
            {recipe.tips?.length > 0 && (
              <div className="recipe-tips">
                <strong>Simmer’s kitchen notes</strong>
                {recipe.tips.map((tip, tipIndex) => <p key={`${recipe.id}-tip-${tipIndex}`}>{tip}</p>)}
              </div>
            )}
            {recipe.substitutions?.length > 0 && (
              <div className="recipe-tips recipe-substitutions">
                <strong>Useful substitutions</strong>
                {recipe.substitutions.map((item, itemIndex) => <p key={`${recipe.id}-sub-${itemIndex}`}>{item}</p>)}
              </div>
            )}
            {recipe.source_links?.length > 0 && (
              <div className="recipe-sources">
                <strong>Recipe references</strong>
                <div>{recipe.source_links.map((source, sourceIndex) => {
                  const href = safeSourceUrl(source.url)
                  return href ? <a key={`${recipe.id}-source-${sourceIndex}`} href={href} target="_blank" rel="noreferrer">{source.title || `Source ${sourceIndex + 1}`} <ExternalLink size={12} /></a> : null
                })}</div>
              </div>
            )}
          </div>
        )}
      </div>
    </article>
  )
}
