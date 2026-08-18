import { useState, useEffect } from 'react';
import ProductCard from './ProductCard';

export default function Hero({ showRoutine, routine, toggleRoutineItem }) {
  const [activeProduct, setActiveProduct] = useState(null);

  // Clear active preview if the active product is removed from routine
  useEffect(() => {
    if (activeProduct && !routine.some(p => p.id === activeProduct.id)) {
      setActiveProduct(null);
    }
  }, [routine, activeProduct]);

  // Clear active product if routine view is closed
  useEffect(() => {
    if (!showRoutine) {
      setActiveProduct(null);
    }
  }, [showRoutine]);

  if (showRoutine) {
    return (
      <section className="hero routine-hero-banner">
        <div className="hero-subtitle">
          <svg className="icon small-beaker" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4.5 3h15"/><path d="M6 3v16a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V3"/><path d="M6 14h12"/>
          </svg>
          <span>YOUR SCIENCE-BACKED REGIMEN</span>
        </div>
        <h1 className="hero-title">my routine<span className="dot">.</span></h1>

        {routine.length === 0 ? (
          <p className="hero-description empty-routine-msg">
            Your routine is currently empty. Browse the product catalog below and click the <strong>Add to Routine</strong> button on any product card to start building your science-backed regimen.
          </p>
        ) : (
          <div className="routine-container">
            <div className="routine-scroll-wrapper">
              {routine.map(prod => {
                const isActive = activeProduct && activeProduct.id === prod.id;
                return (
                  <div 
                    key={prod.id} 
                    className={`routine-item-compact ${isActive ? 'active' : ''}`}
                    onClick={() => setActiveProduct(isActive ? null : prod)}
                  >
                    <div className="routine-item-preview-box">
                      {prod.image_url ? (
                        <img src={prod.image_url} alt={prod.name} className="routine-item-image" />
                      ) : (
                        <div className="routine-item-image-placeholder">
                          {prod.product_type?.substring(0, 3).toUpperCase() || 'SKIN'}
                        </div>
                      )}
                      <button 
                        className="routine-item-remove-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleRoutineItem(prod);
                        }}
                        title="Remove from routine"
                      >
                        <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 12, height: 12 }}>
                          <line x1="18" y1="6" x2="6" y2="18"></line>
                          <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                      </button>
                    </div>
                    <div className="routine-item-meta">
                      <span className="routine-item-brand">{prod.brand}</span>
                      <span className="routine-item-name">{prod.name}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {activeProduct && (
              <div className="routine-active-detail-panel animate-slide-down">
                <div className="routine-detail-header">
                  <span className="routine-detail-label">Routine Product Science details</span>
                  <button className="routine-detail-close-btn" onClick={() => setActiveProduct(null)}>
                    Close Details
                  </button>
                </div>
                <div className="routine-detail-card-container">
                  <ProductCard 
                    product={activeProduct} 
                    priorityConcerns={[]} 
                    routine={routine} 
                    onToggleRoutine={toggleRoutineItem}
                    forceExpanded={true}
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </section>
    );
  }

  return (
    <section className="hero">
      <div className="hero-subtitle">
        <svg className="icon small-beaker" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4.5 3h15"/><path d="M6 3v16a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V3"/><path d="M6 14h12"/>
        </svg>
        <span>EVIDENCE-BASED SKINCARE</span>
      </div>
      <h1 className="hero-title">skinstudy<span className="dot">.</span></h1>
      <p className="hero-description">
        Every product. Every ingredient. Every claim — verified against peer-reviewed research. Build a routine grounded in science, not marketing.
      </p>
    </section>
  );
}
