import { useState } from 'react'
import { Plus, X, Search, Sparkles, Leaf } from 'lucide-react'

const suggestions = ['chicken', 'rice', 'tomato', 'onion', 'egg', 'potato']

export default function IngredientInput({ onSearch, loading }) {
  const [ingredient, setIngredient] = useState('')
  const [ingredients, setIngredients] = useState([])

  function addIngredient(value = ingredient) {
    const clean = value.trim().toLowerCase().replace(/\s+/g, ' ')
    if (clean && !ingredients.includes(clean)) {
      setIngredients(current => [...current, clean])
    }
    setIngredient('')
  }

  function removeIngredient(item) {
    setIngredients(current => current.filter(value => value !== item))
  }

  function handleKeyDown(event) {
    if (event.key === 'Enter') {
      event.preventDefault()
      addIngredient()
    }
  }

  return (
    <div className="pantry-card">
      <div className="pantry-card-top">
        <div className="pantry-card-title">
          <span className="pantry-card-icon"><Sparkles size={18} /></span>
          <div><strong>Your ingredient list</strong><small>Build your basket, one ingredient at a time</small></div>
        </div>
        <span className="ingredient-count"><b>{String(ingredients.length).padStart(2, '0')}</b> ADDED</span>
      </div>

      <div className="ingredient-entry-row">
        <label className="ingredient-entry" htmlFor="ingredient-entry">
          <Search size={18} />
          <input
            id="ingredient-entry"
            value={ingredient}
            onChange={event => setIngredient(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Add an ingredient — e.g. chickpeas, spinach, rice..."
            autoComplete="off"
            maxLength={60}
            disabled={loading}
          />
          {ingredient.trim() && (
            <button type="button" className="inline-add" onClick={() => addIngredient()} aria-label="Add ingredient" disabled={loading}>
              <Plus size={17} />
            </button>
          )}
        </label>
        <button className="find-button" disabled={loading || ingredients.length === 0} onClick={() => onSearch(ingredients)}>
          <span>{loading ? 'Finding ideas' : 'Find recipes'}</span>
          <span className="find-button-icon"><Search size={16} /></span>
        </button>
      </div>

      <div className="pantry-card-bottom">
        <div className="quick-add-row">
          <span className="quick-add-label">QUICK ADD</span>
          {suggestions.map(item => (
            <button key={item} className="quick-add-chip" disabled={loading || ingredients.includes(item)} onClick={() => addIngredient(item)}>
              <Plus size={11} /> {item}
            </button>
          ))}
        </div>
        <div className={`ingredient-chips ${ingredients.length === 0 ? 'is-empty' : ''}`} aria-live="polite">
          {ingredients.length === 0 ? (
            <span className="ingredient-placeholder">Your ingredients will show up here.</span>
          ) : ingredients.map(item => (
            <span className="ingredient-chip" key={item}>
              {item}
              <button type="button" onClick={() => removeIngredient(item)} aria-label={`Remove ${item}`} disabled={loading}><X size={13} /></button>
            </span>
          ))}
          {ingredients.length > 0 && <button className="clear-ingredients" type="button" onClick={() => setIngredients([])} disabled={loading}>Clear all</button>}
        </div>
      </div>
      <div className="pantry-card-footnote"><Leaf size={13} /> Start with 2–3 ingredients for the best ideas.</div>
    </div>
  )
}
