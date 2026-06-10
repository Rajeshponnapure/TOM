# Mobile UI Design — Comprehensive Guide

## 1. Material Design 3 (Material You)

Material Design 3 is Google's latest design system, introducing dynamic color, adaptive layouts, and updated components.

### Design Tokens

```json
{
  "color": {
    "primary": "#6750A4",
    "on-primary": "#FFFFFF",
    "primary-container": "#EADDFF",
    "on-primary-container": "#21005D",
    "secondary": "#625B71",
    "on-secondary": "#FFFFFF",
    "secondary-container": "#E8DEF8",
    "on-secondary-container": "#1D192B",
    "tertiary": "#7D5260",
    "on-tertiary": "#FFFFFF",
    "tertiary-container": "#FFD8E4",
    "on-tertiary-container": "#31111D",
    "error": "#B3261E",
    "on-error": "#FFFFFF",
    "error-container": "#F9DEDC",
    "on-error-container": "#410E0B",
    "background": "#FFFBFE",
    "on-background": "#1C1B1F",
    "surface": "#FFFBFE",
    "on-surface": "#1C1B1F",
    "surface-variant": "#E7E0EC",
    "on-surface-variant": "#49454F",
    "outline": "#79747E",
    "outline-variant": "#CAC4D0",
    "shadow": "#000000",
    "inverse-surface": "#313033",
    "inverse-on-surface": "#F4EFF4",
    "inverse-primary": "#D0BCFF"
  },
  "typography": {
    "display-large": { "font": "Google Sans", "size": 57, "weight": 400, "line-height": 64, "tracking": -0.25 },
    "display-medium": { "font": "Google Sans", "size": 45, "weight": 400, "line-height": 52, "tracking": 0 },
    "display-small": { "font": "Google Sans", "size": 36, "weight": 400, "line-height": 44, "tracking": 0 },
    "headline-large": { "font": "Google Sans", "size": 32, "weight": 400, "line-height": 40, "tracking": 0 },
    "headline-medium": { "font": "Google Sans", "size": 28, "weight": 400, "line-height": 36, "tracking": 0 },
    "headline-small": { "font": "Google Sans", "size": 24, "weight": 400, "line-height": 32, "tracking": 0 },
    "title-large": { "font": "Google Sans", "size": 22, "weight": 400, "line-height": 28, "tracking": 0 },
    "title-medium": { "font": "Google Sans", "size": 16, "weight": 500, "line-height": 24, "tracking": 0.15 },
    "title-small": { "font": "Google Sans", "size": 14, "weight": 500, "line-height": 20, "tracking": 0.1 },
    "body-large": { "font": "Google Sans Text", "size": 16, "weight": 400, "line-height": 24, "tracking": 0.5 },
    "body-medium": { "font": "Google Sans Text", "size": 14, "weight": 400, "line-height": 20, "tracking": 0.25 },
    "body-small": { "font": "Google Sans Text", "size": 12, "weight": 400, "line-height": 16, "tracking": 0.4 },
    "label-large": { "font": "Google Sans Text", "size": 14, "weight": 500, "line-height": 20, "tracking": 0.1 },
    "label-medium": { "font": "Google Sans Text", "size": 12, "weight": 500, "line-height": 16, "tracking": 0.5 },
    "label-small": { "font": "Google Sans Text", "size": 11, "weight": 500, "line-height": 16, "tracking": 0.5 }
  },
  "shape": {
    "none": "0px",
    "extra-small": "4px",
    "small": "8px",
    "medium": "12px",
    "large": "16px",
    "extra-large": "28px",
    "full": "9999px"
  },
  "elevation": {
    "level0": "0px 0px 0px 0px transparent",
    "level1": "0px 1px 3px 1px rgba(0,0,0,0.15), 0px 1px 2px 0px rgba(0,0,0,0.30)",
    "level2": "0px 2px 6px 2px rgba(0,0,0,0.15), 0px 1px 2px 0px rgba(0,0,0,0.30)",
    "level3": "0px 4px 8px 3px rgba(0,0,0,0.15), 0px 1px 3px 0px rgba(0,0,0,0.30)",
    "level4": "0px 6px 10px 4px rgba(0,0,0,0.15), 0px 2px 3px 0px rgba(0,0,0,0.30)",
    "level5": "0px 8px 12px 6px rgba(0,0,0,0.15), 0px 4px 4px 0px rgba(0,0,0,0.30)"
  }
}
```

### Dynamic Color (Material You)

```kotlin
// Android — Compose Material 3
@Composable
fun AppTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = true,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context)
            else dynamicLightColorScheme(context)
        }
        darkTheme -> darkColorScheme()
        else -> lightColorScheme()
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = AppTypography,
        shapes = AppShapes,
        content = content
    )
}
```

### Key Component Heights

