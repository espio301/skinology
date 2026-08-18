import { useEffect, useState, useRef, useCallback } from 'react';
import ProductCard from './ProductCard';
import { getProducts } from '../services/api';

export default function ProductList({ filters, routine, onToggleRoutine, onNavigateToIngredient }) {
  const [products, setProducts] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  const observerRef = useRef(null);

  // Helper to build API query parameters
  const buildApiParams = useCallback((pageNum) => {
    const apiParams = { page: pageNum };
    if (filters.search && filters.search.trim()) {
      apiParams.search = filters.search.trim();
    }
    if (filters.activeCategory && filters.activeCategory !== 'All') {
      apiParams.ingredient_umbrella = filters.activeCategory;
    }
    if (filters.price_max < 200) apiParams.price_max = filters.price_max;
    if (filters.ph_min > 2.0) apiParams.ph_min = filters.ph_min;
    if (filters.ph_max < 10.0) apiParams.ph_max = filters.ph_max;
    if (filters.product_type && filters.product_type.length > 0) apiParams.product_type = filters.product_type.join(',');
    if (filters.strength && filters.strength.length > 0) apiParams.strength = filters.strength.map(s => s.toLowerCase().replace('-', '_')).join(',');
    if (filters.concerns && filters.concerns.length > 0) {
      apiParams.concerns = filters.concerns.join(',');
      apiParams.concern_priority = filters.concerns.join(',');
    }
    return apiParams;
  }, [filters]);

  // Reset & load initial page whenever filters change
  useEffect(() => {
    let isSubscribed = true;
    const fetchInitialProducts = async () => {
      setLoading(true);
      setPage(1);
      try {
        const data = await getProducts(buildApiParams(1));
        if (isSubscribed) {
          const items = data.results || [];
          setProducts(items);
          setCount(data.count || 0);
          setHasMore(Boolean(data.next));
        }
      } catch (err) {
        console.error('Failed to fetch products:', err);
      } finally {
        if (isSubscribed) setLoading(false);
      }
    };
    fetchInitialProducts();
    return () => { isSubscribed = false; };
  }, [filters, buildApiParams]);

  // Load next page function
  const loadNextPage = useCallback(async () => {
    if (loadingMore || !hasMore || loading) return;
    setLoadingMore(true);
    const nextPage = page + 1;
    try {
      const data = await getProducts(buildApiParams(nextPage));
      const newItems = data.results || [];
      setProducts(prev => {
        const existingIds = new Set(prev.map(p => p.id));
        const filteredNew = newItems.filter(p => !existingIds.has(p.id));
        return [...prev, ...filteredNew];
      });
      setPage(nextPage);
      setHasMore(Boolean(data.next));
    } catch (err) {
      console.error('Failed to fetch next page of products:', err);
    } finally {
      setLoadingMore(false);
    }
  }, [page, hasMore, loadingMore, loading, buildApiParams]);

  // Sentinel ref observer for infinite scrolling
  const sentinelRef = useCallback(node => {
    if (loading || loadingMore) return;
    if (observerRef.current) observerRef.current.disconnect();

    observerRef.current = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting && hasMore) {
        loadNextPage();
      }
    }, { rootMargin: '300px' });

    if (node) observerRef.current.observe(node);
  }, [loading, loadingMore, hasMore, loadNextPage]);

  if (loading) return <div style={{ padding: '30px', textAlign: 'center' }}>Loading products...</div>;

  return (
    <section className="product-list-section">
      <div className="product-list-header">
        <h2 className="product-count">{count} PRODUCTS</h2>
      </div>
      <div className="product-grid">
        {products.map(product => (
          <ProductCard 
            key={product.id} 
            product={product} 
            priorityConcerns={filters.concerns} 
            routine={routine}
            onToggleRoutine={onToggleRoutine}
            onNavigateToIngredient={onNavigateToIngredient}
          />
        ))}
      </div>

      {/* Infinite Scroll Sentinel & Indicator */}
      <div ref={sentinelRef} style={{ height: 50, marginTop: 20, textAlign: 'center', color: '#888' }}>
        {loadingMore && <p>Loading more products...</p>}
        {!hasMore && products.length > 0 && <p style={{ fontSize: '0.85rem', color: '#aaa', marginTop: 10 }}>All {count} products loaded.</p>}
      </div>
    </section>
  );
}
