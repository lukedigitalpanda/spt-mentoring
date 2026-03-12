import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';
import { View, Text } from 'react-native';
import { useQuery } from '@tanstack/react-query';

import HomeScreen from '../screens/HomeScreen';
import SessionsScreen from '../screens/SessionsScreen';
import MessagesScreen from '../screens/MessagesScreen';
import NotificationsScreen from '../screens/NotificationsScreen';
import ProfileScreen from '../screens/ProfileScreen';
import api from '../hooks/api';

export type MainTabParamList = {
  Home: undefined;
  Sessions: undefined;
  Messages: undefined;
  Notifications: undefined;
  Profile: undefined;
};

const Tab = createBottomTabNavigator<MainTabParamList>();

function NotifBadge() {
  const { data } = useQuery<{ count: number }>({
    queryKey: ['notif-count'],
    queryFn: () => api.get('/notifications/unread_count/').then(r => r.data),
    refetchInterval: 30_000,
  });
  const count = data?.count ?? 0;
  if (!count) return null;
  return (
    <View style={{
      position: 'absolute', top: -4, right: -8,
      backgroundColor: '#ec4899', borderRadius: 8,
      minWidth: 16, height: 16, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 3,
    }}>
      <Text style={{ color: '#fff', fontSize: 9, fontWeight: '700' }}>{count > 9 ? '9+' : count}</Text>
    </View>
  );
}

export default function MainNavigator() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerStyle: { backgroundColor: '#fff' },
        headerTintColor: '#1e1b4b',
        headerTitleStyle: { fontWeight: '700' },
        tabBarActiveTintColor: '#9333ea',
        tabBarInactiveTintColor: '#94a3b8',
        tabBarStyle: {
          borderTopColor: '#f3e8ff',
          backgroundColor: '#fff',
          paddingBottom: 4,
          height: 60,
        },
        tabBarIcon: ({ focused, color, size }) => {
          const icons: Record<string, [string, string]> = {
            Home:          ['home',          'home-outline'],
            Sessions:      ['calendar',      'calendar-outline'],
            Messages:      ['chatbubbles',   'chatbubbles-outline'],
            Notifications: ['notifications', 'notifications-outline'],
            Profile:       ['person',        'person-outline'],
          };
          const [filled, outline] = icons[route.name] || ['ellipse', 'ellipse-outline'];
          const iconName = (focused ? filled : outline) as any;
          return (
            <View>
              <Ionicons name={iconName} size={size} color={color} />
              {route.name === 'Notifications' && <NotifBadge />}
            </View>
          );
        },
      })}
    >
      <Tab.Screen name="Home" component={HomeScreen} options={{ title: 'Home' }} />
      <Tab.Screen name="Sessions" component={SessionsScreen} />
      <Tab.Screen name="Messages" component={MessagesScreen} />
      <Tab.Screen name="Notifications" component={NotificationsScreen} />
      <Tab.Screen name="Profile" component={ProfileScreen} />
    </Tab.Navigator>
  );
}