| Component | Height (dp) |
|---|---|
| Top app bar (small) | 64 |
| Top app bar (medium) | 112 |
| Top app bar (large) | 152 |
| Bottom navigation bar | 80 |
| Navigation rail | Full height, 72+ |
| FAB (default) | 56 |
| FAB (small) | 40 |
| FAB (large) | 96 |
| Buttons | 40 |
| Chips | 32 |
| Text fields | 56 |

## 2. Apple Human Interface Guidelines (HIG)

### iOS Design Principles

| Principle | Description |
|---|---|
| Deference | UI should defer to content — let content shine |
| Clarity | Text is legible, icons precise, decorations subtle |
| Depth | Visual layers convey hierarchy, motion provides context |

### Safe Areas & Layout Margins

```swift
// UIKit
override func viewDidLoad() {
    super.viewDidLoad()
    view.directionalLayoutMargins = NSDirectionalEdgeInsets(
        top: 0, leading: 16, bottom: 0, trailing: 16
    )
}

// SwiftUI
struct ContentView: View {
    var body: some View {
        VStack {
            Text("Content")
        }
        .padding(.horizontal)
        .safeAreaInset(edge: .bottom) {
            CustomTabBar()
        }
    }
}
```

### iOS Device Metrics

| Device | Width (pt) | Height (pt) | Safe Top | Safe Bottom | Status Bar |
|---|---|---|---|---|---|
| iPhone 15 Pro Max | 430 | 932 | 59 | 34 | 54 |
| iPhone 15 Pro | 393 | 852 | 59 | 34 | 54 |
| iPhone SE (3rd) | 375 | 667 | 0 | 0 | 20 |
| iPad Pro 12.9" | 1024 | 1366 | 24 | 20 | 24 |
| iPad Mini | 744 | 1133 | 24 | 20 | 24 |

### iOS Typography — Text Styles

```swift
// Dynamic Type — automatically scales with accessibility settings
Text("Large Title")
    .font(.largeTitle)  // 34pt
Text("Title 1")
    .font(.title)       // 28pt
Text("Title 2")
    .font(.title2)      // 22pt
Text("Title 3")
    .font(.title3)      // 20pt
Text("Headline")
    .font(.headline)    // 17pt, semibold
Text("Body")
    .font(.body)        // 17pt
Text("Callout")
    .font(.callout)     // 16pt
Text("Subheadline")
    .font(.subheadline) // 15pt
Text("Footnote")
    .font(.footnote)    // 13pt
Text("Caption 1")
    .font(.caption)     // 12pt
Text("Caption 2")
    .font(.caption2)    // 11pt
```

### Navigation Bar Configuration

```swift
// UIKit
let appearance = UINavigationBarAppearance()
appearance.configureWithOpaqueBackground()
appearance.backgroundColor = .systemBackground
appearance.titleTextAttributes = [
    .font: UIFont.systemFont(ofSize: 17, weight: .semibold)
]
navigationItem.standardAppearance = appearance
navigationItem.scrollEdgeAppearance = appearance
```

## 3. Responsive & Adaptive Layouts

### Breakpoint System

| Range | Name | Target |
|---|---|---|
| 0–599dp | Compact | Phones |
| 600–839dp | Medium | Tablets (portrait), foldables |
| 840+dp | Expanded | Tablets (landscape), desktops |

### Adaptive Layout with Compose

```kotlin
@Composable
fun AdaptiveLayout(
    windowSizeClass: WindowSizeClass = currentWindowAdaptiveInfo().windowSizeClass
) {
    when (windowSizeClass.windowWidthSizeClass) {
        WindowWidthSizeClass.COMPACT -> {
            // Phone layout — single pane
            CompactScreen()
        }
        WindowWidthSizeClass.MEDIUM -> {
            // Tablet portrait — list-detail
            ListDetailLayout()
        }
        WindowWidthSizeClass.EXPANDED -> {
            // Tablet landscape or desktop — side-by-side
            SidebarContentLayout()
        }
    }
}

@Composable
fun ListDetailLayout() {
    Row {
        NavigationRail(
            modifier = Modifier.weight(0.25f),
            // ...
        )
        DetailContent(
            modifier = Modifier.weight(0.75f)
        )
    }
}
```

### SwiftUI Adaptive Layout

```swift
struct AdaptiveContentView: View {
    @Environment(\.horizontalSizeClass) var horizontalSizeClass
    
    var body: some View {
        if horizontalSizeClass == .compact {
            TabView {
                ContentView()
                    .tabItem { Label("Home", systemImage: "house") }
                SearchView()
                    .tabItem { Label("Search", systemImage: "magnifyingglass") }
                ProfileView()
                    .tabItem { Label("Profile", systemImage: "person") }
            }
        } else {
            NavigationSplitView {
                SidebarView()
            } content: {
                ContentListView()
            } detail: {
                DetailView()
            }
        }
    }
}
```

### CSS Responsive (React Native / Web)

```css
/* Breakpoint-based grid */
.container {
    display: grid;
    gap: 16px;
    padding: 16px;
}

@media (max-width: 599px) {
    .container { grid-template-columns: 1fr; }
}

@media (min-width: 600px) and (max-width: 839px) {
    .container { grid-template-columns: 1fr 1fr; }
}

@media (min-width: 840px) {
    .container { grid-template-columns: 1fr 1fr 1fr 1fr; }
}
```

