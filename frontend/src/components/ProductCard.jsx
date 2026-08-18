import { useState, useRef, useEffect } from 'react';
import { getProduct } from '../services/api';

/**
 * Calculates responsive inline styles for tooltips to prevent clipping
 * on the left or right edges of the screen/container.
 */
function getTooltipPositionStyle(pillElement, tooltipWidth) {
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
 * Helper to determine concentration zone classification and color styling
 * based on INCI rank order and explicit concentration.
 */
function getConcentrationZoneInfo(order, concentration) {
  if (order && order <= 5) {
    return {
      zoneKey: 'high',
      label: 'Primary Base',
      badgeText: concentration ? `${concentration} (#${order})` : `#${order}`,
      colorClass: 'zone-high',
      desc: 'Top 5 Formulation Base (>1% High Dosage)'
    };
  } else if (order && order <= 10) {
    return {
      zoneKey: 'mid',
      label: 'Active Zone',
      badgeText: concentration ? `${concentration} (#${order})` : `#${order}`,
      colorClass: 'zone-mid',
      desc: 'Active Dosage Zone (~1% Concentration)'
    };
  } else if (order && order < 99) {
    return {
      zoneKey: 'low',
      label: 'Trace / Booster',
      badgeText: concentration ? `${concentration} (#${order})` : `#${order}`,
      colorClass: 'zone-low',
      desc: 'Trace / Support Booster Zone (<1% Dosage)'
    };
  } else {
    return {
      zoneKey: 'mid',
      label: 'Active',
      badgeText: concentration || 'Active',
      colorClass: 'zone-mid',
      desc: 'Formulation Active'
    };
  }
}

function ingredientHasDictionaryEntry(ing) {
  if (!ing) return false;
  const hasArticles = ing.articles && ing.articles.length > 0;
  const hasScores = ing.evidence_scores && ing.evidence_scores.some(e => (e.pubmed_count || 0) > 0);
  const hasBreakdown = ing.concern_breakdown && ing.concern_breakdown.some(g => (g.sub_concerns || []).length > 0);
  const hasCount = (ing.count || 0) > 0;
  return Boolean(hasArticles || hasScores || hasBreakdown || hasCount);
}


/**
 * pH badge with confidence tooltip.
 * Shows the estimated pH value and, on hover, displays a tooltip
 * explaining the confidence level and methodology.
 */
function PhBadge({ ph, confidence, explanation }) {
  const [showTip, setShowTip] = useState(false);
  const confColors = {
    high: '#2e7d32',
    medium: '#ed6c02',
    low: '#9e9e9e',
  };
  const confLabels = {
    high: 'High',
    medium: 'Medium',
    low: 'Low',
  };
  const dotColor = confColors[confidence] || '#9e9e9e';
  const confLabel = confLabels[confidence] || 'Unknown';

  return (
    <span
      className="ph-badge"
      onMouseEnter={() => setShowTip(true)}
      onMouseLeave={() => setShowTip(false)}
      style={{
        position: 'relative',
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        padding: '4px 10px',
        borderRadius: 20,
        background: '#f5f0eb',
        border: '1px solid #e0d5cc',
        fontSize: '0.78rem',
        fontWeight: 600,
        color: '#5a4a3f',
        cursor: 'help',
      }}
    >
      <span style={{ fontSize: '0.72rem', opacity: 0.7 }}>est. pH</span>
      <span>{ph}</span>
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: dotColor,
          flexShrink: 0,
        }}
        title={`Confidence: ${confLabel}`}
      />
      {showTip && explanation && (
        <div
          className="ph-confidence-tooltip"
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            marginTop: 6,
            width: 280,
            padding: '10px 12px',
            background: '#fff',
            border: '1px solid #e0d5cc',
            borderRadius: 8,
            boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
            zIndex: 100,
            fontSize: '0.74rem',
            lineHeight: 1.5,
            color: '#3d3028',
            fontWeight: 400,
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: dotColor }} />
            {confLabel} Confidence
          </div>
          {explanation}
        </div>
      )}
    </span>
  );
}


/**
 * Strength / Potency badge with hover explanation tooltip.
 * Explains the key driving active ingredient and formulation tier.
 */
