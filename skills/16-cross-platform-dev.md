# Cross-Platform Development — Comprehensive Skill Guide

## Table of Contents
1. Flutter (Widget Tree, State Management with Riverpod, Platform Channels, Custom Painters, Animations)
2. React Native (New Architecture, Fabric, TurboModules, Hermes)
3. Kotlin Multiplatform (Shared Logic, expect/actual, Compose Multiplatform)
4. Tauri (Rust Backend, Web Frontend, System APIs)
5. Electron (Main/Renderer Process, IPC, Native Modules)
6. Comparison: When to Use Which
7. Performance Benchmarks
8. Shared Code Strategies
9. Platform-Specific Customization

---

## 1. Flutter

### Widget Tree & Composition

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class UserProfileScreen extends ConsumerWidget {
  const UserProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final userAsync = ref.watch(userProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Profile'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () => context.push('/settings'),
          ),
        ],
      ),
      body: userAsync.when(
        data: (user) => RefreshIndicator(
          onRefresh: () => ref.refresh(userProvider.future),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _AvatarSection(user: user),
              const SizedBox(height: 16),
              _UserDetails(user: user),
              const SizedBox(height: 24),
              _StatsGrid(user: user),
              const SizedBox(height: 16),
              _RecentActivity(userId: user.id),
            ],
          ),
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => ErrorWidget(err.toString()),
      ),
    );
  }
}
```

### State Management with Riverpod

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'providers.g.dart';

// Simple provider (no disposal needed)
@riverpod
String greeting(GreetingRef ref) {
  return 'Hello, World!';
}

// Future provider (async data)
@riverpod
Future<List<User>> users(UsersRef ref) async {
  final api = ref.watch(apiClientProvider);
  return api.getUsers();
}

// Stream provider (real-time)
@riverpod
Stream<List<Message>> messages(MessagesRef ref, String chatId) {
  final repo = ref.watch(chatRepositoryProvider);
  return repo.observeMessages(chatId);
}

// StateNotifier provider (mutable state)
@riverpod
class CartNotifier extends _$CartNotifier {
  @override
  List<CartItem> build() => [];

  void addItem(CartItem item) {
    state = [...state, item];
  }

  void removeItem(String id) {
    state = state.where((item) => item.id != id).toList();
  }

  double get total => state.fold(0, (sum, item) => sum + item.price);
}

// Family provider (parameterized)
@riverpod
Future<User> user(UserRef ref, String userId) async {
  final api = ref.watch(apiClientProvider);
  return api.getUser(userId);
}
```

### Platform Channels

```dart
import 'package:flutter/services.dart';

class PlatformService {
  static const _channel = MethodChannel('com.example.app/native');

  Future<String?> getDeviceId() async {
    try {
      return await _channel.invokeMethod<String>('getDeviceId');
    } on PlatformException catch (e) {
      print("Failed to get device ID: '${e.message}'");
      return null;
    }
  }

  Future<bool> authenticateWithBiometrics() async {
    try {
      final result = await _channel.invokeMethod<bool>('authenticate');
      return result ?? false;
    } on PlatformException catch (e) {
      print("Biometric auth failed: ${e.message}");
      return false;
    }
  }

  // Event channel (streaming)
  static const _eventChannel = EventChannel('com.example.app/sensor');

  Stream<SensorEvent> sensorStream() {
    return _eventChannel
        .receiveBroadcastStream()
        .map((event) => SensorEvent.fromMap(event));
  }
}

// Android implementation (MainActivity.kt)
class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            "com.example.app/native"
        ).setMethodCallHandler { call, result ->
            when (call.method) {
                "getDeviceId" -> result.success(getDeviceId())
                "authenticate" -> {
                    authenticateWithBiometrics { success ->
                        result.success(success)
                    }
                }
                else -> result.notImplemented()
            }
        }
    }
}
```

### Custom Painters