### Flexible Units

```css
/* Typography clamp — fluid scaling */
h1 {
    font-size: clamp(1.75rem, 1.25rem + 2vw, 3rem);
    line-height: clamp(2.25rem, 1.75rem + 2.5vw, 3.5rem);
}

/* Container queries */
.card {
    container-type: inline-size;
}

@container (max-width: 300px) {
    .card__content {
        flex-direction: column;
    }
}
```

## 4. Gesture Design

### Gesture Taxonomy

| Gesture | Touch Points | Motion | Action |
|---|---|---|---|
| Tap | 1 | Press & release | Select / activate |
| Double tap | 1 | Two quick taps | Zoom / like |
| Long press | 1 | Hold | Context menu / reorder |
| Swipe | 1 | Horizontal or vertical | Scroll / dismiss / navigate |
| Drag | 1 | Continuous movement | Move / reorder |
| Pinch | 2 | Move apart/together | Zoom in/out |
| Rotate | 2 | Circular motion | Rotate content |
| Pan | 2+ | Continuous movement | Scroll / move canvas |
| Force touch | 1 | Variable pressure | Peek / quick actions |

### Gesture Design Principles

| Principle | Guideline |
|---|---|
| Discoverability | Never rely on gestures alone — provide visual hints |
| Consistency | Same gesture = same result across app |
| Ergonomics | Primary gestures in thumb zone (bottom 1/3 of screen) |
| Conflict resolution | Disambiguate with timing, direction, and priority |
| Feedback | Visual/haptic response for every gesture start and end |
| Accessibility | Every gesture must have an alternative (button-based) action |

### SwiftUI Gestures

```swift
struct GestureDemo: View {
    @State private var scale: CGFloat = 1.0
    @State private var offset: CGSize = .zero
    @State private var showContextMenu = false

    var body: some View {
        Image(systemName: "hand.point.up.fill")
            .font(.system(size: 60))
            .scaleEffect(scale)
            .offset(offset)
            // Tap
            .onTapGesture { /* simple tap */ }
            // Double tap
            .onTapGesture(count: 2) {
                withAnimation(.spring()) { scale = 1.5 }
            }
            // Long press
            .onLongPressGesture(minimumDuration: 0.5) {
                showContextMenu = true
            }
            // Drag
            .gesture(
                DragGesture()
                    .onChanged { value in offset = value.translation }
                    .onEnded { _ in
                        withAnimation(.spring()) { offset = .zero }
                    }
            )
            // Magnify (pinch)
            .gesture(
                MagnificationGesture()
                    .onChanged { value in scale = value }
            )
    }
}
```

### Jetpack Compose Gestures

```kotlin
@Composable
fun GestureExample() {
    var offset by remember { mutableStateOf(Offset.Zero) }
    var scale by remember { mutableFloatStateOf(1f) }

    Box(
        modifier = Modifier
            .size(100.dp)
            .background(MaterialTheme.colorScheme.primary)
            .clip(RoundedCornerShape(16.dp))
            .pointerInput(Unit) {
                // Tap
                detectTapGestures(
                    onTap = { /* single tap */ },
                    onDoubleTap = {
                        animateFloatAsState(if (scale == 1f) 1.5f else 1f)
                    },
                    onLongPress = { /* context menu */ }
                )
            }
            .pointerInput(Unit) {
                // Drag
                detectDragGestures { change, dragAmount ->
                    change.consume()
                    offset += dragAmount
                }
            }
            .pointerInput(Unit) {
                // Pinch to zoom
                detectTransformGestures { _, pan, zoom, _ ->
                    scale = (scale * zoom).coerceIn(0.5f, 3f)
                }
            }
            .offset { IntOffset(offset.x.roundToInt(), offset.y.roundToInt()) }
            .graphicsLayer { scaleX = scale; scaleY = scale }
    )
}
```

### React Native Gestures (react-native-gesture-handler)

```tsx
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, {
    useSharedValue, useAnimatedStyle, withSpring
} from 'react-native-reanimated';

function PinchableImage() {
    const scale = useSharedValue(1);
    const savedScale = useSharedValue(1);

    const pinchGesture = Gesture.Pinch()
        .onUpdate((e) => {
            scale.value = savedScale.value * e.scale;
        })
        .onEnd(() => {
            savedScale.value = scale.value;
        });

    const doubleTapGesture = Gesture.Tap()
        .numberOfTaps(2)
        .onEnd(() => {
            if (scale.value > 1) {
                scale.value = withSpring(1);
            } else {
                scale.value = withSpring(2.5);
            }
            savedScale.value = scale.value;
        });

    const composed = Gesture.Simultaneous(pinchGesture, doubleTapGesture);

    const animatedStyle = useAnimatedStyle(() => ({
        transform: [{ scale: scale.value }]
    }));

    return (
        <GestureDetector gesture={composed}>
            <Animated.Image
                source={{ uri: 'https://example.com/photo.jpg' }}
                style={[{ width: 200, height: 200 }, animatedStyle]}
            />
        </GestureDetector>
    );
}
```

