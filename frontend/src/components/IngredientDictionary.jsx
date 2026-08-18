import { useState, useEffect, useRef } from 'react';
import { getIngredients, getUmbrellas } from '../services/api';

/**
 * Calculates responsive inline styles for tooltips to prevent clipping
 * on the left or right edges of the screen/container.
 */
function getTooltipPositionStyle(pillElement, tooltipWidth = 280) {
  if (!pillElement) return {};
  const rect = pillElement.getBoundingClientRect();
  const pillCenter = rect.left + rect.width / 2;
  const halfWidth = tooltipWidth / 2;
  const padding = 16;

  let left = '50%';
  let transform = 'translateX(-50%)';
  let arrowLeft = '50%';

  if (pillCenter - halfWidth < padding) {
    const shiftLeft = padding - (pillCenter - halfWidth);
    left = `calc(50% + ${shiftLeft}px)`;
    arrowLeft = `calc(50% - ${shiftLeft}px)`;
  } else if (pillCenter + halfWidth > window.innerWidth - padding) {
    const shiftRight = (pillCenter + halfWidth) - (window.innerWidth - padding);
    left = `calc(50% - ${shiftRight}px)`;
    arrowLeft = `calc(50% + ${shiftRight}px)`;
  }

  return { left, transform, '--arrow-left': arrowLeft };
}

/**
 * Interactive sub-concern pill that toggles a study tooltip on click.
 */