```dart
class WaveProgressPainter extends CustomPainter {
  final double progress;
  final Color color;

  WaveProgressPainter({
    required this.progress,
    required this.color,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.fill;

    final path = Path();
    path.moveTo(0, size.height);

    for (double x = 0; x <= size.width; x++) {
      final waveHeight = sin((x / size.width * 2 * pi) + (progress * 2 * pi)) * 10;
      final y = size.height * (1 - progress) + waveHeight;
      path.lineTo(x, y);
    }

    path.lineTo(size.width, size.height);
    path.close();
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(WaveProgressPainter oldDelegate) =>
      oldDelegate.progress != progress || oldDelegate.color != color;
}
```

### Animations

```dart
// Implicit animations
AnimatedContainer(
  duration: const Duration(milliseconds: 300),
  curve: Curves.easeInOut,
  width: isExpanded ? 200 : 100,
  height: isExpanded ? 200 : 100,
  decoration: BoxDecoration(
    color: isExpanded ? Colors.blue : Colors.red,
    borderRadius: BorderRadius.circular(isExpanded ? 20 : 10),
  ),
)

// Explicit animation with controller
class _FadeInState extends State<FadeIn>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 500),
      vsync: this,
    );
    _animation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOut,
    );
    _controller.forward();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _animation,
      child: child,
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
}

// Hero animation (shared element)
Hero(
  tag: 'profile-${user.id}',
  child: CircleAvatar(
    radius: 50,
    backgroundImage: NetworkImage(user.avatarUrl),
  ),
)
```

---

## 2. React Native

### New Architecture Components

```typescript
// Fabric Component (New Architecture)
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

// Automatic batching, better interop
function UserCard({ user }: { user: User }) {
  return (
    <View style={styles.card}>
      <Image source={{ uri: user.avatar }} style={styles.avatar} />
      <View style={styles.info}>
        <Text style={styles.name}>{user.name}</Text>
        <Text style={styles.email}>{user.email}</Text>
      </View>
    </View>
  );
}

// TurboModule (native module, New Architecture)
import { TurboModuleRegistry, TurboModule } from 'react-native';

interface Spec extends TurboModule {
  readonly getConstants: () => {};

  doSomething(value: string): Promise<string>;
  doSomethingElse(value: number): number;
}

export default TurboModuleRegistry.getEnforcing<Spec>('NativeCalculator');
```

### Performance with Hermes

```javascript
// Hermes engine configuration
// react-native.config.js
module.exports = {
  hermes: {
    // Enable Hermes (on by default in RN 0.70+)
    enabled: true,
    // Enable debugger
    // debug: true,
  },
};

// Optimized list rendering
import { FlashList } from '@shopify/flash-list';

function UserList({ users }) {
  return (
    <FlashList
      data={users}
      renderItem={({ item }) => <UserCard user={item} />}
      estimatedItemSize={80}
      keyExtractor={(item) => item.id}
      // New Arch enables automatic optimization
    />
  );
}
```

### State Management

```typescript
// Zustand (lightweight)
import { create } from 'zustand';

interface AuthState {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  login: async (email, password) => {
    const response = await api.login(email, password);
    set({ user: response.user, token: response.token });
  },
  logout: () => set({ user: null, token: null }),
}));

// TanStack Query (server state)
import { useQuery, useMutation } from '@tanstack/react-query';

function usePosts() {
  return useQuery({
    queryKey: ['posts'],
    queryFn: () => fetch('/api/posts').then(r => r.json()),
  });
}

function useCreatePost() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (post) => fetch('/api/posts', {
      method: 'POST',
      body: JSON.stringify(post),
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['posts'] });
    },
  });
}
```

---

## 3. Kotlin Multiplatform

### Shared Logic

```kotlin
// shared/src/commonMain/kotlin/com/app/domain/UserRepository.kt
class UserRepository(private val api: ApiClient) {
    suspend fun getUser(id: String): Result<User> {
        return try {
            Result.success(api.fetchUser(id))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}

// shared/src/commonMain/kotlin/com/app/domain/User.kt
data class User(
    val id: String,
    val name: String,
    val email: String,
)
```

### expect/actual