## 5. Navigation Patterns

### Navigation Types

| Pattern | Description | Best For |
|---|---|---|
| Stack navigation | Push/pop screens (like iOS UINavigationController) | Linear flows, drill-down |
| Tab navigation | Persistent bottom/bar tabs | Top-level sections |
| Drawer navigation | Side menu, slides in from edge | Many top-level sections |
| Modal presentation | Full-screen or sheet overlay | Forms, alerts, pickers |
| Navigation rail | Side tabs (tablets/desktop) | Responsive UIs |
| Back | Gesture-based or button | Hierarchical content |
| Stepper / wizard | Sequential steps | Onboarding, checkout |
| Search-based | Search bar as primary navigation | Content-heavy apps |

### iOS Navigation Stack

```swift
struct AppNavigation: View {
    var body: some View {
        TabView {
            NavigationStack {
                HomeView()
            }
            .tabItem { Label("Home", systemImage: "house") }

            NavigationStack {
                SearchView()
            }
            .tabItem { Label("Search", systemImage: "magnifyingglass") }

            NavigationStack {
                ProfileView()
            }
            .tabItem { Label("Profile", systemImage: "person") }
        }
    }
}

struct HomeView: View {
    var body: some View {
        List(articles) { article in
            NavigationLink(value: article.id) {
                ArticleRow(article: article)
            }
        }
        .navigationTitle("Home")
        .navigationDestination(for: Article.ID.self) { id in
            ArticleDetailView(articleId: id)
        }
    }
}
```

### Jetpack Compose Navigation

```kotlin
// Define routes
sealed class Route(val route: String) {
    object Home : Route("home")
    object ArticleList : Route("articles")
    data class ArticleDetail(val id: String) : Route("articles/{id}") {
        companion object {
            const val pattern = "articles/{id}"
        }
    }
}

@Composable
fun AppNavigation() {
    val navController = rememberNavController()

    NavHost(navController, startDestination = Route.Home.route) {
        composable(Route.Home.route) {
            HomeScreen(
                onNavigateToArticles = {
                    navController.navigate(Route.ArticleList.route)
                }
            )
        }
        composable(Route.ArticleList.route) {
            ArticleListScreen(
                onArticleClick = { id ->
                    navController.navigate("articles/$id")
                }
            )
        }
        composable(
            route = Route.ArticleDetail.pattern,
            arguments = listOf(navArgument("id") { type = NavType.StringType })
        ) { backStackEntry ->
            val id = backStackEntry.arguments?.getString("id") ?: return@composable
            ArticleDetailScreen(articleId = id)
        }
    }

    // Bottom nav bar
    Scaffold(
        bottomBar = {
            NavigationBar {
                NavigationBarItem(
                    selected = currentRoute?.route == Route.Home.route,
                    onClick = { navController.navigate(Route.Home.route) { popUpTo(0) } },
                    icon = { Icon(Icons.Default.Home, "Home") },
                    label = { Text("Home") }
                )
                NavigationBarItem(
                    selected = currentRoute?.route == Route.ArticleList.route,
                    onClick = { navController.navigate(Route.ArticleList.route) { popUpTo(0) } },
                    icon = { Icon(Icons.Default.List, "Articles") },
                    label = { Text("Articles") }
                )
            }
        }
    ) { padding ->
        // Content rendered inside NavHost
    }
}
```

### React Navigation (React Native)

```tsx
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';

type RootStackParamList = {
    Home: undefined;
    ArticleList: undefined;
    ArticleDetail: { id: string };
};

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator();

function HomeStack() {
    return (
        <Stack.Navigator>
            <Stack.Screen name="Home" component={HomeScreen} />
            <Stack.Screen name="ArticleList" component={ArticleListScreen} />
            <Stack.Screen name="ArticleDetail" component={ArticleDetailScreen} />
        </Stack.Navigator>
    );
}

export default function App() {
    return (
        <NavigationContainer>
            <Tab.Navigator>
                <Tab.Screen
                    name="HomeTab"
                    component={HomeStack}
                    options={{ tabBarLabel: 'Home' }}
                />
                <Tab.Screen
                    name="SearchTab"
                    component={SearchStack}
                    options={{ tabBarLabel: 'Search' }}
                />
            </Tab.Navigator>
        </NavigationContainer>
    );
}
```

### Deep Linking

```swift
// iOS — AppDelegate
func application(
    _ app: UIApplication,
    open url: URL,
    options: [UIApplication.OpenURLOptionsKey: Any] = [:]
) -> Bool {
    guard let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
          let host = components.host else { return false }

    switch host {
    case "article":
        if let id = components.queryItems?.first(where: { $0.name == "id" })?.value {
            navigateToArticle(id)
        }
    case "profile":
        navigateToProfile()
    default:
        return false
    }
    return true
}
```