function StrengthBadge({ strength, label, explanation }) {
  const [showTip, setShowTip] = useState(false);

  return (
    <span
      className={`strength-badge strength-${strength}`}
      onMouseEnter={() => setShowTip(true)}
      onMouseLeave={() => setShowTip(false)}
      style={{
        position: 'relative',
        cursor: 'help',
      }}
    >
      {label}
      {showTip && (
        <div
          className="strength-explanation-tooltip"
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            marginTop: 6,
            width: 280,
            padding: '10px 12px',
            background: '#fff',
            border: '1px solid #e0d5cc',
            borderRadius: 8,
            boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
            zIndex: 100,
            fontSize: '0.74rem',
            lineHeight: 1.5,
            color: '#3d3028',
            fontWeight: 400,
            textAlign: 'left',
            whiteSpace: 'normal',
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{ fontSize: '0.8rem' }}>⚡</span>
            {label} Potency Rating
          </div>
          {explanation || `Classified as ${label} based on formulation strength and active ingredients.`}
        </div>
      )}
    </span>
  );
}

function IngredientPill({ ingredient, productConcerns, order, concentration, onNavigateToIngredient }) {
  const [showTooltip, setShowTooltip] = useState(false);
  const pillRef = useRef(null);
  const [tooltipStyle, setTooltipStyle] = useState({});
  const hasArticles = ingredient.articles && ingredient.articles.length > 0;
  const zoneInfo = getConcentrationZoneInfo(order, concentration);
  const inDictionary = ingredientHasDictionaryEntry(ingredient);

  // Determine highest matching tier for current product's concerns, fallback to top overall tier
  let displayTier = null;
  let displayCount = 0;
  if (ingredient.evidence_scores && ingredient.evidence_scores.length > 0) {
    let scoresToConsider = ingredient.evidence_scores;

    // Filter to product concerns if there are any
    if (productConcerns && productConcerns.length > 0) {
      const matchedScores = ingredient.evidence_scores.filter(
        score => productConcerns.some(pc => pc.internal_key === score.concern.internal_key)
      );
      if (matchedScores.length > 0) {
        scoresToConsider = matchedScores;
      }
    }

    // Pick best tier. Order: well_founded > studied > prospective
    const tierRank = { 'well_founded': 3, 'studied': 2, 'prospective': 1 };
    const bestScore = scoresToConsider.sort((a, b) => tierRank[b.evidence_tier] - tierRank[a.evidence_tier])[0];
    displayTier = bestScore.evidence_tier;
    displayCount = bestScore.pubmed_count;
  }

  const tierClass = displayTier ? `tier-${displayTier}` : '';

  const handleMouseEnter = () => {
    if (pillRef.current) {
      setTooltipStyle(getTooltipPositionStyle(pillRef.current, 260));
    }
    setShowTooltip(true);
  };

  const handlePillClick = (e) => {
    e.stopPropagation();
    if (inDictionary && onNavigateToIngredient) {
      onNavigateToIngredient(ingredient.inci_name);
    }
  };

  return (
    <div 
      ref={pillRef}
      className="ingredient-pill-container"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={() => setShowTooltip(false)}
      onClick={handlePillClick}
      style={{ cursor: inDictionary ? 'pointer' : 'default' }}
      title={inDictionary ? 'Click to view in Ingredient Dictionary' : undefined}
    >
      <span className={`key-active-ingredient ${tierClass} ${hasArticles ? 'has-articles' : ''}`}>
        {order && order < 99 && (
          <span className={`rank-badge ${zoneInfo.colorClass}`} style={{ marginRight: 4 }} title={zoneInfo.desc}>
            #{order}
          </span>
        )}
        {ingredient.inci_name}
        {displayTier ? (
          <span className="article-badge" style={{ marginLeft: 6 }}>{displayCount}</span>
        ) : hasArticles ? (
          <span className="article-badge" style={{ marginLeft: 6 }}>{ingredient.articles.length}</span>
        ) : null}
      </span>
      {showTooltip && (
        <div className="ingredient-tooltip" style={tooltipStyle}>
          <div className="tooltip-header-info">
            <h5 className="tooltip-title">Research Papers</h5>
            {order && order < 99 && (
              <div className="tooltip-rank-row">
                <span className={`tooltip-zone-badge ${zoneInfo.colorClass}`}>
                  Rank #{order} · {zoneInfo.label}
                </span>
                {concentration && (
                  <span className="tooltip-concentration-declared">
                    Declared: {concentration}
                  </span>
                )}
              </div>
            )}
          </div>
          {hasArticles && (
            <ul className="tooltip-articles">
              {ingredient.articles.map(article => (
                <li key={article.id} className="tooltip-article-item">
                  <a href={article.url} target="_blank" rel="noopener noreferrer">
                    {article.title}
                  </a>
                  <span className="tooltip-article-source">{article.source}</span>
                </li>
              ))}
            </ul>
          )}
          {inDictionary && onNavigateToIngredient && (
            <button
              className="tooltip-search-link"
              style={{ width: '100%', textAlign: 'center', marginTop: 8, background: '#fef8f5', border: '1px solid #f5d3c8', borderRadius: 6, color: '#c0522a', cursor: 'pointer', padding: '5px 0' }}
              onClick={(e) => {
                e.stopPropagation();
                onNavigateToIngredient(ingredient.inci_name);
              }}
            >
              View in Ingredient Dictionary →
            </button>
          )}
        </div>
      )}
    </div>
  );
}