```kotlin
// shared/src/commonMain/kotlin/com/app/platform/Platform.kt
expect fun getPlatformName(): String
expect fun currentTimeMillis(): Long
expect class UUID {
    companion object {
        fun random(): UUID
    }
}

// shared/src/androidMain/kotlin/com/app/platform/Platform.android.kt
actual fun getPlatformName(): String = "Android ${Build.VERSION.SDK_INT}"
actual fun currentTimeMillis(): Long = System.currentTimeMillis()
actual class UUID actual constructor(private val uuid: java.util.UUID) {
    actual companion object {
        actual fun random(): UUID = UUID(java.util.UUID.randomUUID())
    }
}

// shared/src/iosMain/kotlin/com/app/platform/Platform.ios.kt
actual fun getPlatformName(): String = "iOS ${UIDevice.currentDevice.systemVersion}"
actual fun currentTimeMillis(): Long = (NSDate().timeIntervalSince1970 * 1000).toLong()
actual class UUID actual constructor(private val uuid: NSUUID) {
    actual companion object {
        actual fun random(): UUID = UUID(NSUUID())
    }
}
```

### Compose Multiplatform

```kotlin
// shared/src/commonMain/kotlin/com/app/ui/App.kt
@Composable
fun App() {
    var count by remember { mutableStateOf(0) }

    MaterialTheme {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
            modifier = Modifier.fillMaxSize(),
        ) {
            Text(
                text = "Platform: ${getPlatformName()}",
                style = MaterialTheme.typography.headlineMedium,
            )
            Text(
                text = "Count: $count",
                style = MaterialTheme.typography.displayLarge,
                modifier = Modifier.padding(16.dp),
            )
            Button(onClick = { count++ }) {
                Text("Increment")
            }
        }
    }
}
```

---

## 4. Tauri

### Rust Backend

```rust
// src-tauri/src/main.rs
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
struct Task {
    id: String,
    title: String,
    completed: bool,
}

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! From Rust!", name)
}

#[tauri::command]
fn get_tasks() -> Vec<Task> {
    vec![
        Task { id: "1".into(), title: "Learn Tauri".into(), completed: true },
        Task { id: "2".into(), title: "Build app".into(), completed: false },
    ]
}

#[tauri::command]
fn save_file(path: String, content: String) -> Result<(), String> {
    std::fs::write(&path, &content).map_err(|e| e.to_string())
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![greet, get_tasks, save_file])
        .setup(|app| {
            // System tray
            let tray = tauri::TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .menu(
                    tauri::menu::MenuBuilder::new(app)
                        .item(&tauri::menu::MenuItemBuilder::with_id("show", "Show").build(app)?)
                        .item(&tauri::menu::MenuItemBuilder::with_id("quit", "Quit").build(app)?)
                        .build()?
                )
                .build()?;

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running application");
}
```

### Web Frontend

```typescript
// src/App.tsx
import { invoke } from '@tauri-apps/api/core';
import { open, save } from '@tauri-apps/plugin-dialog';
import { readTextFile, writeTextFile } from '@tauri-apps/plugin-fs';

function App() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [greeting, setGreeting] = useState('');

  useEffect(() => {
    // Invoke Rust command
    invoke<string>('greet', { name: 'Tom' }).then(setGreeting);
    invoke<Task[]>('get_tasks').then(setTasks);
  }, []);

  async function handleOpenFile() {
    const file = await open({
      multiple: false,
      filters: [{ name: 'Text', extensions: ['txt'] }],
    });
    if (file) {
      const content = await readTextFile(file as string);
      console.log(content);
    }
  }

  async function handleSaveFile() {
    const filePath = await save({
      filters: [{ name: 'JSON', extensions: ['json'] }],
    });
    if (filePath) {
      await writeTextFile(filePath, JSON.stringify(tasks));
    }
  }

  return (
    <div>
      <h1>{greeting}</h1>
      <button onClick={handleOpenFile}>Open File</button>
      <button onClick={handleSaveFile}>Save Tasks</button>
      <ul>
        {tasks.map(task => (
          <li key={task.id}>{task.title}</li>
        ))}
      </ul>
    </div>
  );
}
```

