import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { StatusBar } from 'expo-status-bar';
import { Icon } from 'react-native-elements';
import { SafeAreaProvider } from 'react-native-safe-area-context';

// Auth screens
import LoginScreen from './src/screens/auth/LoginScreen';
import RegisterScreen from './src/screens/auth/RegisterScreen';

// Main screens
import HomeScreen from './src/screens/main/HomeScreen';
import SearchScreen from './src/screens/main/SearchScreen';
import ArticleDetailScreen from './src/screens/main/ArticleDetailScreen';
import ProfileScreen from './src/screens/main/ProfileScreen';

// Context
import { AuthProvider, useAuth } from './src/context/AuthContext';

// Define the type for the root stack param list
export type RootStackParamList = {
  Auth: { screen?: string };
  Main: undefined;
  ArticleDetail: { articleId: string };
};

// Define the type for the auth stack param list
export type AuthStackParamList = {
  Login: undefined;
  Register: undefined;
};

// Define the type for the main tab param list
export type MainTabParamList = {
  Home: undefined;
  Search: undefined;
  Profile: undefined;
};

// Create navigators with proper typing
const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator();

// Auth Navigator (Login/Register screens)
const AuthStack = createNativeStackNavigator<AuthStackParamList>();

const AuthNavigator = () => {
  return (
    <AuthStack.Navigator 
      screenOptions={{ 
        headerShown: false,
        contentStyle: { backgroundColor: '#FFFFFF' }
      }}
    >
      <AuthStack.Screen name="Login" component={LoginScreen} />
      <AuthStack.Screen name="Register" component={RegisterScreen} />
    </AuthStack.Navigator>
  );
};

// Main Tab Navigator (Home, Search, Profile)
const MainTab = createBottomTabNavigator<MainTabParamList>();

const MainNavigator = () => {
  return (
    <MainTab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: '#2196F3',
        tabBarInactiveTintColor: '#757575',
        tabBarStyle: {
          elevation: 4,
          shadowColor: '#000',
          shadowOffset: { width: 0, height: -2 },
          shadowOpacity: 0.1,
          shadowRadius: 4,
        },
        tabBarIcon: ({ color, size }) => {
          let iconName: string = 'home'; // Default value
          
          if (route.name === 'Home') {
            iconName = 'home';
          } else if (route.name === 'Search') {
            iconName = 'search';
          } else if (route.name === 'Profile') {
            iconName = 'person';
          }

          return <Icon name={iconName} type="material" size={size} color={color} />;
        },
      })}
    >
      <MainTab.Screen name="Home" component={HomeScreen} />
      <MainTab.Screen name="Search" component={SearchScreen} />
      <MainTab.Screen name="Profile" component={ProfileScreen} />
    </MainTab.Navigator>
  );
};

// Main stack with nested navigators
const MainStackNavigator = () => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    // You could add a splash screen here
    return null;
  }

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {!isAuthenticated ? (
        <Stack.Screen name="Auth" component={AuthNavigator} />
      ) : (
        <>
          <Stack.Screen name="Main" component={MainNavigator} />
          <Stack.Screen 
            name="ArticleDetail" 
            component={ArticleDetailScreen}
            options={{
              headerShown: false, 
              presentation: 'fullScreenModal',
              animation: 'slide_from_right',
              contentStyle: { backgroundColor: '#FFFFFF' }
            }}
          />
        </>
      )}
    </Stack.Navigator>
  );
};

// Root component
export default function App() {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <NavigationContainer>
          <MainStackNavigator />
          <StatusBar style="auto" />
        </NavigationContainer>
      </AuthProvider>
    </SafeAreaProvider>
  );
}