/**
 * Standalone evidence pill for the concern breakdown cards.
 * Click to show a tooltip with up to 5 PubMed article links.
 */
function ConcernIngredientPill({ ing, isOpen, onToggleTooltip, onNavigateToIngredient }) {
  const pillRef = useRef(null);
  const [tooltipStyle, setTooltipStyle] = useState({});
  const tierClass = ing.tier ? `tier-${ing.tier}` : '';
  const hasArticles = ing.articles && ing.articles.length > 0;
  const hasQuery = ing.query_used && ing.query_used.length > 0;
  const inDictionary = ingredientHasDictionaryEntry(ing);

  useEffect(() => {
    if (isOpen && pillRef.current) {
      setTooltipStyle(getTooltipPositionStyle(pillRef.current, 280));
    }
  }, [isOpen]);

  const handleClick = (e) => {
    e.stopPropagation();
    if (hasArticles || hasQuery || (ing.order && ing.order < 99)) {
      onToggleTooltip();
    } else if (inDictionary && onNavigateToIngredient) {
      onNavigateToIngredient(ing.inci_name);
    }
  };

  const pubmedSearchUrl = hasQuery
    ? `https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(ing.query_used)}`
    : null;

  return (
    <div
      ref={pillRef}
      className="concern-pill-wrapper"
      onClick={handleClick}
    >
      <span className={`concern-pill-ingredient ${tierClass} ${hasArticles || hasQuery ? 'has-articles' : ''}`}>
        {ing.inci_name}
        {ing.count > 0 && (
          <span className="article-badge" style={{ marginLeft: 4 }}>{ing.count}</span>
        )}
      </span>
      {isOpen && (hasArticles || hasQuery || (ing.order && ing.order < 99)) && (
        <div className="concern-pill-tooltip" style={tooltipStyle} onClick={e => e.stopPropagation()}>
          <div className="tooltip-header-info">
            <h5 className="tooltip-title">
              PubMed Studies
              <span className="tooltip-count">{ing.count || 0} total</span>
            </h5>
            {ing.order && ing.order < 99 && (
              <div className="tooltip-rank-row" style={{ marginTop: 4 }}>
                <span style={{ color: '#94a3b8', fontSize: '0.78rem', fontWeight: 500 }}>
                  ingredient number: {ing.order}
                </span>
                {ing.concentration && (
                  <span className="tooltip-concentration-declared" style={{ marginLeft: 6 }}>
                    · Declared: {ing.concentration}
                  </span>
                )}
              </div>
            )}
          </div>
          {hasArticles && (
            <ul className="tooltip-articles">
              {ing.articles.map(article => (
                <li key={article.pmid} className="tooltip-article-item">
                  <a
                    href={`https://pubmed.ncbi.nlm.nih.gov/${article.pmid}/`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {article.title}
                  </a>
                  <span className="tooltip-article-source">
                    PubMed · {article.year}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
            {inDictionary && onNavigateToIngredient && (
              <button
                className="tooltip-search-link"
                style={{ width: '100%', textAlign: 'center', background: '#fef8f5', border: '1px solid #f5d3c8', borderRadius: 6, color: '#c0522a', cursor: 'pointer', padding: '6px 0', fontSize: '0.78rem', fontWeight: 600 }}
                onClick={(e) => {
                  e.stopPropagation();
                  onNavigateToIngredient(ing.inci_name);
                }}
              >
                View in Ingredient Dictionary →
              </button>
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
        </div>
      )}
    </div>
  );
}

/**
 * Expandable concern card within the "Targeted Concerns" section.
 * Shows parent concern as header; click to reveal sub-concerns + ingredient pills.
 */
function ConcernCard({ group, isOpen, onToggle, onNavigateToIngredient }) {
  const [openPillKey, setOpenPillKey] = useState(null);

  // Filter sub-concerns to only include ingredients with over 10 studies backing them
  const subConcernsWithFilteredIngredients = group.sub_concerns
    .map(sc => ({
      ...sc,
      ingredients: sc.ingredients.filter(ing => (ing.count || 0) > 10)
    }))
    .filter(sc => sc.ingredients.length > 0);

  // Total unique ingredients across all sub-concerns (only >10 studies)
  const allIngredientIds = new Set();
  subConcernsWithFilteredIngredients.forEach(sc =>
    sc.ingredients.forEach(ing => allIngredientIds.add(ing.id))
  );
  const ingredientCount = allIngredientIds.size;

  // Close open pill tooltip when clicking outside or closing concern card
  useEffect(() => {
    if (!openPillKey) return;
    const handleOutsideClick = () => setOpenPillKey(null);
    window.addEventListener('click', handleOutsideClick);
    return () => window.removeEventListener('click', handleOutsideClick);
  }, [openPillKey]);

  return (
    <div
      className={`concern-card ${isOpen ? 'concern-card--open' : ''}`}
      onClick={onToggle}
    >
      <div className="concern-card-header">
        <span className="concern-card-name">{group.parent.label}</span>
        <span className="concern-card-count">
          {ingredientCount} supporting ingredient{ingredientCount !== 1 ? 's' : ''} (&gt;10 studies)
        </span>
      </div>
      {isOpen && (
        <div className="concern-card-body">
          {subConcernsWithFilteredIngredients.length > 0 ? (
            subConcernsWithFilteredIngredients.map(sc => {
              const sortedIngredients = [...sc.ingredients].sort(
                (a, b) => (a.order || 99) - (b.order || 99)
              );
              return (
                <div key={sc.concern.id} className="concern-subconcern">
                  <span className="concern-subconcern-label">{sc.concern.label}</span>
                  <div className="concern-subconcern-pills">
                    {sortedIngredients.map(ing => {
                      const pillKey = `${sc.concern.id}-${ing.id}`;
                      return (
                        <ConcernIngredientPill
                          key={pillKey}
                          ing={ing}
                          isOpen={openPillKey === pillKey}
                          onToggleTooltip={() => setOpenPillKey(openPillKey === pillKey ? null : pillKey)}
                          onNavigateToIngredient={onNavigateToIngredient}
                        />
                      );
                    })}
                  </div>
                </div>
              );
            })
          ) : (
            <p className="no-ingredients-hint" style={{ fontSize: '0.78rem', color: '#64748b', fontStyle: 'italic', margin: '4px 0 0' }}>
              No ingredients with &gt;10 studies found for this concern.
            </p>
          )}
        </div>
      )}
    </div>
  );
}



export default function ProductCard({ product, priorityConcerns, routine = [], onToggleRoutine, forceExpanded = false, onNavigateToIngredient }) {
  const [expanded, setExpanded] = useState(forceExpanded);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showFullInci, setShowFullInci] = useState(false);
  const [expandedUmbrella, setExpandedUmbrella] = useState(null);
  const [expandedConcern, setExpandedConcern] = useState(null);

  const inRoutine = routine && routine.some(p => p.id === product.id);

  // Automatically fetch details if forceExpanded is true
  useEffect(() => {
    const checkAndFetchDetails = async () => {
      if (expanded && !detail) {
        setLoading(true);
        try {
          const data = await getProduct(product.slug);
          setDetail(data);
        } catch (err) {
          console.error('Failed to fetch product detail:', err);
        } finally {
          setLoading(false);
        }
      }
    };
    checkAndFetchDetails();
  }, [expanded, detail, product.slug]);

  useEffect(() => {
    setExpanded(forceExpanded);
  }, [forceExpanded]);

  const priceDisplay = product.min_price ? `$${product.min_price}` : 'Check Price';
  const tags = (product.concerns || []).filter(c => !c.parent_id).map(c => c.label);
  // Fallback: if no parent-level concerns, show sub-concerns
  const displayTags = tags.length > 0 ? tags : (product.concerns || []).map(c => c.label);

  const handleClick = async () => {
    if (expanded) {
      setExpanded(false);
      return;
    }

    // Fetch detail data if we don't have it yet
    if (!detail) {
      setLoading(true);
      try {
        const data = await getProduct(product.slug);
        setDetail(data);
      } catch (err) {
        console.error('Failed to fetch product detail:', err);
      } finally {
        setLoading(false);
      }
    }
    setExpanded(true);
  };

  // Build umbrella → ingredients map from product_ingredients
  const getUmbrellaMap = () => {
    if (!detail) return {};
    const map = {};
    for (const pi of detail.product_ingredients) {
      for (const umb of pi.ingredient.umbrellas) {
        if (!map[umb.name]) {
          map[umb.name] = { description: umb.description, ingredients: [] };
        }
        map[umb.name].ingredients.push(pi.ingredient);
      }
    }
    return map;
  };

  const umbrellaMap = detail ? getUmbrellaMap() : {};
  const concernBreakdown = detail?.concern_breakdown || [];

  const getSortedConcernBreakdown = () => {
    if (!concernBreakdown || concernBreakdown.length === 0) return [];
    if (!priorityConcerns || priorityConcerns.length === 0) return concernBreakdown;

    const keyMap = {};
    priorityConcerns.forEach((k, idx) => {
      keyMap[String(k).toLowerCase()] = idx;
    });

    return [...concernBreakdown].sort((a, b) => {
      const keyA1 = String(a.parent.id).toLowerCase();
      const keyA2 = String(a.parent.internal_key).toLowerCase();
      const keyB1 = String(b.parent.id).toLowerCase();
      const keyB2 = String(b.parent.internal_key).toLowerCase();

      const idxA = keyMap[keyA1] ?? keyMap[keyA2] ?? 999;
      const idxB = keyMap[keyB1] ?? keyMap[keyB2] ?? 999;

      return idxA - idxB;
    });
  };

  const sortedConcernBreakdown = getSortedConcernBreakdown();

  return (
    <div className={`product-card ${expanded ? 'product-card--expanded' : ''}`} onClick={handleClick}>
      <div className="product-preview" style={{ backgroundColor: '#f0f0f0' }}>
        {product.image_url && <img src={product.image_url} alt={product.name} style={{ width: '100%', height: '100%', objectFit: 'contain' }} />}
      </div>
      <div className="product-info">
        <span className="product-brand">{product.brand}</span>
        <h3 className="product-name">{product.name}</h3>
        <p className="product-price">{priceDisplay}</p>
        
        {onToggleRoutine && (
          <div className="product-card-actions" onClick={e => e.stopPropagation()}>
            <button 
              className={`btn-add-routine ${inRoutine ? 'active' : ''}`}
              onClick={() => onToggleRoutine(product)}
            >
              {inRoutine ? (
                <>
                  <svg className="icon check-icon animate-pop" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 13, height: 13, marginRight: 4 }}>
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                  In Routine
                </>
              ) : (
                <>
                  <svg className="icon plus-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 13, height: 13, marginRight: 4 }}>
                    <line x1="12" y1="5" x2="12" y2="19"></line>
                    <line x1="5" y1="12" x2="19" y2="12"></line>
                  </svg>
                  Add to Routine
                </>
              )}
            </button>
          </div>
        )}

        <div className="product-tags">
          {displayTags.slice(0, expanded ? displayTags.length : 3).map((tag, idx) => (
            <span key={idx} className={`tag ${tag.startsWith('+') ? 'tag-badge' : ''}`}>{tag}</span>
          ))}
          {!expanded && displayTags.length > 3 && (
            <span className="tag tag-badge">+{displayTags.length - 3}</span>
          )}
        </div>
      </div>

      {/* Expanded Section */}
      {expanded && (
        <div className="product-expanded" onClick={e => e.stopPropagation()}>
          {loading && <p className="expanded-loading">Loading details...</p>}

          {detail && (
            <>
              {/* pH & Strength badges */}
              {(detail.avg_ph || detail.strength_label) && (
                <div className="expanded-section" style={{ paddingBottom: 0 }}>
                  <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
                    {detail.avg_ph != null && (
                      <PhBadge
                        ph={detail.avg_ph}
                        confidence={detail.ph_confidence}
                        explanation={detail.ph_confidence_explanation}
                      />
                    )}
                    {detail.strength_label && (
                      <StrengthBadge
                        strength={detail.strength}
                        label={detail.strength_label}
                        explanation={detail.strength_explanation}
                      />
                    )}
                  </div>
                </div>
              )}

              {/* Concern Breakdown (hierarchical) */}
              <div className="expanded-section">
                <h4 className="expanded-label">Targeted Concerns</h4>
                {sortedConcernBreakdown.length > 0 ? (
                  <div className="concern-cards-grid">
                    {sortedConcernBreakdown.map(group => (
                      <ConcernCard
                        key={group.parent.id}
                        group={group}
                        isOpen={expandedConcern === group.parent.id}
                        onToggle={() =>
                          setExpandedConcern(
                            expandedConcern === group.parent.id ? null : group.parent.id
                          )
                        }
                        onNavigateToIngredient={onNavigateToIngredient}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="concern-list">
                    {detail.concerns.map(c => (
                      <span key={c.id} className="concern-chip">{c.label}</span>
                    ))}
                  </div>
                )}
              </div>

              {/* Key Active Ingredients / Full INCI toggle */}
              <div className="expanded-section">
                <div className="expanded-section-header">
                  <h4 className="expanded-label">
                    {showFullInci ? 'Full Ingredients' : 'Key Active Ingredients'}
                  </h4>
                  <button
                    className="toggle-inci-btn"
                    onClick={() => { setShowFullInci(!showFullInci); setExpandedUmbrella(null); }}
                  >
                    {showFullInci ? 'Show Key Actives' : 'Show All Ingredients'}
                  </button>
                </div>

                {showFullInci ? (
                  <ul className="full-inci-list">
                    {detail.product_ingredients.map(pi => {
                      const inDict = ingredientHasDictionaryEntry(pi.ingredient);
                      return (
                        <li key={pi.id} className="inci-item">
                          {inDict ? (
                            <span 
                              className="inci-name" 
                              style={{ cursor: 'pointer', textDecoration: 'underline', color: '#c0522a' }}
                              onClick={(e) => {
                                e.stopPropagation();
                                if (onNavigateToIngredient) onNavigateToIngredient(pi.ingredient.inci_name);
                              }}
                              title="Click to view in Ingredient Dictionary"
                            >
                              {pi.ingredient.inci_name}
                            </span>
                          ) : (
                            <span className="inci-name">{pi.ingredient.inci_name}</span>
                          )}
                          {pi.ingredient.umbrellas.length > 0 && (
                            <span className="inci-umbrella-tags">
                              {pi.ingredient.umbrellas.map(u => u.name).join(', ')}
                            </span>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  <div className="key-actives-grid">
                    {Object.entries(umbrellaMap).map(([name, data]) => (
                      <div
                        key={name}
                        className={`key-active-card ${expandedUmbrella === name ? 'key-active-card--open' : ''}`}
                        onClick={() => setExpandedUmbrella(expandedUmbrella === name ? null : name)}
                      >
                        <span className="key-active-name">{name}</span>
                        {expandedUmbrella === name ? (
                          <div className="key-active-ingredients">
                            {data.ingredients.map((ing, i) => {
                              const pi = detail.product_ingredients.find(p => p.ingredient.id === ing.id);
                              return (
                                <IngredientPill
                                  key={i}
                                  ingredient={ing}
                                  productConcerns={detail.concerns}
                                  order={pi?.order}
                                  concentration={pi?.concentration}
                                  onNavigateToIngredient={onNavigateToIngredient}
                                />
                              );
                            })}
                          </div>
                        ) : (
                          <span className="key-active-desc">
                            {data.description || `${data.ingredients.length} ingredient${data.ingredients.length > 1 ? 's' : ''} found`}
                          </span>
                        )}
                      </div>
                    ))}
                    {Object.keys(umbrellaMap).length === 0 && (
                      <p className="no-actives">No key active ingredient categories found.</p>
                    )}
                  </div>
                )}
              </div>

              {/* Purchase Links */}
              {detail.retailer_listings && detail.retailer_listings.length > 0 && (
                <div className="expanded-section">
                  <h4 className="expanded-label">Where to Buy</h4>
                  <div className="purchase-links">
                    {detail.retailer_listings.filter(l => l.in_stock).map(listing => (
                      <a
                        key={listing.id}
                        href={listing.affiliate_url || listing.product_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="purchase-link"
                      >
                        <span className="retailer-name">{listing.retailer?.name || 'Buy'}</span>
                        <span className="retailer-price">${listing.price}</span>
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Collapse button */}
              <button className="collapse-btn" onClick={() => setExpanded(false)}>
                Collapse ▲
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
