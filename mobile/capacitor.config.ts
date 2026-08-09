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
      backgroundColor: '#ffffff', // white to match the Arkwright mark on the splash/icon
      showSpinner: false,
    },
  },
};

export default config;
