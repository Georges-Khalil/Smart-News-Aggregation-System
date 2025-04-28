import React, { useState, useEffect } from 'react';
import { 
  StyleSheet, 
  View, 
  FlatList, 
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

interface SearchScreenProps {
  navigation: any;
  route: {
    params?: {
      query?: string;
    }
  }
}

const SearchScreen = ({ navigation, route }: SearchScreenProps) => {
  const { isAuthenticated } = useAuth();
  const [articles, setArticles] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMorePages, setHasMorePages] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [initialQuery, setInitialQuery] = useState(route.params?.query || '');
  const [likedArticles, setLikedArticles] = useState<Record<string, boolean>>({});
  const [activeFilters, setActiveFilters] = useState({
    sources: [] as string[],
    minUrgency: 0,
    sortBy: 'relevance' as 'relevance' | 'recency' | 'urgency',
    personalized: isAuthenticated
  });

  // Search for articles
  const searchArticles = async (
    query: string, 
    pageNum = 1, 
    refresh = false,
    filters = activeFilters
  ) => {
    if (!query.trim()) {
      setArticles([]);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      if (refresh) {
        setArticles([]);
        setPage(1);
        setHasMorePages(true);
        pageNum = 1;
      }

      const response = await articlesApi.searchArticles({
        query,
        page: pageNum,
        pageSize: 10,
        sources: filters.sources.length > 0 ? filters.sources : undefined,
        minUrgency: filters.minUrgency > 0 ? filters.minUrgency : undefined,
        sortBy: filters.sortBy,
        personalized: filters.personalized && isAuthenticated
      });

      if (response.success) {
        const newArticles = response.data || [];
        setArticles(prev => refresh ? newArticles : [...prev, ...newArticles]);
        setHasMorePages(pageNum < response.total_pages);
        setPage(pageNum);
      } else {
        setError('Failed to search for articles');
      }
    } catch (err) {
      console.error('Error searching articles:', err);
      setError('Failed to search for articles. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Initial search if query was passed
  useEffect(() => {
    if (initialQuery) {
      searchArticles(initialQuery, 1, true);
    }
  }, [initialQuery]);

  // Handle search submit
  const handleSearch = (query: string) => {
    setInitialQuery(query);
    searchArticles(query, 1, true);
  };

  // Load more articles when reaching end of list
  const handleLoadMore = () => {
    if (!loading && hasMorePages) {
      searchArticles(initialQuery, page + 1);
    }
  };

  // Handle article press - navigate to detail and record 'read' interaction
  const handleArticlePress = async (articleId: string) => {
    if (isAuthenticated) {
      try {
        await articlesApi.recordInteraction({
          article_id: articleId,
          read: true
        });
      } catch (err) {
        console.error('Error recording read interaction:', err);
      }
    }
    
    navigation.navigate('ArticleDetail', { articleId });
  };

  // Handle like press - record 'like' interaction
  const handleLikePress = async (articleId: string, liked: boolean) => {
    if (!isAuthenticated) {
      navigation.navigate('Auth', { screen: 'Login' });
      return;
    }
    
    setLikedArticles(prev => ({
      ...prev,
      [articleId]: liked
    }));
    
    try {
      await articlesApi.recordInteraction({
        article_id: articleId,
        liked
      });
    } catch (err) {
      console.error('Error recording like interaction:', err);
      setLikedArticles(prev => ({
        ...prev,
        [articleId]: !liked
      }));
    }
  };

  // Handle filter changes
  const applyFilters = (filters: typeof activeFilters) => {
    setActiveFilters(filters);
    searchArticles(initialQuery, 1, true, filters);
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity 
          style={styles.backButton}
          onPress={() => navigation.goBack()}
        >
          <Icon name="arrow-back" type="material" size={24} color="#212121" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Search</Text>
      </View>

      <SearchBar 
        onSearch={handleSearch}
        placeholder="Search for news articles..."
      />

      {/* Filter Button - Could be expanded to a full filter UI */}
      <View style={styles.filterContainer}>
        <TouchableOpacity 
          style={styles.filterButton}
          onPress={() => {
            // In a full app, this would open a modal/screen with filter options
            alert('Filter functionality would be implemented here');
          }}
        >
          <Icon name="filter-list" type="material" size={18} color="#757575" />
          <Text style={styles.filterText}>Filter</Text>
        </TouchableOpacity>
        
        {activeFilters.personalized && isAuthenticated && (
          <View style={styles.filterChip}>
            <Text style={styles.filterChipText}>Personalized</Text>
          </View>
        )}
        
        {activeFilters.sortBy !== 'relevance' && (
          <View style={styles.filterChip}>
            <Text style={styles.filterChipText}>
              Sort: {activeFilters.sortBy.charAt(0).toUpperCase() + activeFilters.sortBy.slice(1)}
            </Text>
          </View>
        )}
      </View>

      {error && (
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      )}

      {loading && articles.length === 0 ? (
        <View style={styles.loaderContainer}>
          <ActivityIndicator size="large" color="#2196F3" />
        </View>
      ) : (
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
          onEndReached={handleLoadMore}
          onEndReachedThreshold={0.5}
          ListFooterComponent={loading ? (
            <View style={styles.loaderContainer}>
              <ActivityIndicator size="small" color="#2196F3" />
            </View>
          ) : null}
          ListEmptyComponent={!loading && initialQuery ? (
            <View style={styles.emptyContainer}>
              <Icon
                name="search-off"
                type="material"
                size={64}
                color="#BDBDBD"
              />
              <Text style={styles.emptyText}>No results found for "{initialQuery}"</Text>
            </View>
          ) : !initialQuery ? (
            <View style={styles.emptyContainer}>
              <Icon
                name="search"
                type="material"
                size={64}
                color="#BDBDBD"
              />
              <Text style={styles.emptyText}>Search for news articles</Text>
            </View>
          ) : null}
        />
      )}
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
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#fff',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
  },
  backButton: {
    marginRight: 16,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#212121',
  },
  filterContainer: {
    flexDirection: 'row',
    padding: 8,
    paddingHorizontal: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#EEEEEE',
  },
  filterButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F5F5F5',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    marginRight: 8,
  },
  filterText: {
    marginLeft: 4,
    fontSize: 14,
    color: '#757575',
  },
  filterChip: {
    backgroundColor: '#E3F2FD',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    marginRight: 8,
  },
  filterChipText: {
    fontSize: 14,
    color: '#2196F3',
  },
  loaderContainer: {
    flex: 1,
    paddingVertical: 20,
    justifyContent: 'center',
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
    textAlign: 'center',
  },
  errorContainer: {
    margin: 16,
    padding: 12,
    backgroundColor: '#FFEBEE',
    borderRadius: 8,
  },
  errorText: {
    color: '#D32F2F',
    textAlign: 'center',
  },
});

export default SearchScreen;