function SubconcernStudyPill({ subconcern }) {
  const [showTooltip, setShowTooltip] = useState(false);
  const pillRef = useRef(null);
  const [tooltipStyle, setTooltipStyle] = useState({});

  const articles = subconcern.articles || [];
  const queryUsed = subconcern.query_used || '';
  const count = subconcern.count || articles.length || 0;
  const tier = subconcern.tier || 'studied';
  const tierClass = `tier-${tier}`;

  const handleClick = (e) => {
    e.stopPropagation();
    if (!showTooltip && pillRef.current) {
      setTooltipStyle(getTooltipPositionStyle(pillRef.current, 290));
    }
    setShowTooltip(!showTooltip);
  };

  const pubmedSearchUrl = queryUsed
    ? `https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(queryUsed)}`
    : null;

  return (
    <div ref={pillRef} className="concern-pill-wrapper" onClick={handleClick}>
      <span className={`concern-pill-ingredient ${tierClass} has-articles`}>
        {subconcern.concern?.label || 'Subconcern'}
        {count > 0 && <span className="article-badge" style={{ marginLeft: 5 }}>{count}</span>}
      </span>
      {showTooltip && (
        <div className="concern-pill-tooltip" style={tooltipStyle} onClick={(e) => e.stopPropagation()}>
          <div className="tooltip-header-info">
            <h5 className="tooltip-title">
              PubMed Studies
              <span className="tooltip-count">{count} total</span>
            </h5>
          </div>
          {articles.length > 0 ? (
            <ul className="tooltip-articles">
              {articles.map((art, idx) => (
                <li key={art.pmid || idx} className="tooltip-article-item">
                  <a
                    href={art.pmid ? `https://pubmed.ncbi.nlm.nih.gov/${art.pmid}/` : (art.url || '#')}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {art.title}
                  </a>
                  <span className="tooltip-article-source">
                    PubMed {art.year ? `· ${art.year}` : ''}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p style={{ fontSize: '0.78rem', color: '#64748b', margin: '6px 0' }}>
              Indexed in PubMed query database.
            </p>
          )}
          {pubmedSearchUrl && (
            <a
              href={pubmedSearchUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="tooltip-search-link"
            >
              Search PubMed →
            </a>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Expandable parent concern card inside an ingredient's drop-down details.
 */
function IngredientConcernCard({ group, isOpen, onToggle }) {
  const subConcerns = group.sub_concerns || [];
  const totalStudies = subConcerns.reduce((acc, sc) => acc + (sc.count || 0), 0);

  return (
    <div className={`concern-card ${isOpen ? 'concern-card--open' : ''}`} onClick={onToggle}>
      <div className="concern-card-header">
        <span className="concern-card-name">{group.parent?.label || 'Concern'}</span>
        <span className="concern-card-count">
          {subConcerns.length} sub-concern{subConcerns.length !== 1 ? 's' : ''} ({totalStudies} total studies)
        </span>
      </div>
      {isOpen && (
        <div className="concern-card-body" onClick={(e) => e.stopPropagation()}>
          <div className="concern-subconcern">
            <span className="concern-subconcern-label">Targeted Sub-concerns (Click pill for PubMed papers)</span>
            <div className="concern-subconcern-pills">
              {subConcerns.map((sc, idx) => (
                <SubconcernStudyPill key={sc.concern?.id || idx} subconcern={sc} />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Individual Ingredient Card in the Dictionary.
 */
function IngredientCard({ ingredient, isOpen, onToggle }) {
  const [openConcernId, setOpenConcernId] = useState(null);

  const breakdown = ingredient.concern_breakdown || [];
  const totalStudies = (ingredient.evidence_scores || []).reduce(
    (acc, ev) => acc + (ev.pubmed_count || 0),
    0
  );
  const articleCount = totalStudies || (ingredient.articles || []).length || 0;

  return (
    <div
      id={`ingredient-card-${ingredient.id}`}
      className={`ingredient-dict-card ${isOpen ? 'ingredient-dict-card--open' : ''}`}
    >
      <div className="ingredient-dict-header" onClick={onToggle}>
        <div className="ingredient-dict-title-group">
          <h3 className="ingredient-dict-name">{ingredient.inci_name}</h3>
          {ingredient.common_name && ingredient.common_name !== ingredient.inci_name && (
            <span className="ingredient-dict-common">({ingredient.common_name})</span>
          )}
          <div className="ingredient-dict-umbrellas">
            {(ingredient.umbrellas || []).map((u) => (
              <span key={u.id || u.name} className="umbrella-badge">
                {u.name}
              </span>
            ))}
          </div>
        </div>
        <div className="ingredient-dict-meta">
          <span className="study-count-badge">
            📚 {articleCount} study{articleCount !== 1 ? 'ies' : ''} / papers
          </span>
          <button className="dict-expand-btn">
            {isOpen ? 'Close ▲' : 'Targeted Concerns ▼'}
          </button>
        </div>
      </div>

      {isOpen && (
        <div className="ingredient-dict-body">
          {ingredient.description && (
            <p className="ingredient-dict-desc">{ingredient.description}</p>
          )}

          <div className="ingredient-dict-concerns-section">
            <h4 className="expanded-label" style={{ marginBottom: 12 }}>Targeted Skin Concerns</h4>
            {breakdown.length > 0 ? (
              <div className="concern-cards-grid">
                {breakdown.map((group) => (
                  <IngredientConcernCard
                    key={group.parent.id}
                    group={group}
                    isOpen={openConcernId === group.parent.id}
                    onToggle={() =>
                      setOpenConcernId(openConcernId === group.parent.id ? null : group.parent.id)
                    }
                  />
                ))}
              </div>
            ) : (
              <p className="no-actives" style={{ fontStyle: 'italic', color: '#64748b' }}>
                No specific skin concern evidence scores indexed for this ingredient.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Main Ingredient Dictionary Page View.
 */
export default function IngredientDictionary({ selectedIngredient }) {
  const [ingredients, setIngredients] = useState([]);
  const [umbrellas, setUmbrellas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedUmbrella, setSelectedUmbrella] = useState('All');
  const [openIngredientId, setOpenIngredientId] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [ingData, umbData] = await Promise.all([
          getIngredients({ has_evidence: 'true' }),
          getUmbrellas(),
        ]);
        const ingList = ingData.results || ingData || [];
        // Filter strictly to ingredients that have accumulated PubMed studies/articles
        const listWithArticles = ingList.filter(
          (ing) =>
            (ing.articles && ing.articles.length > 0) ||
            (ing.evidence_scores && ing.evidence_scores.some((e) => (e.pubmed_count || 0) > 0)) ||
            (ing.concern_breakdown && ing.concern_breakdown.some((g) => (g.sub_concerns || []).length > 0))
        );

        // Sort by total study count descending, then by INCI name
        listWithArticles.sort((a, b) => {
          const countA = (a.articles?.length || 0) + (a.evidence_scores?.reduce((sum, e) => sum + (e.pubmed_count || 0), 0) || 0);
          const countB = (b.articles?.length || 0) + (b.evidence_scores?.reduce((sum, e) => sum + (e.pubmed_count || 0), 0) || 0);
          if (countB !== countA) return countB - countA;
          return a.inci_name.localeCompare(b.inci_name);
        });

        setIngredients(listWithArticles);
        setUmbrellas(umbData.results || umbData || []);
      } catch (err) {
        console.error('Failed to load ingredient dictionary:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Handle direct navigation to a selected ingredient
  useEffect(() => {
    if (selectedIngredient && ingredients.length > 0) {
      const match = ingredients.find(
        (ing) =>
          ing.inci_name.toLowerCase() === selectedIngredient.toLowerCase() ||
          ing.id === selectedIngredient ||
          (ing.common_name && ing.common_name.toLowerCase() === selectedIngredient.toLowerCase())
      );
      if (match) {
        setOpenIngredientId(match.id);
        setSearchTerm('');
        setSelectedUmbrella('All');
        setTimeout(() => {
          const el = document.getElementById(`ingredient-card-${match.id}`);
          if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
        }, 150);
      }
    }
  }, [selectedIngredient, ingredients]);

  // Filter ingredients by search term and selected umbrella category
  const filteredIngredients = ingredients.filter((ing) => {
    const matchesSearch =
      ing.inci_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (ing.common_name && ing.common_name.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesUmbrella =
      selectedUmbrella === 'All' ||
      (ing.umbrellas && ing.umbrellas.some((u) => u.name === selectedUmbrella));

    return matchesSearch && matchesUmbrella;
  });

  return (
    <div className="ingredient-dictionary-page">
      <div className="dictionary-hero">
        <h1 className="dictionary-title">Ingredient Dictionary</h1>
        <p className="dictionary-subtitle">
          Explore evidence-based skincare actives, their targeted skin concerns, and peer-reviewed PubMed literature.
        </p>

        {/* Search Bar */}
        <div className="dictionary-search-container">
          <svg className="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            type="text"
            className="dictionary-search-input"
            placeholder="Search ingredients by INCI or common name (e.g. Panthenol, Retinol, Niacinamide)..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          {searchTerm && (
            <button className="clear-search-btn" onClick={() => setSearchTerm('')}>×</button>
          )}
        </div>

        {/* Umbrella Category Chips */}
        {umbrellas.length > 0 && (
          <div className="dictionary-umbrella-chips">
            <button
              className={`umbrella-chip ${selectedUmbrella === 'All' ? 'active' : ''}`}
              onClick={() => setSelectedUmbrella('All')}
            >
              All Categories
            </button>
            {umbrellas.map((u) => (
              <button
                key={u.id || u.name}
                className={`umbrella-chip ${selectedUmbrella === u.name ? 'active' : ''}`}
                onClick={() => setSelectedUmbrella(u.name)}
              >
                {u.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Main List */}
      {loading ? (
        <div className="dictionary-loading">Loading scientific literature & ingredient data...</div>
      ) : (
        <div className="dictionary-list-container">
          <div className="dictionary-count-bar">
            <span>Showing {filteredIngredients.length} evidence-backed ingredient{filteredIngredients.length !== 1 ? 's' : ''}</span>
          </div>

          <div className="dictionary-cards-list">
            {filteredIngredients.map((ing) => (
              <IngredientCard
                key={ing.id}
                ingredient={ing}
                isOpen={openIngredientId === ing.id}
                onToggle={() => setOpenIngredientId(openIngredientId === ing.id ? null : ing.id)}
              />
            ))}

            {filteredIngredients.length === 0 && (
              <div className="no-results">
                <h3>No matching ingredients found</h3>
                <p>Try searching for a different INCI name or select "All Categories".</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
