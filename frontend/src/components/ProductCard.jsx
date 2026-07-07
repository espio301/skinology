export default function ProductCard({ product }) {
  return (
    <div className="product-card">
      <div className="product-preview" style={{ backgroundColor: product.color }}>
        <span className="product-type-label">{product.type}</span>
      </div>
      <div className="product-info">
        <span className="product-brand">{product.brand}</span>
        <h3 className="product-name">{product.name}</h3>
        <p className="product-price">{product.price}</p>
        <div className="product-tags">
          {product.tags.map((tag, idx) => (
            <span key={idx} className={`tag ${tag.startsWith('+') ? 'tag-badge' : ''}`}>{tag}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
