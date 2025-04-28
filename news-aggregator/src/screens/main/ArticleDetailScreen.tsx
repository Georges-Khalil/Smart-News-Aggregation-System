import React, { useState, useEffect, useRef } from 'react';
import { 
  StyleSheet, 
  View, 
  ScrollView, 
  Text, 
  Image, 
  TouchableOpacity, 
  ActivityIndicator,
  Share,
  Animated,
  Linking
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Icon } from 'react-native-elements';
import dayjs from 'dayjs';
import { articlesApi } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../../App';

// Use React Navigation's type utility for screen props with our RootStackParamList
type ArticleDetailProps = NativeStackScreenProps<RootStackParamList, 'ArticleDetail'>;

const ArticleDetailScreen: React.FC<ArticleDetailProps> = ({ route, navigation }) => {
  const { articleId } = route.params;
  const { isAuthenticated } = useAuth();
  const [article, setArticle] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLiked, setIsLiked] = useState(false);
  const [readingStartTime, setReadingStartTime] = useState<number>(0);
  const scrollY = useRef(new Animated.Value(0)).current;
  const headerOpacity = scrollY.interpolate({
    inputRange: [0, 100],
    outputRange: [0, 1],
    extrapolate: 'clamp'
  });

  // Fetch article details
  useEffect(() => {
    const loadArticle = async () => {
      try {
        setLoading(true);
        setError(null);
        const articleData = await articlesApi.getArticleById(articleId);
        setArticle(articleData);
        
        // Start tracking reading time
        setReadingStartTime(Date.now());
      } catch (err) {
        console.error('Error loading article:', err);
        setError('Failed to load article. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    loadArticle();

    // Record reading time when unmounting
    return () => {
      if (isAuthenticated && readingStartTime > 0) {
        const readTimeSeconds = Math.round((Date.now() - readingStartTime) / 1000);
        
        // Only record if the user spent more than 5 seconds on the article
        if (readTimeSeconds > 5) {
          articlesApi.recordInteraction({
            article_id: articleId,
            read: true,
            read_time: readTimeSeconds
          }).catch(err => {
            console.error('Error recording read time:', err);
          });
        }
      }
    };
  }, [articleId, isAuthenticated]);

  // Handle like press
  const handleLikePress = async () => {
    if (!isAuthenticated) {
      navigation.navigate('Auth', { screen: 'Login' });
      return;
    }

    // Optimistic update
    setIsLiked(prev => !prev);
    
    try {
      await articlesApi.recordInteraction({
        article_id: articleId,
        liked: !isLiked
      });
    } catch (err) {
      console.error('Error recording like:', err);
      // Revert on failure
      setIsLiked(prev => !prev);
    }
  };

  // Share article
  const handleShare = async () => {
    if (!article) return;
    
    try {
      await Share.share({
        message: `Check out this article: ${article.title} ${article.link}`
      });
    } catch (err) {
      console.error('Error sharing article:', err);
    }
  };

  // Open original article link in browser
  const handleOpenSource = () => {
    if (article?.link) {
      Linking.openURL(article.link).catch(err => {
        console.error('Error opening link:', err);
      });
    }
  };

  // Loading state
  if (loading) {
    return (
      <SafeAreaView style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#2196F3" />
        <Text style={styles.loadingText}>Loading article...</Text>
      </SafeAreaView>
    );
  }

  // Error state
  if (error || !article) {
    return (
      <SafeAreaView style={styles.errorContainer}>
        <Icon name="error-outline" type="material" size={64} color="#D32F2F" />
        <Text style={styles.errorText}>{error || 'Article not found'}</Text>
        <TouchableOpacity
          style={styles.errorButton}
          onPress={() => navigation.goBack()}
        >
          <Text style={styles.errorButtonText}>Go Back</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  // Format date
  const formattedDate = dayjs(article.pub_date).format('MMMM D, YYYY');
  
  // Get urgency indicator color
  const getUrgencyColor = (score: number) => {
    if (score <= 3) return '#4CAF50'; // Green for low urgency
    if (score <= 6) return '#FFC107'; // Yellow for medium urgency
    return '#F44336'; // Red for high urgency
  };

  return (
    <SafeAreaView style={styles.container} edges={['bottom', 'left', 'right']}>
      {/* Animated header */}
      <Animated.View style={[
        styles.animatedHeader,
        { opacity: headerOpacity }
      ]}>
        <Text style={styles.headerTitle} numberOfLines={1}>
          {article.title}
        </Text>
      </Animated.View>
      
      {/* Static header */}
      <View style={styles.header}>
        <TouchableOpacity 
          style={styles.backButton}
          onPress={() => navigation.goBack()}
        >
          <Icon name="arrow-back" type="material" size={24} color="#212121" />
        </TouchableOpacity>
        
        <View style={styles.headerActions}>
          <TouchableOpacity 
            style={styles.headerButton}
            onPress={handleLikePress}
          >
            <Icon 
              name={isLiked ? 'heart' : 'heart-outline'} 
              type="material-community" 
              size={24} 
              color={isLiked ? '#F44336' : '#616161'} 
            />
          </TouchableOpacity>
          
          <TouchableOpacity 
            style={styles.headerButton}
            onPress={handleShare}
          >
            <Icon name="share" type="material" size={24} color="#616161" />
          </TouchableOpacity>
        </View>
      </View>
      
      <Animated.ScrollView 
        style={styles.scrollView}
        showsVerticalScrollIndicator={false}
        onScroll={Animated.event(
          [{ nativeEvent: { contentOffset: { y: scrollY } } }],
          { useNativeDriver: true }
        )}
        scrollEventThrottle={16}
      >
        {/* Article content */}
        <View style={styles.content}>
          {/* Title and metadata */}
          <Text style={styles.title}>{article.title}</Text>
          
          <View style={styles.metaContainer}>
            <View style={styles.sourceContainer}>
              <Text style={styles.source}>{article.source}</Text>
              <View 
                style={[
                  styles.urgencyIndicator, 
                  { backgroundColor: getUrgencyColor(article.urgency_score) }
                ]} 
              />
            </View>
            <Text style={styles.date}>{formattedDate}</Text>
          </View>
          
          {/* Featured image */}
          {article.image && (
            <Image
              source={{ uri: article.image }}
              style={styles.image}
              resizeMode="cover"
            />
          )}
          
          {/* Article body */}
          {article.description && (
            <Text style={styles.description}>{article.description}</Text>
          )}
          
          <Text style={styles.body}>{article.content}</Text>
          
          {/* Original source link */}
          <TouchableOpacity 
            style={styles.sourceLink}
            onPress={handleOpenSource}
          >
            <Text style={styles.sourceLinkText}>
              Read original article
            </Text>
            <Icon name="open-in-new" type="material" size={16} color="#2196F3" />
          </TouchableOpacity>
        </View>
      </Animated.ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#757575',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    padding: 24,
  },
  errorText: {
    marginTop: 16,
    fontSize: 16,
    color: '#757575',
    textAlign: 'center',
    marginBottom: 24,
  },
  errorButton: {
    backgroundColor: '#2196F3',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  errorButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  animatedHeader: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 56,
    backgroundColor: '#FFFFFF',
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 56,
    zIndex: 100,
    elevation: 2,
    shadowColor: '#000000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#212121',
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    height: 56,
    zIndex: 10,
  },
  backButton: {
    padding: 8,
  },
  headerActions: {
    flexDirection: 'row',
  },
  headerButton: {
    padding: 8,
    marginLeft: 8,
  },
  scrollView: {
    flex: 1,
  },
  content: {
    padding: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#212121',
    marginBottom: 16,
  },
  metaContainer: {
    marginBottom: 16,
  },
  sourceContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  source: {
    fontSize: 14,
    fontWeight: '600',
    color: '#616161',
  },
  urgencyIndicator: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginLeft: 8,
  },
  date: {
    fontSize: 14,
    color: '#9E9E9E',
  },
  image: {
    width: '100%',
    height: 200,
    borderRadius: 8,
    marginBottom: 16,
  },
  description: {
    fontSize: 16,
    fontWeight: '600',
    color: '#424242',
    marginBottom: 16,
    lineHeight: 24,
  },
  body: {
    fontSize: 16,
    color: '#212121',
    lineHeight: 24,
  },
  sourceLink: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 24,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#EEEEEE',
  },
  sourceLinkText: {
    fontSize: 14,
    color: '#2196F3',
    marginRight: 4,
  },
});

export default ArticleDetailScreen;