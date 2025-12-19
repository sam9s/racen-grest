# GRESTA Android App - Build Instructions

## Prerequisites
- **Android Studio** (latest version)
- **Node.js** (version 18 or higher)
- **npm** (comes with Node.js)

## Step-by-Step Build Guide

### Step 1: Download the Required Files
Download these files/folders from Replit:
- `android/` (the Android project folder)
- `package.json`
- `package-lock.json` 
- `capacitor.config.ts`
- `node_modules/` (IMPORTANT - this contains the Capacitor libraries)

**Easiest method**: Download the entire project as a ZIP from Replit.

### Step 2: Open in Android Studio
1. Open Android Studio
2. Click "Open" (not "New Project")
3. Navigate to the `android` folder inside your downloaded project
4. Select it and click OK

### Step 3: Wait for Gradle Sync
- Android Studio will automatically start syncing
- This may take a few minutes on first run
- If you see "Gradle sync failed", see Troubleshooting below

### Step 4: Build the APK
1. In Android Studio, go to: **Build → Build Bundle(s) / APK(s) → Build APK(s)**
2. Wait for the build to complete
3. Click "locate" in the notification to find your APK

The APK will be at: `android/app/build/outputs/apk/debug/app-debug.apk`

### Step 5: Install on Your Phone
1. Transfer the APK to your Android phone
2. Open it and tap "Install"
3. If prompted about unknown sources, enable it temporarily

---

## Troubleshooting

### "Gradle sync failed" or "Cannot find module"
If you only downloaded the `android/` folder without the other files:

1. Make sure you have the FULL project folder (not just android/)
2. Open a terminal in the project root folder
3. Run: `npm install`
4. Run: `npx cap sync android`
5. Then open the `android/` folder in Android Studio again

### "SDK location not found"
1. In Android Studio, go to File → Settings → Appearance & Behavior → System Settings → Android SDK
2. Note the SDK location
3. The `local.properties` file will be created automatically

---

## What This App Does
GRESTA is a mobile wrapper for the GREST e-commerce chatbot. It opens the web app (https://grest.in) inside a native Android container with:
- Splash screen with GREST branding
- Native app icon on home screen
- Full-screen experience
