import React, { useState, useEffect } from 'react';
import { 
  StyleSheet, 
  View, 
  FlatList, 
  ActivityIndicator, 
  Text, 
  TouchableOpacity,
  Modal,
  ScrollView
} from 'react-native';
import Slider from '@react-native-community/slider';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Icon } from 'react-native-elements';
import ArticleCard from '../../components/ArticleCard';
import SearchBar from '../../components/SearchBar';
import { articlesApi } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

// Define common news sources
const NEWS_SOURCES = [
  "CNN", 
  "BBC", 
  "Al Jazeera", 
  "The Guardian", 
  "FOX News", 
  "LBC", 
  "New York Times"
];

// Urgency levels
const URGENCY_LEVELS = [
  { label: 'Low', value: 'low', minScore: 1, maxScore: 4, color: '#4CAF50' },
  { label: 'Medium', value: 'medium', minScore: 5, maxScore: 8, color: '#FFC107' },
  { label: 'Breaking', value: 'breaking', minScore: 9, maxScore: 10, color: '#F44336' },
];

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
    urgencyLevel: '' as '' | 'low' | 'medium' | 'breaking',
    sortBy: 'relevance' as 'relevance' | 'recency' | 'urgency'
  });
  const [sortModalVisible, setSortModalVisible] = useState(false);
  const [filterModalVisible, setFilterModalVisible] = useState(false);
  const [tempFilters, setTempFilters] = useState({
    sources: [] as string[],
    urgencyLevel: '' as '' | 'low' | 'medium' | 'breaking'
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

      // Determine minimum urgency based on selected urgency level
      let minUrgency: number | undefined;
      
      if (filters.urgencyLevel) {
        const urgencyLevel = URGENCY_LEVELS.find(level => level.value === filters.urgencyLevel);
        if (urgencyLevel) {
          minUrgency = urgencyLevel.minScore;
        }
      }

      const response = await articlesApi.searchArticles({
        query,
        page: pageNum,
        pageSize: 10,
        sources: filters.sources.length > 0 ? filters.sources : undefined,
        minUrgency,
        sortBy: filters.sortBy
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

  // Initialize temporary filters when filter modal opens
  useEffect(() => {
    if (filterModalVisible) {
      setTempFilters({
        sources: [...activeFilters.sources],
        urgencyLevel: activeFilters.urgencyLevel
      });
    }
  }, [filterModalVisible]);

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

  // Handle sorting selection
  const handleSortSelect = (sortBy: 'relevance' | 'recency' | 'urgency') => {
    setActiveFilters(prev => ({
      ...prev,
      sortBy
    }));
    setSortModalVisible(false);
    
    // Re-search with new sorting option
    if (initialQuery) {
      searchArticles(initialQuery, 1, true, {
        ...activeFilters,
        sortBy
      });
    }
  };

  // Handle source toggle in filter modal
  const handleSourceToggle = (source: string) => {
    setTempFilters(prev => {
      const newSources = [...prev.sources];
      const index = newSources.indexOf(source);
      
      if (index === -1) {
        newSources.push(source);
      } else {
        newSources.splice(index, 1);
      }
      
      return {
        ...prev,
        sources: newSources
      };
    });
  };

  // Handle apply filters
  const handleApplyFilters = () => {
    setActiveFilters(prev => ({
      ...prev,
      sources: tempFilters.sources,
      urgencyLevel: tempFilters.urgencyLevel as '' | 'low' | 'medium' | 'breaking'
    }));
    setFilterModalVisible(false);
    
    // Re-search with new filters
    if (initialQuery) {
      searchArticles(initialQuery, 1, true, {
        ...activeFilters,
        sources: tempFilters.sources,
        urgencyLevel: tempFilters.urgencyLevel as '' | 'low' | 'medium' | 'breaking'
      });
    }
  };

  // Handle reset filters
  const handleResetFilters = () => {
    setTempFilters({
      sources: [],
      urgencyLevel: ''
    });
  };

  // Handle removing a source filter chip
  const handleRemoveSourceFilter = (source: string) => {
    setActiveFilters(prev => {
      const newSources = prev.sources.filter(s => s !== source);
      const newFilters = {
        ...prev,
        sources: newSources
      };
      
      // Re-search with the updated filters
      if (initialQuery) {
        searchArticles(initialQuery, 1, true, newFilters);
      }
      
      return newFilters;
    });
  };

  // Handle clearing urgency filter
  const handleClearUrgencyFilter = () => {
    setActiveFilters(prev => {
      const newFilters = {
        ...prev,
        urgencyLevel: '' as '' | 'low' | 'medium' | 'breaking'
      };
      
      // Re-search with the updated filters
      if (initialQuery) {
        searchArticles(initialQuery, 1, true, newFilters);
      }
      
      return newFilters;
    });
  };

  // Check if any filters are active
  const hasActiveFilters = activeFilters.sources.length > 0 || activeFilters.urgencyLevel !== '';

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

      {/* Filter and Sort Buttons */}
      <View style={styles.filterContainer}>
        <TouchableOpacity 
          style={[
            styles.filterButton,
            hasActiveFilters && styles.activeFilterButton
          ]}
          onPress={() => setFilterModalVisible(true)}
        >
          <Icon 
            name="filter-list" 
            type="material" 
            size={18} 
            color={hasActiveFilters ? "#2196F3" : "#757575"} 
          />
          <Text 
            style={[
              styles.filterText,
              hasActiveFilters && styles.activeFilterText
            ]}
          >
            Filter
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity 
          style={styles.filterButton}
          onPress={() => setSortModalVisible(true)}
        >
          <Icon name="sort" type="material" size={18} color="#757575" />
          <Text style={styles.filterText}>Sort</Text>
        </TouchableOpacity>
        
        {activeFilters.sortBy !== 'relevance' && (
          <View style={styles.filterChip}>
            <Text style={styles.filterChipText}>
              Sort: {activeFilters.sortBy.charAt(0).toUpperCase() + activeFilters.sortBy.slice(1)}
            </Text>
          </View>
        )}
      </View>

      {/* Active Filters Container - Only rendered when there are active filters */}
      {hasActiveFilters && (
        <View style={styles.activeFiltersContainer}>
          <ScrollView 
            horizontal 
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.activeFiltersContent}
          >
            {activeFilters.sources.map(source => (
              <TouchableOpacity 
                key={source} 
                style={styles.activeFilterChip}
                onPress={() => handleRemoveSourceFilter(source)}
              >
                <Text 
                  style={styles.activeFilterChipText}
                  numberOfLines={1}
                  ellipsizeMode="tail"
                >
                  {source}
                </Text>
                <Icon name="close" type="material" size={16} color="#2196F3" />
              </TouchableOpacity>
            ))}
            
            {activeFilters.urgencyLevel && (
              <TouchableOpacity 
                style={styles.activeFilterChip}
                onPress={handleClearUrgencyFilter}
              >
                <Text 
                  style={styles.activeFilterChipText}
                  numberOfLines={1}
                  ellipsizeMode="tail"
                >
                  Urgency: {activeFilters.urgencyLevel.charAt(0).toUpperCase() + activeFilters.urgencyLevel.slice(1)}
                </Text>
                <Icon name="close" type="material" size={16} color="#2196F3" />
              </TouchableOpacity>
            )}
          </ScrollView>
        </View>
      )}

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
          keyExtractor={(item, index) => `search-article-${item.id}-${index}`}
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

      {/* Sorting modal */}
      <Modal
        visible={sortModalVisible}
        transparent={true}
        animationType="fade"
        onRequestClose={() => setSortModalVisible(false)}
      >
        <TouchableOpacity 
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setSortModalVisible(false)}
        >
          <View style={styles.sortModalContainer}>
            <View style={styles.sortModal}>
              <Text style={styles.sortModalTitle}>Sort By</Text>
              
              <TouchableOpacity 
                style={styles.sortOption}
                onPress={() => handleSortSelect('relevance')}
              >
                <Text style={styles.sortOptionText}>Relevance</Text>
                {activeFilters.sortBy === 'relevance' && (
                  <Icon name="check" type="material" size={20} color="#2196F3" />
                )}
              </TouchableOpacity>
              
              <TouchableOpacity 
                style={styles.sortOption}
                onPress={() => handleSortSelect('recency')}
              >
                <Text style={styles.sortOptionText}>Recency</Text>
                {activeFilters.sortBy === 'recency' && (
                  <Icon name="check" type="material" size={20} color="#2196F3" />
                )}
              </TouchableOpacity>
              
              <TouchableOpacity 
                style={styles.sortOption}
                onPress={() => handleSortSelect('urgency')}
              >
                <Text style={styles.sortOptionText}>Urgency</Text>
                {activeFilters.sortBy === 'urgency' && (
                  <Icon name="check" type="material" size={20} color="#2196F3" />
                )}
              </TouchableOpacity>
            </View>
          </View>
        </TouchableOpacity>
      </Modal>

      {/* Filter modal */}
      <Modal
        visible={filterModalVisible}
        transparent={true}
        animationType="slide"
        onRequestClose={() => setFilterModalVisible(false)}
      >
        <View style={styles.filterModalContainer}>
          <View style={styles.filterModal}>
            <View style={styles.filterModalHeader}>
              <TouchableOpacity 
                onPress={() => setFilterModalVisible(false)}
                hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
              >
                <Icon name="close" type="material" size={24} color="#616161" />
              </TouchableOpacity>
              <Text style={styles.filterModalTitle}>Filters</Text>
              <TouchableOpacity 
                onPress={handleResetFilters}
                hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
              >
                <Text style={styles.resetText}>Reset</Text>
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.filterModalContent}>
              {/* Sources section */}
              <View style={styles.filterSection}>
                <Text style={styles.filterSectionTitle}>Sources</Text>
                {NEWS_SOURCES.map(source => (
                  <TouchableOpacity 
                    key={source}
                    style={styles.sourceItem}
                    onPress={() => handleSourceToggle(source)}
                  >
                    <Text style={styles.sourceItemText}>{source}</Text>
                    <View style={[
                      styles.checkbox,
                      tempFilters.sources.includes(source) && styles.checkboxSelected
                    ]}>
                      {tempFilters.sources.includes(source) && (
                        <Icon name="check" type="material" size={16} color="#FFFFFF" />
                      )}
                    </View>
                  </TouchableOpacity>
                ))}
              </View>

              {/* Urgency section */}
              <View style={styles.filterSection}>
                <Text style={styles.filterSectionTitle}>Minimum Urgency Level</Text>
                {URGENCY_LEVELS.map(level => (
                  <TouchableOpacity 
                    key={level.value}
                    style={styles.sourceItem}
                    onPress={() => setTempFilters(prev => ({...prev, urgencyLevel: level.value as '' | 'low' | 'medium' | 'breaking'}))}
                  >
                    <Text style={styles.sourceItemText}>{level.label}</Text>
                    <View style={[
                      styles.checkbox,
                      tempFilters.urgencyLevel === level.value && styles.checkboxSelected
                    ]}>
                      {tempFilters.urgencyLevel === level.value && (
                        <Icon name="check" type="material" size={16} color="#FFFFFF" />
                      )}
                    </View>
                  </TouchableOpacity>
                ))}
              </View>
            </ScrollView>

            <TouchableOpacity 
              style={styles.applyButton}
              onPress={handleApplyFilters}
            >
              <Text style={styles.applyButtonText}>Apply Filters</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
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
  activeFilterButton: {
    backgroundColor: '#E3F2FD',
  },
  filterText: {
    marginLeft: 4,
    fontSize: 14,
    color: '#757575',
  },
  activeFilterText: {
    color: '#2196F3',
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
  activeFiltersContainer: {
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#EEEEEE',
    height: 52, // Fixed height for container to ensure consistent UI
    overflow: 'hidden', // Prevent container from expanding
  },
  activeFiltersContent: {
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  activeFilterChip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#E3F2FD',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    marginRight: 8,
  },
  activeFilterChipText: {
    fontSize: 14,
    color: '#2196F3',
    marginRight: 4,
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
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  sortModalContainer: {
    width: '80%',
    alignItems: 'center',
    justifyContent: 'center',
  },
  sortModal: {
    backgroundColor: 'white',
    borderRadius: 10,
    padding: 20,
    width: '100%',
  },
  sortModalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 15,
    color: '#212121',
    textAlign: 'center',
  },
  sortOption: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  sortOptionText: {
    fontSize: 16,
    color: '#424242',
  },
  filterModalContainer: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  filterModal: {
    backgroundColor: 'white',
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    height: '70%',
  },
  filterModalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#EEEEEE',
  },
  filterModalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#212121',
  },
  resetText: {
    fontSize: 14,
    color: '#2196F3',
  },
  filterModalContent: {
    flex: 1,
  },
  filterSection: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#EEEEEE',
  },
  filterSectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#212121',
    marginBottom: 12,
  },
  sourceItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F5F5F5',
  },
  sourceItemText: {
    fontSize: 16,
    color: '#424242',
  },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 4,
    borderWidth: 2,
    borderColor: '#BDBDBD',
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkboxSelected: {
    backgroundColor: '#2196F3',
    borderColor: '#2196F3',
  },
  sliderContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 12,
  },
  slider: {
    flex: 1,
    height: 40,
    marginHorizontal: 8,
  },
  sliderLabel: {
    fontSize: 14,
    color: '#757575',
    width: 20,
    textAlign: 'center',
  },
  sliderHint: {
    fontSize: 14,
    color: '#757575',
    marginTop: 4,
  },
  applyButton: {
    backgroundColor: '#2196F3',
    padding: 16,
    alignItems: 'center',
  },
  applyButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
});

export default SearchScreen;