```kotlin
// Android — AndroidManifest intent filter
// <intent-filter>
//     <action android:name="android.intent.action.VIEW" />
//     <category android:name="android.intent.category.DEFAULT" />
//     <category android:name="android.intent.category.BROWSABLE" />
//     <data android:scheme="myapp" android:host="article" />
// </intent-filter>

// Compose — handle deep link
NavHost(
    navController = navController,
    startDestination = "home",
    deepLinks = listOf(
        navDeepLink { uriPattern = "myapp://article/{id}" }
    )
) { /* routes */ }
```

## 6. Form Design

### Form Design Principles

| Principle | Guideline |
|---|---|
| One thing per page | Complex forms should be multi-step |
| Label every field | Floating labels or persistent labels |
| Smart defaults | Pre-fill values when possible |
| Input validation | Validate inline, not on submit |
| Error messages | Specific, helpful, near the field |
| Keyboard type | Set appropriate keyboard (email, number, URL) |
| Auto-focus | Focus first field on mount |
| Progress indicator | Show step progress for multi-step forms |
| Save drafts | Don't lose data on accidental back |

### Input Types & Keyboard

```swift
// SwiftUI — keyboard types
TextField("Email", text: $email)
    .keyboardType(.emailAddress)
    .textContentType(.emailAddress)
    .autocapitalization(.none)
    .disableAutocorrection(true)

TextField("Phone", text: $phone)
    .keyboardType(.phonePad)

TextField("Amount", value: $amount, format: .currency(code: "USD"))
    .keyboardType(.decimalPad)

SecureField("Password", text: $password)
    .textContentType(.password)
```

```kotlin
// Compose — keyboard options
OutlinedTextField(
    value = email,
    onValueChange = { email = it },
    label = { Text("Email") },
    keyboardOptions = KeyboardOptions(
        keyboardType = KeyboardType.Email,
        imeAction = ImeAction.Next
    ),
    singleLine = true
)

OutlinedTextField(
    value = amount,
    onValueChange = { amount = it },
    label = { Text("Amount") },
    keyboardOptions = KeyboardOptions(
        keyboardType = KeyboardType.Decimal,
        imeAction = ImeAction.Done
    ),
    visualTransformation = VisualTransformation.None,
    prefix = { Text("$") }
)
```

### Validation Pattern

```kotlin
// Compose — inline validation
@Composable
fun EmailField(
    email: String,
    onEmailChange: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    var hasError by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf("") }

    OutlinedTextField(
        value = email,
        onValueChange = {
            onEmailChange(it)
            hasError = false
        },
        label = { Text("Email") },
        isError = hasError,
        supportingText = if (hasError) {
            { Text(errorMessage, color = MaterialTheme.colorScheme.error) }
        } else null,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.EmailAddress),
        singleLine = true,
        modifier = modifier
    )

    // Expose validation function
    LaunchedEffect(email) {
        if (email.isNotEmpty() && !isValidEmail(email)) {
            hasError = true
            errorMessage = "Please enter a valid email"
        }
    }
}

fun isValidEmail(email: String): Boolean {
    return android.util.Patterns.EMAIL_ADDRESS.matcher(email).matches()
}
```

### Form Accessibility

```kotlin
// Compose — labeled form with error announcement
OutlinedTextField(
    value = phone,
    onValueChange = { phone = it },
    label = { Text("Phone number") },
    modifier = Modifier
        .semantics {
            contentDescription = "Phone number"
            stateDescription = if (hasError) "Error: $errorMessage" else ""
            error(hasError)
        },
    isError = hasError,
    supportingText = {
        if (hasError) Text(
            text = errorMessage,
            color = MaterialTheme.colorScheme.error,
            modifier = Modifier.semantics { liveRegion = LiveRegion.Assertive }
        )
    }
)
```

## 7. Loading, Empty & Error States

### The Three-State Pattern

Every screen should handle three states: Loading, Success (content), and Error.

```kotlin
// Compose — sealed state
sealed class UiState<out T> {
    object Loading : UiState<Nothing>()
    data class Success<T>(val data: T) : UiState<T>()
    data class Error(val message: String, val throwable: Throwable? = null) : UiState<Nothing>()
}

@Composable
fun <T> StatefulContent(
    state: UiState<T>,
    onRetry: () -> Unit = {},
    loadingContent: @Composable () -> Unit = { FullScreenLoader() },
    errorContent: @Composable (String) -> Unit = { message -> ErrorScreen(message, onRetry) },
    content: @Composable (T) -> Unit
) {
    when (state) {
        is UiState.Loading -> loadingContent()
        is UiState.Success -> content(state.data)
        is UiState.Error -> errorContent(state.message)
    }
}

@Composable
fun FullScreenLoader() {
    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center
    ) {
        CircularProgressIndicator()
    }
}

@Composable
fun ErrorScreen(message: String, onRetry: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(
            imageVector = Icons.Default.Warning,
            contentDescription = null,
            modifier = Modifier.size(64.dp),
            tint = MaterialTheme.colorScheme.error
        )
        Spacer(Modifier.height(16.dp))
        Text(
            text = "Something went wrong",
            style = MaterialTheme.typography.titleMedium
        )
        Spacer(Modifier.height(8.dp))
        Text(
            text = message,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(Modifier.height(24.dp))
        Button(onClick = onRetry) {
            Text("Try Again")
        }
    }
}
```

