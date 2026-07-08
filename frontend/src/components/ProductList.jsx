import { useEffect, useState } from 'react';
import ProductCard from './ProductCard';
import { getProducts } from '../services/api';

export default function ProductList({ activeCategory }) {
  const [products, setProducts] = useState([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchProducts = async () => {
      setLoading(true);
      try {
        const filters = {};
        if (activeCategory && activeCategory !== 'All') {
          filters.ingredient_umbrella = activeCategory;
        }

        const data = await getProducts(filters);
        setProducts(data.results || []);
        setCount(data.count || 0);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchProducts();
  }, [activeCategory]);

  if (loading) return <div>Loading products...</div>;

  return (
    <section className="product-list-section">
      <div className="product-list-header">
        <h2 className="product-count">{count} PRODUCTS</h2>
      </div>
      <div className="product-grid">
        {products.map(product => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    </section>
  );
}
