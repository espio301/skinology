export default function ProductCard({ product }) {
  const priceDisplay = product.min_price ? `$${product.min_price}` : 'Check Price';
  const typeLabel = product.product_type ? product.product_type.toUpperCase() : 'OTHER';
  const tags = (product.concerns || []).map(c => c.label);

  return (
    <div className="product-card">
      <div className="product-preview" style={{ backgroundColor: product.color || '#f0f0f0' }}>
        {product.image_url && <img src={product.image_url} alt={product.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />}
        <span className="product-type-label">{typeLabel}</span>
      </div>
      <div className="product-info">
        <span className="product-brand">{product.brand}</span>
        <h3 className="product-name">{product.name}</h3>
        <p className="product-price">{priceDisplay}</p>
        <div className="product-tags">
          {tags.map((tag, idx) => (
            <span key={idx} className={`tag ${tag.startsWith('+') ? 'tag-badge' : ''}`}>{tag}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