### Skeleton Loading

```kotlin
// Compose — shimmer skeleton
@Composable
fun SkeletonLoader(modifier: Modifier = Modifier) {
    val infiniteTransition = rememberInfiniteTransition()
    val alpha by infiniteTransition.animateFloat(
        initialValue = 0.3f,
        targetValue = 0.7f,
        animationSpec = infiniteRepeatable(
            animation = tween(1000, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        )
    )

    Column(modifier.padding(16.dp)) {
        // Header skeleton
        Box(
            modifier = Modifier
                .width(200.dp)
                .height(24.dp)
                .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = alpha))
                .clip(RoundedCornerShape(4.dp))
        )
        Spacer(Modifier.height(12.dp))
        // Content lines
        repeat(3) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(16.dp)
                    .padding(vertical = 4.dp)
                    .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = alpha))
                    .clip(RoundedCornerShape(4.dp))
            )
        }
        Spacer(Modifier.height(16.dp))
        // Card skeleton
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(120.dp)
                .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = alpha))
                .clip(RoundedCornerShape(12.dp))
        )
    }
}
```

### Empty States

```swift
// SwiftUI — empty state
struct EmptyStateView: View {
    let title: String
    let message: String
    let actionTitle: String?
    let action: (() -> Void)?

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "tray")
                .font(.system(size: 64))
                .foregroundStyle(.secondary)
            Text(title)
                .font(.title2)
                .fontWeight(.semibold)
            Text(message)
                .font(.body)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            if let actionTitle, let action {
                Button(actionTitle, action: action)
                    .buttonStyle(.borderedProminent)
                    .padding(.top, 8)
            }
        }
        .padding(.horizontal, 32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
```

### Snackbar & Toast

```kotlin
// Compose — Snackbar
@Composable
fun ScreenWithSnackbar() {
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    Scaffold(
        snackbarHost = { SnackbarHost(hostState = snackbarHostState) }
    ) { padding ->
        Button("Show Error") {
            scope.launch {
                snackbarHostState.showSnackbar(
                    message = "Network error. Please try again.",
                    actionLabel = "Retry",
                    duration = SnackbarDuration.Long
                )
            }
        }
    }
}
```

## 8. Accessibility (a11y)

### Touch Targets

| Platform | Minimum Size | Best Practice |
|---|---|---|
| iOS | 44x44 pt | 48x48 pt for safety |
| Android | 48x48 dp | 48dp minimum, 64dp recommended |
| Web (mobile) | 44x44 CSS px | 48px |

### Dynamic Type Support

```swift
// SwiftUI — ScaledMetric for custom sizes
struct CustomView: View {
    @ScaledMetric(relativeTo: .body) var padding: CGFloat = 16
    @ScaledMetric(relativeTo: .title) var iconSize: CGFloat = 24

    var body: some View {
        HStack(spacing: padding) {
            Image(systemName: "star")
                .font(.system(size: iconSize))
            Text("Important")
                .font(.body)
        }
        .padding(padding)
        .dynamicTypeSize(...DynamicTypeSize.accessibility3)
    }
}
```

```kotlin
// Compose — respect font scale
@Composable
fun AccessibleButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val density = LocalDensity.current
    val configuration = LocalConfiguration.current
    val fontScale = configuration.fontScale

    Button(
        onClick = onClick,
        modifier = modifier
            .height(48.dp * fontScale)  // Scale with font
            .defaultMinSize(minWidth = 48.dp * fontScale)
    ) {
        Text("Submit")
    }
}
```

### Screen Reader Labels

```swift
// SwiftUI
Button(action: deleteItem) {
    Image(systemName: "trash")
}
.accessibilityLabel("Delete item")
.accessibilityHint("Removes this item permanently")
.accessibilityRemoveTraits(.isImage)
// Or .accessibilityAddTraits(.isButton)
```

```kotlin
// Compose
IconButton(
    onClick = { deleteItem() },
    modifier = Modifier.semantics {
        contentDescription = "Delete item"
        // Also set stateDescription for dynamic values
        stateDescription = if (isDeleting) "Deleting" else ""
    }
) {
    Icon(Icons.Default.Delete, contentDescription = null)
}
```

```tsx
// React Native
<TouchableOpacity
    onPress={deleteItem}
    accessibilityLabel="Delete item"
    accessibilityHint="Removes this item permanently"
    accessibilityRole="button"
>
    <Icon name="trash" />
</TouchableOpacity>
```

### Accessibility Inspector

