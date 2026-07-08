import { useState } from 'react';
import Header from './components/Header';
import Hero from './components/Hero';
import FilterBar from './components/FilterBar';
import ProductList from './components/ProductList';
import './App.css';

function App() {
  const [activeCategory, setActiveCategory] = useState('All');

  return (
    <div className="app-container">
      <Header />
      <main className="main-content">
        <Hero />
        <FilterBar activeCategory={activeCategory} setActiveCategory={setActiveCategory} />
        <ProductList activeCategory={activeCategory} />
      </main>
    </div>
  );
}

export default App;
