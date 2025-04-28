import React, { useState, useEffect } from 'react';
import { 
  StyleSheet, 
  View, 
  Text, 
  TouchableOpacity, 
  Switch, 
  ScrollView, 
  ActivityIndicator,
  Alert,
  TextInput
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Icon } from 'react-native-elements';
import { useAuth } from '../../context/AuthContext';
import { authApi } from '../../services/api';

const ProfileScreen = () => {
  const { user, logout, loading: authLoading } = useAuth();
  const [loading, setLoading] = useState(false);
  const [notificationsEnabled, setNotificationsEnabled] = useState(
    user?.notification_enabled || false
  );
  const [urgencyThreshold, setUrgencyThreshold] = useState(
    user?.urgency_threshold?.toString() || '7'
  );
  
  // Set initial values when user data loads
  useEffect(() => {
    if (user) {
      setNotificationsEnabled(user.notification_enabled);
      setUrgencyThreshold(user.urgency_threshold?.toString() || '7');
    }
  }, [user]);

  const handleLogout = async () => {
    try {
      setLoading(true);
      await logout();
    } catch (error) {
      console.error('Error logging out:', error);
    } finally {
      setLoading(false);
    }
  };

  // For a full implementation, this would call an API to update user preferences
  // We'll just show an alert for now
  const handleSavePreferences = () => {
    Alert.alert(
      "Save Preferences",
      "In a full implementation, this would update your preferences in the backend.",
      [
        { text: "OK", onPress: () => console.log("OK Pressed") }
      ]
    );
  };

  if (authLoading) {
    return (
      <SafeAreaView style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#2196F3" />
        <Text style={styles.loadingText}>Loading profile...</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>My Profile</Text>
      </View>

      <ScrollView style={styles.content}>
        {/* User info section */}
        <View style={styles.userSection}>
          <View style={styles.avatarContainer}>
            <Icon
              name="account-circle"
              type="material-community"
              size={80}
              color="#2196F3"
            />
          </View>
          <Text style={styles.userName}>{user?.full_name || 'User'}</Text>
          <Text style={styles.userEmail}>{user?.email}</Text>
        </View>

        {/* Preferences section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Preferences</Text>
          
          <View style={styles.preferenceItem}>
            <Text style={styles.preferenceLabel}>Notifications</Text>
            <Switch
              value={notificationsEnabled}
              onValueChange={setNotificationsEnabled}
              trackColor={{ false: '#E0E0E0', true: '#BBDEFB' }}
              thumbColor={notificationsEnabled ? '#2196F3' : '#BDBDBD'}
            />
          </View>
          
          <View style={styles.preferenceItem}>
            <Text style={styles.preferenceLabel}>Urgency Threshold</Text>
            <View style={styles.urgencyInputContainer}>
              <TextInput
                style={styles.urgencyInput}
                value={urgencyThreshold}
                onChangeText={(value) => {
                  // Only allow values 1-10
                  const num = parseInt(value);
                  if (!isNaN(num) && num >= 1 && num <= 10) {
                    setUrgencyThreshold(value);
                  } else if (value === '') {
                    setUrgencyThreshold('');
                  }
                }}
                keyboardType="number-pad"
                maxLength={2}
              />
              <Text style={styles.urgencyLabel}>(1-10)</Text>
            </View>
          </View>
          
          <TouchableOpacity
            style={styles.saveButton}
            onPress={handleSavePreferences}
          >
            <Text style={styles.saveButtonText}>Save Preferences</Text>
          </TouchableOpacity>
        </View>

        {/* Account section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Account</Text>
          
          <TouchableOpacity style={styles.menuItem}>
            <Icon name="key" type="font-awesome" size={20} color="#616161" />
            <Text style={styles.menuItemText}>Change Password</Text>
            <Icon name="chevron-right" type="font-awesome" size={16} color="#BDBDBD" />
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.menuItem}>
            <Icon name="notifications" type="material" size={20} color="#616161" />
            <Text style={styles.menuItemText}>Notification Settings</Text>
            <Icon name="chevron-right" type="font-awesome" size={16} color="#BDBDBD" />
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.menuItem}>
            <Icon name="info-circle" type="font-awesome" size={20} color="#616161" />
            <Text style={styles.menuItemText}>About</Text>
            <Icon name="chevron-right" type="font-awesome" size={16} color="#BDBDBD" />
          </TouchableOpacity>
        </View>
        
        {/* Logout button */}
        <TouchableOpacity
          style={styles.logoutButton}
          onPress={handleLogout}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <>
              <Icon name="logout" type="material" size={20} color="#fff" />
              <Text style={styles.logoutText}>Logout</Text>
            </>
          )}
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FAFAFA',
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
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
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
  content: {
    flex: 1,
  },
  userSection: {
    backgroundColor: '#fff',
    paddingVertical: 24,
    alignItems: 'center',
    marginBottom: 16,
  },
  avatarContainer: {
    marginBottom: 16,
  },
  userName: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#212121',
    marginBottom: 4,
  },
  userEmail: {
    fontSize: 16,
    color: '#757575',
  },
  section: {
    backgroundColor: '#fff',
    padding: 16,
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#212121',
    marginBottom: 16,
  },
  preferenceItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F5F5F5',
  },
  preferenceLabel: {
    fontSize: 16,
    color: '#424242',
  },
  urgencyInputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  urgencyInput: {
    backgroundColor: '#F5F5F5',
    borderRadius: 4,
    paddingHorizontal: 12,
    paddingVertical: 8,
    width: 50,
    textAlign: 'center',
    fontSize: 16,
    color: '#212121',
  },
  urgencyLabel: {
    marginLeft: 8,
    fontSize: 14,
    color: '#757575',
  },
  saveButton: {
    backgroundColor: '#2196F3',
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: 'center',
    marginTop: 16,
  },
  saveButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#F5F5F5',
  },
  menuItemText: {
    flex: 1,
    fontSize: 16,
    color: '#424242',
    marginLeft: 16,
  },
  logoutButton: {
    backgroundColor: '#F44336',
    borderRadius: 8,
    paddingVertical: 12,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginHorizontal: 16,
    marginTop: 24,
    marginBottom: 40,
  },
  logoutText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
});

export default ProfileScreen;