```swift
// UIKit — programmatic audit
func performAccessibilityAudit() {
    let elements = view.allSubviews()
    for element in elements {
        if element.isAccessibilityElement && element.accessibilityLabel == nil {
            print("Missing label: \(type(of: element))")
        }
        if let control = element as? UIControl,
           control.isEnabled && control.isAccessibilityElement {
            assert(control.accessibilityTraits.contains(.button) ||
                   control.accessibilityTraits.contains(.link))
        }
    }
}
```

### Android Accessibility Checks

```kotlin
// Use AccessibilityTestChecker with Espresso
@Test
fun testAccessibility() {
    AccessibilityChecks.enable()
    onView(withId(R.id.main_content))
        .check(matches(isDisplayed()))
        .perform(scrollTo())
}

// Programmatic check
fun checkAccessibility(view: View) {
    val checker = AccessibilityNodeInfoCompat.AccessibilityActionCompat
    val info = AccessibilityNodeInfoCompat.obtain(view)
    if (info.className == "android.widget.Button" &&
        info.contentDescription == null &&
        info.text == null
    ) {
        Log.w("A11Y", "Button without label found")
    }
}
```

## 9. Design Token Systems for Mobile

### Token Hierarchy

```
Global tokens (primitives)
    |
    v
Alias tokens (semantic)
    |
    v
Component tokens (specific)
```

### Global Tokens (Primitives)

```json
{
  "color": {
    "blue-50": "#E3F2FD",
    "blue-100": "#BBDEFB",
    "blue-200": "#90CAF9",
    "blue-300": "#64B5F6",
    "blue-400": "#42A5F5",
    "blue-500": "#2196F3",
    "blue-600": "#1E88E5",
    "blue-700": "#1976D2",
    "blue-800": "#1565C0",
    "blue-900": "#0D47A1",
    "neutral-0": "#000000",
    "neutral-50": "#FAFAFA",
    "neutral-100": "#F5F5F5",
    "neutral-200": "#EEEEEE",
    "neutral-300": "#E0E0E0",
    "neutral-800": "#424242",
    "neutral-900": "#212121",
    "neutral-1000": "#FFFFFF"
  },
  "spacing": {
    "xs": 4,
    "sm": 8,
    "md": 16,
    "lg": 24,
    "xl": 32,
    "2xl": 48,
    "3xl": 64
  },
  "border-radius": {
    "none": 0,
    "sm": 4,
    "md": 8,
    "lg": 12,
    "xl": 16,
    "full": 9999
  },
  "font-size": {
    "xs": 12,
    "sm": 14,
    "md": 16,
    "lg": 18,
    "xl": 20,
    "2xl": 24,
    "3xl": 32,
    "4xl": 40
  },
  "font-weight": {
    "regular": "400",
    "medium": "500",
    "semibold": "600",
    "bold": "700"
  },
  "opacity": {
    "disabled": 0.38,
    "medium": 0.6,
    "high": 0.87
  }
}
```

### Semantic Tokens (Aliases)

```json
{
  "color": {
    "text-primary": "{color.neutral-900}",
    "text-secondary": "{color.neutral-800}",
    "text-disabled": "{color.neutral-800}",
    "text-inverse": "{color.neutral-1000}",
    "background-primary": "{color.neutral-1000}",
    "background-secondary": "{color.neutral-50}",
    "background-tertiary": "{color.neutral-100}",
    "border-default": "{color.neutral-300}",
    "border-focus": "{color.blue-500}",
    "border-error": "#B3261E",
    "interactive-primary": "{color.blue-600}",
    "interactive-hover": "{color.blue-700}",
    "interactive-pressed": "{color.blue-800}",
    "interactive-disabled": "{color.neutral-300}"
  },
  "spacing": {
    "inset": "{spacing.md}",
    "inset-sm": "{spacing.sm}",
    "stack": "{spacing.md}",
    "inline": "{spacing.sm}",
    "section": "{spacing.xl}"
  }
}
```

### Component Tokens (Compose)

```kotlin
// Token as Kotlin object
object AppTokens {
    object Color {
        val textPrimary = Color(0xFF1C1B1F)
        val textSecondary = Color(0xFF49454F)
        val surface = Color(0xFFFFFBFE)
        val surfaceVariant = Color(0xFFE7E0EC)
        val primary = Color(0xFF6750A4)
        val primaryContainer = Color(0xFFEADDFF)
        val error = Color(0xFFB3261E)
        val outline = Color(0xFF79747E)
    }

    object Spacing {
        val xs = 4.dp
        val sm = 8.dp
        val md = 16.dp
        val lg = 24.dp
        val xl = 32.dp
    }

    object Typography {
        val heading1 = TextStyle(
            fontSize = 32.sp,
            fontWeight = FontWeight.Bold,
            lineHeight = 40.sp
        )
        val heading2 = TextStyle(
            fontSize = 24.sp,
            fontWeight = FontWeight.Semibold,
            lineHeight = 32.sp
        )
        val body = TextStyle(
            fontSize = 16.sp,
            fontWeight = FontWeight.Normal,
            lineHeight = 24.sp
        )
        val caption = TextStyle(
            fontSize = 12.sp,
            fontWeight = FontWeight.Normal,
            lineHeight = 16.sp,
            color = Color(0xFF49454F)
        )
    }

    object Shape {
        val small = RoundedCornerShape(8.dp)
        val medium = RoundedCornerShape(12.dp)
        val large = RoundedCornerShape(16.dp)
        val full = RoundedCornerShape(9999.dp)
    }

    object Elevation {
        val card = 2.dp
        val dialog = 6.dp
        val fab = 6.dp
        val bottomNav = 8.dp
    }
}
```

