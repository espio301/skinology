import { useState, useEffect } from 'react';
import { getConcerns } from '../services/api';
import './AdvancedFilters.css';

export default function AdvancedFilters({ isOpen, onClose, initialFilters, onApply }) {
  const [localFilters, setLocalFilters] = useState(initialFilters);
  const [concernsList, setConcernsList] = useState([]);

  useEffect(() => {
    const fetchConcerns = async () => {
      try {
        const data = await getConcerns();
        setConcernsList(data.results || data);
      } catch (err) {
        console.error('Failed to load concerns:', err);
      }
    };
    fetchConcerns();
  }, []);

  // Update local filters if initialFilters changes (like reset)
  useEffect(() => {
    if (isOpen) {
      setLocalFilters(initialFilters);
    }
  }, [isOpen, initialFilters]);

  if (!isOpen) return null;

  const toggleArrayItem = (array, item) => {
    if (array.includes(item)) {
      return array.filter(i => i !== item);
    }
    return [...array, item];
  };

  const handleApply = () => {
    onApply({ ...initialFilters, ...localFilters });
    onClose();
  };

  return (
    <div className="advanced-filters-panel">
      
      <div className="filters-grid">
        {/* Concerns Pills */}
        <div className="filter-column">
          <label className="section-label">Concerns</label>
          <div className="pill-group">
            {concernsList.map(concern => (
              <button
                key={concern.id}
                className={`filter-pill ${localFilters.concerns.includes(concern.id) ? 'active' : ''}`}
                onClick={() => setLocalFilters({
                  ...localFilters,
                  concerns: toggleArrayItem(localFilters.concerns, concern.id)
                })}
                title={concern.description}
              >
                {concern.label}
              </button>
            ))}
          </div>
        </div>

        {/* Formulation Pills */}
        <div className="filter-column">
          <label className="section-label">Formulation</label>
          <div className="pill-group">
            {['serum', 'moisturizer', 'toner', 'sunscreen', 'cleanser', 'exfoliant', 'oil'].map(type => (
              <button
                key={type}
                className={`filter-pill ${localFilters.product_type.includes(type) ? 'active' : ''}`}
                onClick={() => setLocalFilters({
                  ...localFilters,
                  product_type: toggleArrayItem(localFilters.product_type, type)
                })}
              >
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Sliders & Strength */}
        <div className="filter-column">
          
          <div className="filter-group">
            <div className="group-header">
              <label>Max Price</label>
              <span className="value-display">${localFilters.price_max}</span>
            </div>
            <input 
              type="range" 
              min="5" max="200" step="1"
              value={localFilters.price_max}
              onChange={(e) => setLocalFilters({ ...localFilters, price_max: parseInt(e.target.value) })}
              className="slider"
            />
          </div>

          <div className="filter-group" style={{ marginTop: '20px' }}>
            <div className="group-header">
              <label>pH Range</label>
              <span className="value-display">{localFilters.ph_min} - {localFilters.ph_max}</span>
            </div>
            <div className="dual-slider">
              <span>Min pH:</span>
              <input 
                type="range" 
                min="2.0" max="10.0" step="0.1"
                value={localFilters.ph_min}
                onChange={(e) => setLocalFilters({ ...localFilters, ph_min: parseFloat(e.target.value) })}
                className="slider"
              />
            </div>
            <div className="dual-slider">
              <span>Max pH:</span>
              <input 
                type="range" 
                min="2.0" max="10.0" step="0.1"
                value={localFilters.ph_max}
                onChange={(e) => setLocalFilters({ ...localFilters, ph_max: parseFloat(e.target.value) })}
                className="slider"
              />
            </div>
          </div>

          <div className="filter-group" style={{ marginTop: '20px' }}>
            <label className="section-label">Strength</label>
            <div className="pill-group">
              {['Ultra-Gentle', 'Gentle', 'Moderate', 'Potent', 'Clinical'].map(strength => (
                <button
                  key={strength}
                  className={`filter-pill ${localFilters.strength.includes(strength) ? 'active' : ''}`}
                  onClick={() => setLocalFilters({
                    ...localFilters,
                    strength: toggleArrayItem(localFilters.strength, strength)
                  })}
                >
                  {strength}
                </button>
              ))}
            </div>
          </div>

        </div>
      </div>
      
      <div className="panel-footer">
        <button 
          className="btn btn-outline" 
          onClick={() => setLocalFilters({...initialFilters, price_max: 200, strength: [], concerns: [], product_type: [], ph_min: 2.0, ph_max: 10.0})}
        >
          Clear All
        </button>
        <button className="btn btn-primary" onClick={handleApply}>
          Apply Filters
        </button>
      </div>
    </div>
  );
}
