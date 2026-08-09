import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'org.spt.mentoring',
  appName: 'SPT Mentoring',
  webDir: '../frontend/dist',
  server: {
    androidScheme: 'https', // bundled origin becomes https://localhost on Android
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 1200,
      backgroundColor: '#6b21a8',
      showSpinner: false,
    },
  },
};

export default config;
