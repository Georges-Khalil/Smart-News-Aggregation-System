import React, { useState, useEffect, useCallback } from 'react';
import { 
  StyleSheet, 
  View, 
  FlatList, 
  RefreshControl, 
  ActivityIndicator, 
  Text,
  TouchableOpacity 
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Icon } from 'react-native-elements';
import ArticleCard from '../../components/ArticleCard';
import SearchBar from '../../components/SearchBar';
import { articlesApi } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

const HomeScreen = ({ navigation }: any) => {
  const { isAuthenticated, user } = useAuth();
  const [articles, setArticles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMorePages, setHasMorePages] = useState(true);
  const [isPersonalized, setIsPersonalized] = useState(true);
  const [likedArticles, setLikedArticles] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);

  // Load articles based on personalization state
  const loadArticles = useCallback(async (pageNum = 1, refresh = false) => {
    if (refresh) {
      setArticles([]);
      setPage(1);
      setHasMorePages(true);
      pageNum = 1;
    }

    try {
      setError(null);
      const fetchFunction = isAuthenticated && isPersonalized ? 
        articlesApi.getPersonalizedFeed : 
        articlesApi.getRecent;
      
      const response = await fetchFunction(pageNum);
      
      if (response.success) {
        const newArticles = response.data || [];
        setArticles(prev => refresh ? newArticles : [...prev, ...newArticles]);
        setHasMorePages(pageNum < response.total_pages);
        setPage(pageNum);
      } else {
        setError('Failed to load articles');
      }
    } catch (err) {
      console.error('Error loading articles:', err);
      setError('Failed to load articles. Please try again.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [isAuthenticated, isPersonalized]);

  // Initial load
  useEffect(() => {
    loadArticles(1, true);
  }, [loadArticles, isPersonalized]);

  // Pull-to-refresh handler
  const handleRefresh = () => {
    setRefreshing(true);
    loadArticles(1, true);
  };

  // Load more articles when reaching end of list
  const handleLoadMore = () => {
    if (!loading && hasMorePages) {
      loadArticles(page + 1);
    }
  };

  // Handle article press - navigate to detail and record 'read' interaction
  const handleArticlePress = async (articleId: string) => {
    if (isAuthenticated) {
      try {
        // Record that the user has read this article
        await articlesApi.recordInteraction({
          article_id: articleId,
          read: true
        });
      } catch (err) {
        console.error('Error recording read interaction:', err);
      }
    }
    
    // Navigate to article detail
    navigation.navigate('ArticleDetail', { articleId });
  };

  // Handle like press - record 'like' interaction
  const handleLikePress = async (articleId: string, liked: boolean) => {
    if (!isAuthenticated) {
      // Prompt to login if not authenticated
      navigation.navigate('Auth', { screen: 'Login' });
      return;
    }
    
    // Update UI immediately
    setLikedArticles(prev => ({
      ...prev,
      [articleId]: liked
    }));
    
    try {
      // Record the interaction with the backend
      await articlesApi.recordInteraction({
        article_id: articleId,
        liked
      });
    } catch (err) {
      console.error('Error recording like interaction:', err);
      // Revert UI state if request fails
      setLikedArticles(prev => ({
        ...prev,
        [articleId]: !liked
      }));
    }
  };

  // Handle search button press
  const handleSearch = (query: string) => {
    navigation.navigate('Search', { query });
  };

  // Toggle between personalized and recent feeds
  const toggleFeedType = () => {
    setIsPersonalized(prev => !prev);
    setLoading(true);
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>News Feed</Text>
        {isAuthenticated && (
          <TouchableOpacity style={styles.feedToggle} onPress={toggleFeedType}>
            <Icon
              name={isPersonalized ? 'account-circle' : 'public'}
              type="material"
              size={22}
              color="#2196F3"
            />
            <Text style={styles.feedToggleText}>
              {isPersonalized ? 'Personalized' : 'Recent'}
            </Text>
          </TouchableOpacity>
        )}
      </View>

      <SearchBar onSearch={handleSearch} />

      {error && (
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity style={styles.retryButton} onPress={handleRefresh}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      )}

      <FlatList
        data={articles}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <ArticleCard
            id={item.id}
            title={item.title}
            description={item.description}
            source={item.source}
            pubDate={item.pub_date}
            image={item.image}
            urgencyScore={item.urgency_score}
            onPress={handleArticlePress}
            onLikePress={handleLikePress}
            isLiked={likedArticles[item.id] || false}
          />
        )}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            colors={['#2196F3']}
          />
        }
        onEndReached={handleLoadMore}
        onEndReachedThreshold={0.5}
        ListFooterComponent={loading && !refreshing ? (
          <View style={styles.loaderContainer}>
            <ActivityIndicator size="small" color="#2196F3" />
          </View>
        ) : null}
        ListEmptyComponent={!loading ? (
          <View style={styles.emptyContainer}>
            <Icon
              name="newspaper"
              type="material-community"
              size={64}
              color="#BDBDBD"
            />
            <Text style={styles.emptyText}>No articles available</Text>
          </View>
        ) : null}
      />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FAFAFA',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#fff',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#212121',
  },
  feedToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#E3F2FD',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  feedToggleText: {
    marginLeft: 4,
    fontSize: 14,
    color: '#2196F3',
    fontWeight: '500',
  },
  loaderContainer: {
    paddingVertical: 20,
    alignItems: 'center',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyText: {
    marginTop: 16,
    fontSize: 16,
    color: '#757575',
  },
  errorContainer: {
    margin: 16,
    padding: 12,
    backgroundColor: '#FFEBEE',
    borderRadius: 8,
    alignItems: 'center',
  },
  errorText: {
    color: '#D32F2F',
    marginBottom: 8,
  },
  retryButton: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    backgroundColor: '#D32F2F',
    borderRadius: 4,
  },
  retryText: {
    color: '#fff',
    fontWeight: '500',
  },
});

export default HomeScreen;