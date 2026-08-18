import { useEffect, useState } from 'react';
import { getUmbrellas, getConcerns } from '../services/api';
import AdvancedFilters from './AdvancedFilters';
import ConcernPriorityBar from './ConcernPriorityBar';

export default function FilterBar({ filters, setFilters }) {
  const [categories, setCategories] = useState(['All']);
  const [concernsList, setConcernsList] = useState([]);
  const [isAdvancedFiltersOpen, setIsAdvancedFiltersOpen] = useState(false);
  const [showCallout, setShowCallout] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [umbData, concData] = await Promise.all([
          getUmbrellas(),
          getConcerns(),
        ]);
        const names = (umbData.results || umbData).map(u => u.name);
        setCategories(['All', ...names]);
        setConcernsList(concData.results || concData);
      } catch (err) {
        console.error('Failed to load filter bar metadata:', err);
      }
    };
    fetchData();
  }, []);

  const handlePriorityChange = (newPriorityOrder) => {
    setFilters({
      ...filters,
      concerns: newPriorityOrder,
    });
  };

  return (
    <div className="filter-bar-wrapper">
      <div className="filter-bar-container">
        <div className="filter-pills">
          {categories.map((cat, idx) => (
            <button 
              key={idx} 
              className={`filter-pill ${filters.activeCategory === cat ? 'active' : ''}`}
              onClick={() => setFilters({ ...filters, activeCategory: cat })}
            >
              {cat}
            </button>
          ))}
        </div>
        <div className="filter-actions-right">
           <div className="search-bar-box">
             <svg className="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
               <circle cx="11" cy="11" r="8"></circle>
               <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
             </svg>
             <input
               type="text"
               className="search-input"
               placeholder="Search product or brand..."
               value={filters.search || ''}
               onChange={(e) => setFilters({ ...filters, search: e.target.value })}
             />
             {filters.search && (
               <button 
                 className="search-clear-btn"
                 onClick={() => setFilters({ ...filters, search: '' })}
                 title="Clear search"
               >
                 ×
               </button>
             )}
           </div>

           <div className="filter-btn-wrapper">
             {showCallout && (!filters.concerns || filters.concerns.length === 0) && (
               <div className="concern-floating-callout" onClick={() => setIsAdvancedFiltersOpen(true)}>
                 <span>have a specific concern?</span>
                 <button 
                   className="callout-close-btn"
                   onClick={(e) => {
                     e.stopPropagation();
                     setShowCallout(false);
                   }}
                   title="Dismiss"
                 >
                   ×
                 </button>
                 <div className="callout-arrow"></div>
               </div>
             )}
             <button className="btn btn-filter" onClick={() => setIsAdvancedFiltersOpen(!isAdvancedFiltersOpen)}>
               <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                 <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
               </svg>
               Filters {filters.concerns && filters.concerns.length > 0 ? `(${filters.concerns.length})` : ''}
             </button>
           </div>
        </div>
      </div>
      
      {/* Priority Bar for Selected Concerns */}
      {filters.concerns && filters.concerns.length > 0 && (
        <ConcernPriorityBar
          concernsList={concernsList}
          selectedConcerns={filters.concerns}
          onPriorityChange={handlePriorityChange}
        />
      )}

      <AdvancedFilters 
        isOpen={isAdvancedFiltersOpen} 
        onClose={() => setIsAdvancedFiltersOpen(false)} 
        initialFilters={filters}
        onApply={setFilters}
      />
    </div>
  );
}