### Token Usage (SwiftUI)

```swift
struct AppTheme {
    // Colors
    static let primary = Color(hex: "6750A4")
    static let surface = Color(hex: "FFFBFE")
    static let textPrimary = Color(hex: "1C1B1F")
    static let textSecondary = Color(hex: "49454F")

    // Spacing
    static let spacingXS: CGFloat = 4
    static let spacingSM: CGFloat = 8
    static let spacingMD: CGFloat = 16
    static let spacingLG: CGFloat = 24
    static let spacingXL: CGFloat = 32

    // Typography
    static let headingFont = Font.system(size: 24, weight: .semibold)
    static let bodyFont = Font.system(size: 16, weight: .regular)
    static let captionFont = Font.system(size: 12, weight: .regular)
}

// Environment key for theme injection
private struct AppThemeKey: EnvironmentKey {
    static let defaultValue = AppTheme.self
}

extension EnvironmentValues {
    var appTheme: AppTheme.Type {
        get { self[AppThemeKey.self] }
        set { self[AppThemeKey.self] = newValue }
    }
}
```

### Token Distribution

```yaml
# design-tokens.yaml
# Single source of truth — can generate platform-specific tokens
tokens:
  color:
    primary:
      value: "#6750A4"
      type: color
    on-primary:
      value: "#FFFFFF"
      type: color
  spacing:
    md:
      value: 16
      type: dimension
```

Generate Swift/Kotlin from YAML using style-dictionary:

```bash
npm install -g style-dictionary
style-dictionary build --config config.json
```

```json
{
  "source": ["tokens/**/*.json"],
  "platforms": {
    "android": {
      "transformGroup": "android",
      "buildPath": "app/src/main/res/values/",
      "files": [{
        "destination": "tokens.xml",
        "format": "android/resources"
      }]
    },
    "ios": {
      "transformGroup": "ios-swift",
      "buildPath": "ios/App/",
      "files": [{
        "destination": "Tokens.swift",
        "format": "ios-swift/class.swift"
      }]
    }
  }
}
```

## Platform-Specific Best Practices

### iOS

| Practice | Rationale |
|---|---|
| Use system colors | Automatic dark mode support |
| SF Symbols for icons | Consistent, scalable, accessibility-friendly |
| NavigationStack over NavigationView | Modern API, better deeplink support |
| .sheet for modals, .fullScreenCover for immersive flows | Appropriate modal depth |
| ScrollView with .safeAreaInset | Proper edge-to-edge content |
| List over manual ScrollView | Free swipe actions, reordering |
| Prefers home indicator auto-hidden | Video/gaming full-screen experiences |

### Android

| Practice | Rationale |
|---|---|
| Edge-to-edge rendering | Modern look, uses entire screen |
| Material 3 with dynamic color | Personalization, up-to-date design |
| Navigation Compose over Fragments | Type-safe, composable-first |
| ViewModels + StateFlow | Survives configuration changes |
| ConstraintLayout in XML | Flat view hierarchy |
| Baseline profiles | Pre-compiled code paths, faster startup |
| App Startup library | Efficient ContentProvider initialization |

### React Native

| Practice | Rationale |
|---|---|
| FlashList over FlatList | 10x better performance with recycling |
| Hermes engine | Faster startup, smaller bundle |
| react-native-reanimated | 60fps animations on UI thread |
| StyleSheet.create | Optimized style objects |
| Platform-specific extensions (.ios.tsx, .android.tsx) | Platform-optimized code |
| react-native-safe-area-context | Proper safe area handling |
| FastImage over Image | Caching, priority loading |

## Performance Metrics

| Metric | Good | Needs Work | Poor |
|---|---|---|---|
| App launch time | < 2s | 2-4s | > 4s |
| Time to interactive | < 3s | 3-5s | > 5s |
| Frame rate | 60fps stable | 30-60fps | < 30fps |
| Scroll jank | 0 dropped frames | < 5 dropped frames/1000 | > 5 dropped frames |
| APK/IPA size | < 50MB | 50-100MB | > 100MB |
| Memory usage (peak) | < 200MB | 200-400MB | > 400MB |
| Cold start (Android) | < 1.5s | 1.5-3s | > 3s |
| Cold start (iOS) | < 2s | 2-4s | > 4s |
