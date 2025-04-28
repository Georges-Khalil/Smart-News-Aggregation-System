import React, { createContext, useState, useEffect, useContext, ReactNode } from 'react';
import { authApi } from '../services/api';

// Define the AuthContext types
type User = {
  id: string;
  email: string;
  full_name?: string;
  notification_enabled: boolean;
  urgency_threshold: number;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
};

type AuthContextType = {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (userData: {
    email: string;
    full_name?: string;
    password: string;
    notification_enabled?: boolean;
    urgency_threshold?: number;
  }) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
};

// Create the AuthContext
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Provider component
type AuthProviderProps = {
  children: ReactNode;
};

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);

  // Check if user is authenticated on load
  useEffect(() => {
    const initAuth = async () => {
      setLoading(true);
      try {
        const isAuth = await authApi.isAuthenticated();
        setIsAuthenticated(isAuth);
        
        if (isAuth) {
          const userProfile = await authApi.getProfile();
          setUser(userProfile);
        }
      } catch (err) {
        console.error('Authentication error:', err);
        setError('Failed to initialize authentication');
        // Clear token if authentication fails
        await authApi.logout();
        setIsAuthenticated(false);
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  // Login function
  const login = async (email: string, password: string) => {
    setLoading(true);
    setError(null);
    try {
      await authApi.login(email, password);
      setIsAuthenticated(true);
      const userProfile = await authApi.getProfile();
      setUser(userProfile);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Register function
  const register = async (userData: {
    email: string;
    full_name?: string;
    password: string;
    notification_enabled?: boolean;
    urgency_threshold?: number;
  }) => {
    setLoading(true);
    setError(null);
    try {
      await authApi.register(userData);
      // Login after successful registration
      await login(userData.email, userData.password);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Logout function
  const logout = async () => {
    setLoading(true);
    try {
      await authApi.logout();
      setUser(null);
      setIsAuthenticated(false);
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      setLoading(false);
    }
  };

  const value = {
    user,
    loading,
    error,
    login,
    register,
    logout,
    isAuthenticated
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Custom hook to use auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};