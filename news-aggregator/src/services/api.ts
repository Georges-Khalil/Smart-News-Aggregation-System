import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Alert, Platform } from 'react-native';

// Get the appropriate API URL based on the platform
const getApiUrl = () => {
  // For web browser, use localhost
  if (Platform.OS === 'web') {
    return 'http://localhost:8000/api/v1';
  }
  
  // For mobile device using Expo Go, use the computer's IP address
  if (Platform.OS === 'android' || Platform.OS === 'ios') {
    // IMPORTANT: This is the IP address visible to your mobile device
    // We're using the IP address from your Wi-Fi adapter
    return 'http://192.168.0.136:8000/api/v1';
  }
  
  // Default fallback
  return 'http://192.168.0.136:8000/api/v1';
};

// Base API configuration using the platform-appropriate URL
const API_URL = getApiUrl();

console.log(`Using API URL: ${API_URL} for platform: ${Platform.OS}`);

// Create axios instance with default config
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // Increase timeout for mobile networks
  timeout: 15000,
});

// Add request interceptor to attach auth token
api.interceptors.request.use(
  async (config) => {
    // Get token from storage
    const token = await AsyncStorage.getItem('access_token');
    
    // If token exists, add to headers
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => Promise.reject(error)
);

// Authentication APIs
export const authApi = {
  // Login user and get access token
  login: async (email: string, password: string) => {
    try {
      console.log(`Attempting to login with email: ${email}`);
      console.log(`API URL: ${API_URL}/auth/login`);
      
      const formData = new FormData();
      formData.append('username', email); // The backend expects 'username' for email
      formData.append('password', password);
      
      // For debugging on mobile
      if (Platform.OS !== 'web') {
        // Test if the server is reachable using a standard fetch with timeout
        try {
          console.log('Testing server connectivity...');
          // Create a timeout promise
          const timeoutPromise = new Promise<never>((_, reject) => {
            setTimeout(() => reject(new Error('Connection timed out')), 5000);
          });
          
          // Create a fetch promise
          const fetchPromise = fetch(`${API_URL.replace('/api/v1', '')}/docs`, { 
            method: 'GET',
            headers: { 'Accept': 'text/html' }
          });
          
          // Race the fetch against the timeout
          const pingResponse: Response = await Promise.race([fetchPromise, timeoutPromise]);
          console.log('Server ping status:', pingResponse.status);
        } catch (pingError: any) {
          console.error('Server connectivity test failed:', pingError);
          throw new Error(
            `Cannot connect to server at ${API_URL}. ` +
            `Please make sure your phone and computer are on the same network. ` +
            `Error: ${pingError.message || 'Unknown error'}`
          );
        }
      }
      
      console.log('Sending login request...');
      const response = await axios.post(`${API_URL}/auth/login`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 15000, // 15 second timeout
      });
      
      console.log('Login response received:', response.status);
      
      // Store token in AsyncStorage
      if (response.data && response.data.access_token) {
        await AsyncStorage.setItem('access_token', response.data.access_token);
        console.log('Access token stored successfully');
      }
      
      return response.data;
    } catch (error: any) { // Type assertion here
      console.error('Login error:', error);
      
      let errorMessage = "Network error. ";
      
      // More detailed error message based on the error
      if (axios.isAxiosError(error)) {
        console.error('Error details:', {
          status: error.response?.status,
          data: error.response?.data,
          message: error.message,
        });
        
        if (error.message.includes('Network Error')) {
          errorMessage += `Cannot connect to server at ${API_URL}. ` +
            `Please check that:\n` +
            `1. Your phone and computer are on the same WiFi network\n` +
            `2. Your computer's firewall is not blocking connections\n` +
            `3. The backend server is running`;
        } else if (error.response) {
          // The request was made and the server responded with a status code
          // that falls out of the range of 2xx
          errorMessage = `Server error: ${error.response.status} - ${error.response.data?.detail || 'Unknown error'}`;
        } else if (error.request) {
          // The request was made but no response was received
          errorMessage += "Server did not respond. Check that the backend is running.";
        }
      }
      
      // Throw a more informative error
      const enhancedError = new Error(errorMessage);
      throw enhancedError;
    }
  },
  
  // Register new user
  register: async (userData: {
    email: string;
    full_name?: string;
    password: string;
    notification_enabled?: boolean;
    urgency_threshold?: number;
  }) => {
    try {
      console.log(`Attempting to register with email: ${userData.email}`);
      console.log(`API URL: ${API_URL}/auth/register`);
      
      // For mobile, check connectivity first
      if (Platform.OS !== 'web') {
        try {
          console.log('Testing server connectivity before registration...');
          // Create a timeout promise
          const timeoutPromise = new Promise<never>((_, reject) => {
            setTimeout(() => reject(new Error('Connection timed out')), 5000);
          });
          
          // Create a fetch promise
          const fetchPromise = fetch(`${API_URL.replace('/api/v1', '')}/docs`, { 
            method: 'GET',
            headers: { 'Accept': 'text/html' }
          });
          
          // Race the fetch against the timeout
          const pingResponse: Response = await Promise.race([fetchPromise, timeoutPromise]);
          console.log('Server ping status for registration:', pingResponse.status);
        } catch (pingError: any) {
          console.error('Server connectivity test failed during registration:', pingError);
          throw new Error(
            `Cannot connect to server at ${API_URL}. ` +
            `Please make sure your phone and computer are on the same network. ` +
            `Error: ${pingError.message || 'Unknown error'}`
          );
        }
      }
      
      const response = await api.post('/auth/register', userData);
      console.log('Register response received:', response.status);
      return response.data;
    } catch (error: any) { // Type assertion here
      console.error('Registration error:', error);
      if (axios.isAxiosError(error)) {
        console.error('Error details:', {
          status: error.response?.status,
          data: error.response?.data,
          message: error.message,
        });
      }
      throw error;
    }
  },
  
  // Get current user profile
  getProfile: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
  
  // Logout (clear token)
  logout: async () => {
    await AsyncStorage.removeItem('access_token');
  },
  
  // Check if user is authenticated
  isAuthenticated: async () => {
    const token = await AsyncStorage.getItem('access_token');
    return !!token;
  }
};