---

## 5. Electron

### Main Process

```javascript
// main.js
const { app, BrowserWindow, ipcMain, Menu, Tray, dialog } = require('electron');
const path = require('path');

let mainWindow;
let tray;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
    frame: false,
    titleBarStyle: 'hidden',
  });

  mainWindow.loadFile('dist/index.html');
}

// IPC handlers
ipcMain.handle('get-file', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters: [{ name: 'Images', extensions: ['jpg', 'png'] }],
  });
  return result.filePaths[0];
});

ipcMain.handle('save-file', async (event, data) => {
  const result = await dialog.showSaveDialog(mainWindow, {
    filters: [{ name: 'JSON', extensions: ['json'] }],
  });
  if (!result.canceled) {
    require('fs').writeFileSync(result.filePath, JSON.stringify(data));
  }
});

// Auto updater
const { autoUpdater } = require('electron-updater');
autoUpdater.checkForUpdatesAndNotify();

app.whenReady().then(createWindow);
```

### Preload Script

```javascript
// preload.js
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // Renderer → Main (invoke → handle)
  getFile: () => ipcRenderer.invoke('get-file'),
  saveFile: (data) => ipcRenderer.invoke('save-file', data),

  // Main → Renderer (send → on)
  onUpdateAvailable: (callback) => {
    ipcRenderer.on('update-available', (_event, info) => callback(info));
  },

  // Renderer → Main → Renderer (sendSync)
  getAppVersion: () => ipcRenderer.sendSync('get-app-version'),

  // Window controls
  minimize: () => ipcRenderer.send('window-minimize'),
  maximize: () => ipcRenderer.send('window-maximize'),
  close: () => ipcRenderer.send('window-close'),
});
```

### Renderer

```tsx
// App.tsx
const App: React.FC = () => {
  const [version, setVersion] = useState<string>('');

  useEffect(() => {
    // Use exposed API from preload
    const ver = window.electronAPI.getAppVersion();
    setVersion(ver);

    window.electronAPI.onUpdateAvailable((info) => {
      console.log('Update available:', info);
    });
  }, []);

  const handleOpen = async () => {
    const filePath = await window.electronAPI.getFile();
    if (filePath) {
      // Process file
    }
  };

  return (
    <div>
      <div className="titlebar" id="drag-region">
        <span>My App v{version}</span>
        <div className="window-controls">
          <button onClick={() => window.electronAPI.minimize()}>─</button>
          <button onClick={() => window.electronAPI.maximize()}>□</button>
          <button onClick={() => window.electronAPI.close()}>✕</button>
        </div>
      </div>
      <div className="content">
        <button onClick={handleOpen}>Open File</button>
      </div>
    </div>
  );
};
```

---

## 6. Comparison: When to Use Which

### Decision Matrix

| Factor | Flutter | React Native | Kotlin MP | Tauri | Electron |
|--------|---------|-------------|-----------|-------|----------|
| **Target platforms** | iOS, Android, Web, Desktop | iOS, Android, Web | iOS, Android, Desktop | Desktop (Win/Mac/Linux) | Desktop (Win/Mac/Linux) |
| **Language** | Dart | JavaScript/TypeScript | Kotlin | Rust + JS/TS | JavaScript/TypeScript |
| **UI rendering** | Skia (custom engine) | Native components | Compose / Native | Web (system WebView) | Chromium (full browser) |
| **App size** | ~6MB minimal | ~7MB minimal | ~4MB minimal | ~3MB minimal | ~150MB minimal |
| **Performance** | Native (60fps) | Near-native | Native | Near-native | Moderate |
| **Startup time** | Fast | Fast | Fast | Very fast | Slow |
| **Memory usage** | Moderate | Moderate | Low | Very low | High |
| **Native API access** | Platform channels | Native modules | expect/actual | Rust + plugin | Node.js modules |
| **Hot reload** | Yes | Yes | Yes | No (manual) | No |
| **Maturity** | Mature (stable) | Mature (stable) | Growing | Growing | Very mature |
| **Community** | Large, growing | Very large | Small, growing | Growing | Very large |
| **Best for** | Consumer apps | Social/food apps | Shared logic | Desktop utilities | Desktop apps |

