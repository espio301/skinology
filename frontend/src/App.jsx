import { useState } from 'react';
import Header from './components/Header';
import Hero from './components/Hero';
import FilterBar from './components/FilterBar';
import ProductList from './components/ProductList';
import IngredientDictionary from './components/IngredientDictionary';
import './App.css';

const defaultFilters = {
  activeCategory: 'All',
  search: '',
  price_max: 200,
  ph_min: 2.0,
  ph_max: 10.0,
  product_type: [],
  concerns: [],
  strength: []
};

function App() {
  const [filters, setFilters] = useState(defaultFilters);
  const [showRoutine, setShowRoutine] = useState(false);
  const [currentView, setCurrentView] = useState('products'); // 'products' | 'dictionary'
  const [selectedDictionaryIngredient, setSelectedDictionaryIngredient] = useState(null);
  const [routine, setRoutine] = useState(() => {
    const saved = localStorage.getItem('skinstudy_routine');
    return saved ? JSON.parse(saved) : [];
  });

  const handleViewChange = (view) => {
    setCurrentView(view);
    if (view === 'dictionary') {
      setShowRoutine(false);
    }
  };

  const handleNavigateToIngredient = (inciNameOrId) => {
    setSelectedDictionaryIngredient(inciNameOrId);
    setCurrentView('dictionary');
    setShowRoutine(false);
  };

  const handleSetShowRoutine = (show) => {
    setShowRoutine(show);
    if (show) {
      setCurrentView('products');
    }
  };

  const toggleRoutineItem = (product) => {
    const exists = routine.some(p => p.id === product.id);
    let updated;
    if (exists) {
      updated = routine.filter(p => p.id !== product.id);
    } else {
      updated = [...routine, product];
    }
    setRoutine(updated);
    localStorage.setItem('skinstudy_routine', JSON.stringify(updated));
  };

  return (
    <div className="app-container">
      <Header
        showRoutine={showRoutine}
        setShowRoutine={handleSetShowRoutine}
        currentView={currentView}
        onViewChange={handleViewChange}
        routineCount={routine.length}
      />
      <main className="main-content">
        {currentView === 'dictionary' ? (
          <IngredientDictionary selectedIngredient={selectedDictionaryIngredient} />
        ) : (
          <>
            <Hero showRoutine={showRoutine} routine={routine} toggleRoutineItem={toggleRoutineItem} />
            <FilterBar filters={filters} setFilters={setFilters} />
            <ProductList
              filters={filters}
              routine={routine}
              onToggleRoutine={toggleRoutineItem}
              onNavigateToIngredient={handleNavigateToIngredient}
            />
          </>
        )}
      </main>
    </div>
  );
}

export default App;
