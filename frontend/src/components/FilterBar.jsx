import { categories } from '../data/mockData';

export default function FilterBar({ activeCategory, setActiveCategory }) {
  return (
    <div className="filter-bar-container">
      <div className="filter-pills">
        {categories.map((cat, idx) => (
          <button 
            key={idx} 
            className={`filter-pill ${activeCategory === cat ? 'active' : ''}`}
            onClick={() => setActiveCategory(cat)}
          >
            {cat}
          </button>
        ))}
      </div>
      <div className="filter-actions-right">
         <button className="btn btn-filter">
           <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
             <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
           </svg>
           Filters
         </button>
      </div>
    </div>
  );
}