### Decision Flow

```
Need cross-platform mobile?
├── Yes → Need maximum performance?
│   ├── Yes → Flutter
│   └── No → Need native feel?
│       ├── Yes → React Native
│       └── No → Flutter
│
Need cross-platform desktop?
├── Need small file size?
│   ├── Yes → Tauri
│   └── No → Need maximum platform APIs?
│       ├── Yes → Electron
│       └── No → Tauri
│
Need shared business logic (different UIs)?
├── Kotlin Multiplatform

Need all platforms?
├── Flutter or React Native (mobile) + Tauri (desktop)
└── Kotlin MP for shared logic + per-platform UI
```

---

## 7. Performance Benchmarks

| Metric | Flutter | React Native | Tauri | Electron |
|--------|---------|-------------|-------|----------|
| Cold start (iOS) | 1.2s | 2.1s | — | — |
| Cold start (desktop) | 1.5s | — | 0.3s | 3.5s |
| Memory (simple app) | 35MB | 40MB | 15MB | 120MB |
| Memory (complex) | 80MB | 95MB | 40MB | 250MB+ |
| App bundle size | 6-10MB | 7-15MB | 3-8MB | 120-200MB |
| Frame rate (60fps) | Native | Mostly | Native | Droppable |
| Dev build time | Fast | Fast | Medium | Fast |

---

## 8. Shared Code Strategies

### Code Sharing Architecture

```
Shared Business Logic (60-80% of code)
├── Data models / entities
├── API client / networking
├── State management
├── Business logic / use cases
├── Validation
└── Storage / caching

Platform-Specific (20-40% of code)
├── UI components
├── Navigation
├── Hardware features (camera, sensors)
├── Platform-specific APIs
└── Animations
```

### Strategy by Framework

```
Flutter: 95% shared (including UI), 5% platform (channels)
React Native: 90% shared (including UI), 10% platform (native modules)
Kotlin MP: 60-80% shared (logic only), 20-40% platform (UI)
Tauri: 80% shared (web UI), 20% platform (Rust backend)
Electron: 90% shared (including UI), 10% platform (native modules)
```

---

## 9. Platform-Specific Customization

### Flutter

```dart
import 'dart:io' show Platform;

if (Platform.isIOS) {
  return CupertinoPageScaffold(
    navigationBar: CupertinoNavigationBar(
      middle: Text('iOS Style'),
    ),
    child: content,
  );
} else {
  return Scaffold(
    appBar: AppBar(title: Text('Material Style')),
    body: content,
  );
}
```

### React Native

```typescript
import { Platform, StyleSheet } from 'react-native';

const styles = StyleSheet.create({
  container: {
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.25,
      },
      android: {
        elevation: 4,
      },
    }),
  },
  font: {
    fontFamily: Platform.OS === 'ios' ? 'System' : 'Roboto',
  },
});
```

---

## Build & Deploy Checklist

### Flutter
- [ ] `flutter analyze` — no issues
- [ ] `flutter test` — all passing
- [ ] Build with `--release` flag
- [ ] App icon for all platforms
- [ ] Splash screen configured
- [ ] Deep linking configured
- [ ] Push notifications

### React Native
- [ ] Hermes enabled for iOS & Android
- [ ] Metro bundle size optimized
- [ ] CodePush / Expo Updates configured
- [ ] Sentry or Crashlytics integrated
- [ ] Fastlane for deployment automation

### Tauri
- [ ] Rust code clippy-clean
- [ ] CSP headers configured in `tauri.conf.json`
- [ ] Bundle identifier set
- [ ] Code signing for macOS/Windows
- [ ] Auto-updater configured

### Electron
- [ ] `electron-builder` configured
- [ ] Auto-update (electron-updater)
- [ ] Code signing
- [ ] Crash reporter (Sentry)
- [ ] App icon for all OS
- [ ] Notarization for macOS
- [ ] NSIS/DMG packaging
