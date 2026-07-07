import Header from './components/Header';
import Hero from './components/Hero';
import FilterBar from './components/FilterBar';
import ProductList from './components/ProductList';
import './App.css';

function App() {
  return (
    <div className="app-container">
      <Header />
      <main className="main-content">
        <Hero />
        <FilterBar />
        <ProductList />
      </main>
    </div>
  );
}

export default App;
