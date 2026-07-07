import ProductCard from './ProductCard';
import { products } from '../data/mockData';

export default function ProductList() {
  return (
    <section className="product-list-section">
      <div className="product-list-header">
        <h2 className="product-count">{products.length} PRODUCTS</h2>
      </div>
      <div className="product-grid">
        {products.map(product => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    </section>
  );
}
