import React from 'react';
import { StyleSheet, View, Text, Image, TouchableOpacity, Dimensions } from 'react-native';
import { Icon } from 'react-native-elements';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

// Initialize dayjs with relative time plugin
dayjs.extend(relativeTime);

// Types
interface ArticleCardProps {
  id: string;
  title: string;
  description?: string;
  source: string;
  pubDate: string;
  image?: string;
  urgencyScore: number;
  onPress: (id: string) => void;
  onLikePress?: (id: string, liked: boolean) => void;
  isLiked?: boolean;
}

const ArticleCard: React.FC<ArticleCardProps> = ({
  id,
  title,
  description,
  source,
  pubDate,
  image,
  urgencyScore,
  onPress,
  onLikePress,
  isLiked = false
}) => {
  const getUrgencyColor = (score: number) => {
    // Scale from green to red based on urgency score (1-10)
    if (score <= 4) return '#4CAF50'; // Green for low urgency
    if (score <= 8) return '#FFC107'; // Yellow for medium urgency
    return '#F44336'; // Red for breaking news (9-10)
  };

  const getUrgencyLabel = (score: number) => {
    if (score <= 4) return 'Low';
    if (score <= 8) return 'Medium';
    return 'Breaking';
  };

  const getUrgencyIcon = (score: number) => {
    if (score <= 4) return "information-outline";
    if (score <= 8) return "clock-outline";
    return "alarm-light";
  };

  const timeAgo = dayjs(pubDate).fromNow();

  // Always show urgency indicator for all articles
  
  return (
    <View style={styles.cardWrapper}>
      <View style={styles.card}>
        <TouchableOpacity 
          activeOpacity={0.9}
          onPress={() => onPress(id)}
          style={styles.cardContent}
        >
          {/* Header with source and time */}
          <View style={styles.cardHeader}>
            <Text style={styles.source}>{source}</Text>
            <Text style={styles.time}>{timeAgo}</Text>
          </View>
          
          {/* Main content */}
          <View style={styles.mainContent}>
            {/* Article image */}
            {image && (
              <View style={styles.imageContainer}>
                <Image
                  source={{ uri: image }}
                  style={styles.image}
                  resizeMode="cover"
                />
              </View>
            )}
            
            {/* Article text */}
            <View style={styles.textContainer}>
              <Text style={styles.title} numberOfLines={2}>
                {title}
              </Text>
              {description && (
                <Text style={styles.description} numberOfLines={3}>
                  {description}
                </Text>
              )}
            </View>
          </View>
          
          {/* Footer with urgency indicator and like button */}
          <View style={styles.cardFooter}>
            {/* Urgency pill badge - now shown for all articles */}
            <View 
              style={[
                styles.urgencyPill, 
                { backgroundColor: getUrgencyColor(urgencyScore) }
              ]}
            >
              <Icon
                name={getUrgencyIcon(urgencyScore)}
                type="material-community"
                size={14}
                color="#FFFFFF"
                style={styles.urgencyIcon}
              />
              <Text style={styles.urgencyText}>
                {getUrgencyLabel(urgencyScore)}
              </Text>
            </View>
            
            {/* Like button */}
            {onLikePress && (
              <TouchableOpacity
                style={styles.likeButton}
                onPress={() => onLikePress(id, !isLiked)}
              >
                <Icon
                  name={isLiked ? 'heart' : 'heart-outline'}
                  type="material-community"
                  size={20}
                  color={isLiked ? '#F44336' : '#757575'}
                />
                <Text style={styles.likeText}>{isLiked ? 'Liked' : 'Like'}</Text>
              </TouchableOpacity>
            )}
          </View>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  cardWrapper: {
    marginVertical: 6,
  },
  card: {
    borderRadius: 12,
    marginHorizontal: 8,
    marginBottom: 6,
    padding: 0,
    elevation: 2,
    backgroundColor: '#FFFFFF',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  cardContent: {
    padding: 12,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  source: {
    fontSize: 13,
    fontWeight: '600',
    color: '#424242',
  },
  time: {
    fontSize: 12,
    color: '#757575',
    marginLeft: 'auto',
  },
  mainContent: {
    flexDirection: 'row',
  },
  imageContainer: {
    position: 'relative',
    marginRight: 12,
  },
  image: {
    width: 100,
    height: 100,
    borderRadius: 8,
  },
  textContainer: {
    flex: 1,
  },
  title: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#212121',
    marginBottom: 6,
  },
  description: {
    fontSize: 14,
    color: '#616161',
    lineHeight: 20,
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 12,
  },
  urgencyPill: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 16,
  },
  urgencyIcon: {
    marginRight: 4,
  },
  urgencyText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  likeButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 6,
    paddingHorizontal: 12,
  },
  likeText: {
    marginLeft: 4,
    fontSize: 12,
    color: '#757575',
  },
});

export default ArticleCard;