import axios from 'axios';

const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/',
  timeout: 5000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getProducts = async (filters = {}) => {
  try {
    const response = await api.get('products/', { params: filters });
    return response.data;
  } catch (error) {
    console.error('Error fetching products:', error);
    throw error;
  }
};

export const getProduct = async (slug) => {
  try {
    const response = await api.get(`products/${slug}/`);
    return response.data;
  } catch (error) {
    console.error('Error fetching product details:', error);
    throw error;
  }
};

export const trackAffiliateClick = async (productId, listingId, sourcePage = '') => {
  try {
    const response = await api.post('events/click/', {
      product: productId,
      retailer_listing: listingId,
      source_page: sourcePage,
    });
    return response.data;
  } catch (error) {
    console.error('Error tracking click:', error);
    throw error;
  }
};

export default api;