// Articles APIs
export const articlesApi = {
  // Get recent articles with optional source filtering
  getRecent: async (page = 1, pageSize = 10, sourceFilter?: string[]) => {
    let url = `/articles/recent?page=${page}&page_size=${pageSize}`;
    
    // Add source filter if provided
    if (sourceFilter && sourceFilter.length > 0) {
      sourceFilter.forEach(source => {
        url += `&source_filter=${encodeURIComponent(source)}`;
      });
    }
    
    const response = await api.get(url);
    return response.data;
  },
  
  // Get personalized feed
  getPersonalizedFeed: async (page = 1, pageSize = 10, explorationRatio = 0.2) => {
    const url = `/articles/feed?page=${page}&page_size=${pageSize}&exploration_ratio=${explorationRatio}`;
    const response = await api.get(url);
    return response.data;
  },
  
  // Search articles
  searchArticles: async (params: {
    query: string;
    page?: number;
    pageSize?: number;
    sources?: string[];
    minUrgency?: number;
    sortBy?: 'relevance' | 'recency' | 'urgency';
    personalized?: boolean;
  }) => {
    const {
      query,
      page = 1,
      pageSize = 10,
      sources,
      minUrgency,
      sortBy = 'relevance',
      personalized = true
    } = params;
    
    let url = `/articles/search?query=${encodeURIComponent(query)}&page=${page}&page_size=${pageSize}&sort_by=${sortBy}&personalized=${personalized}`;
    
    if (sources && sources.length > 0) {
      sources.forEach(source => {
        url += `&sources=${encodeURIComponent(source)}`;
      });
    }
    
    if (minUrgency) {
      url += `&min_urgency=${minUrgency}`;
    }
    
    const response = await api.get(url);
    return response.data;
  },
  
  // Get search suggestions
  getSearchSuggestions: async (query: string, limit = 5) => {
    const url = `/articles/search/suggestions?query=${encodeURIComponent(query)}&limit=${limit}`;
    const response = await api.get(url);
    return response.data;
  },
  
  // Record user interaction with article
  recordInteraction: async (interaction: {
    article_id: string;
    liked?: boolean;
    read?: boolean;
    read_time?: number;
  }) => {
    const response = await api.post('/articles/interaction', interaction);
    return response.data;
  },
  
  // Get article by ID
  getArticleById: async (articleId: string) => {
    const response = await api.get(`/articles/${articleId}`);
    return response.data;
  }
};

export default {
  auth: authApi,
  articles: articlesApi
};