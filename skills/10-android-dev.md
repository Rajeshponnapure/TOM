# Android Development — Comprehensive Skill Guide

## Table of Contents
1. Kotlin Coroutines (Structured Concurrency, Flows, Channels, StateFlow, SharedFlow)
2. Jetpack Compose (Composition, Recomposition, Side Effects, State Hoisting, Custom Layouts)
3. MVVM + Clean Architecture
4. Room Database (Entities, DAOs, Migrations, Relations)
5. Retrofit + OkHttp + Kotlinx Serialization
6. Hilt DI (Dependency Injection)
7. Material 3 Theming
8. Navigation Compose
9. WorkManager
10. Compose UI Testing
11. Performance Optimization
12. Play Store Deployment

---

## 1. Kotlin Coroutines

### Structured Concurrency

```kotlin
import kotlinx.coroutines.*

// CoroutineScope — manage lifecycle
class MyViewModel : ViewModel() {
    private val scope = viewModelScope

    fun loadData() {
        scope.launch {
            try {
                val data = fetchData()  // Suspending call
                updateUI(data)
            } catch (e: Exception) {
                handleError(e)
            }
        }
    }
}

// SupervisorJob — child failure doesn't cancel siblings
val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
scope.launch { task1() }
scope.launch { task2() }  // Continues even if task1 fails

// Structured concurrency — parent waits for children
scope.launch {
    launch { taskA() }
    launch { taskB() }
    // Both complete before parent continues
}
```

### Flows

```kotlin
import kotlinx.coroutines.flow.*

// Cold flow — starts on collection
fun observeData(): Flow<Result<List<User>>> = flow {
    emit(Result.Loading)
    try {
        val users = api.getUsers()
        emit(Result.Success(users))
    } catch (e: Exception) {
        emit(Result.Error(e))
    }
}.flowOn(Dispatchers.IO)

// StateFlow — state holder, always has value
class UserViewModel : ViewModel() {
    private val _uiState = MutableStateFlow<UserUiState>(UserUiState.Loading)
    val uiState: StateFlow<UserUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            observeData()
                .catch { _uiState.value = UserUiState.Error(it.message) }
                .collect { _uiState.value = UserUiState.Success(it) }
        }
    }
}

// SharedFlow — one-to-many, no initial value
private val _events = MutableSharedFlow<UiEvent>()
val events: SharedFlow<UiEvent> = _events.asSharedFlow()

// Flow operators
val filteredFlow = flow
    .map { transform(it) }
    .filter { it.isValid }
    .debounce(300)              // Wait for pause
    .distinctUntilChanged()     // Skip duplicates
    .catch { emit(defaultValue) }
    .retry(3) { it is IOException }
    .combine(otherFlow) { a, b -> combine(a, b) }
```

### Channels (Concurrent-safe communication)

```kotlin
import kotlinx.coroutines.channels.*

// Channel — hot, rendezvous by default
val channel = Channel<Event>(Channel.UNLIMITED)  // Capabilities: CONFLATED, BUFFERED, RENDEZVOUS

suspend fun produce() {
    channel.send(Event("data"))  // Producer
}

suspend fun consume() {
    for (event in channel) {     // Consumer
        handleEvent(event)
    }
}

// Produce/consume with scope
fun CoroutineScope.produceEvents(): ReceiveChannel<Event> = produce {
    while (true) {
        val event = fetchEvent()
        send(event)
    }
}

fun CoroutineScope.consumeEvents(channel: ReceiveChannel<Event>) = launch {
    for (event in channel) {
        process(event)
    }
}

// Fan-out (multiple consumers)
val channel = Channel<String>(10)
repeat(3) { id ->
    scope.launch {
        for (event in channel) {
            println("Worker $id processing: $event")
        }
    }
}
```

---

## 2. Jetpack Compose

### Composition & Recomposition

```kotlin
@Composable
fun UserProfile(userId: String) {
    // Recomposes when userId changes

    val viewModel: UserViewModel = viewModel()

    // snapshotFlow — observe state as flow
    val user by viewModel.user.collectAsStateWithLifecycle()

    key(userId) {  // Scope recomposition to key changes
        Column {
            UserAvatar(user.avatarUrl)
            UserDetails(user.name, user.email)
            UserStats(user.stats)

            UserActions(
                onEdit = { viewModel.edit(userId) },
                onDelete = { viewModel.delete(userId) },
            )
        }
    }
}
```

### Side Effects

```kotlin
@Composable
fun DataScreen() {
    val scope = rememberCoroutineScope()
    val context = LocalContext.current

    // LaunchedEffect — runs once when entering composition
    LaunchedEffect(Unit) {
        viewModel.loadData()
    }

    // LaunchedEffect — re-launches on key change
    LaunchedEffect(searchQuery) {
        delay(300)  // Debounce
        viewModel.search(searchQuery)
    }

    // DisposableEffect — cleanup on leave
    DisposableEffect(Unit) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_STOP) {
                viewModel.saveState()
            }
        }
        val lifecycle = LocalLifecycleOwner.current.lifecycle
        lifecycle.addObserver(observer)
        onDispose { lifecycle.removeObserver(observer) }
    }

    // SideEffect — runs on every recomposition
    SideEffect {
        // Report to analytics
        analytics.track("screen_view")
    }

    // snapshotFlow — convert state to Flow
    LaunchedEffect(Unit) {
        snapshotFlow { viewModel.count }
            .collect { count -> analytics.track("count", count) }
    }
}
```

### State Hoisting Pattern

```kotlin
// Stateless composable (reusable, testable)
@Composable
fun SearchBar(
    query: String,                    // State (hoisted)
    onQueryChange: (String) -> Unit,  // Events
    onSearch: () -> Unit,            // Events
    modifier: Modifier = Modifier,
) {
    OutlinedTextField(
        value = query,
        onValueChange = onQueryChange,
        trailingIcon = { Icon(Icons.Default.Search, "Search") },
        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
        keyboardActions = KeyboardActions(onSearch = onSearch),
        modifier = modifier.fillMaxWidth(),
    )
}

// Stateful wrapper
@Composable
fun SearchBarWithState(
    onSearch: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    var query by remember { mutableStateOf("") }

    SearchBar(
        query = query,
        onQueryChange = { query = it },
        onSearch = { onSearch(query) },
        modifier = modifier,
    )
}

// Screen-level usage
@Composable
fun UserListScreen() {
    var query by remember { mutableStateOf("") }
    val users by viewModel.filteredUsers.collectAsStateWithLifecycle()

    Column {
        SearchBar(query, onQueryChange = { query = it }, onSearch = { viewModel.search(it) })
        LazyColumn {
            items(users) { user ->
                UserRow(user)
            }
        }
    }
}
```

### Custom Layouts

```kotlin
@Composable
fun Row(
    modifier: Modifier,
    horizontalArrangement: Arrangement,
    verticalAlignment: Alignment,
    content: @Composable RowScope.() -> Unit,
) {
    // Compose provides Row, Column, Box, FlowRow, FlowColumn
}

// Custom layout
@Composable
fun StaggeredGrid(
    modifier: Modifier = Modifier,
    columns: Int = 2,
    content: @Composable () -> Unit,
) {
    Layout(
        content = content,
        modifier = modifier,
    ) { measurables, constraints ->
        val itemConstraints = constraints.copy(minWidth = 0)
        val columnHeights = IntArray(columns) { 0 }
        val placeables = measurables.map { measurable ->
            val column = columnHeights.indexOfSmallest()
            val placeable = measurable.measure(itemConstraints)
            columnHeights[column] += placeable.height
            placeable to column
        }

        val height = columnHeights.maxOrNull() ?: constraints.minHeight
        layout(constraints.maxWidth, height) {
            columnHeights.fill(0)
            placeables.forEach { (placeable, column) ->
                placeable.placeRelative(
                    x = column * (constraints.maxWidth / columns),
                    y = columnHeights[column],
                )
                columnHeights[column] += placeable.height
            }
        }
    }
}
```

---

## 3. MVVM + Clean Architecture

### Project Structure

```
app/
├── data/
│   ├── local/
│   │   ├── dao/
│   │   ├── entity/
│   │   └── database/
│   ├── remote/
│   │   ├── api/
│   │   ├── dto/
│   │   └── interceptor/
│   └── repository/
├── domain/
│   ├── model/
│   ├── repository/    (interfaces)
│   └── usecase/
├── ui/
│   ├── components/
│   ├── navigation/
│   └── screens/
│       ├── home/
│       ├── detail/
│       └── settings/
└── di/
    ├── modules/
    └── AppModule.kt
```

### Use Case Layer

```kotlin
// domain/usecase/GetUserUseCase.kt
class GetUserUseCase @Inject constructor(
    private val userRepository: UserRepository,
) {
    suspend operator fun invoke(userId: String): Result<User> {
        return userRepository.getUser(userId)
    }
}
```

### ViewModel

```kotlin
// ui/screens/detail/DetailViewModel.kt
@HiltViewModel
class DetailViewModel @Inject constructor(
    private val getUserUseCase: GetUserUseCase,
    private val savedStateHandle: SavedStateHandle,
) : ViewModel() {

    private val _uiState = MutableStateFlow<DetailUiState>(DetailUiState.Loading)
    val uiState: StateFlow<DetailUiState> = _uiState.asStateFlow()

    private val _events = MutableSharedFlow<DetailEvent>()
    val events: SharedFlow<DetailEvent> = _events.asSharedFlow()

    init {
        val userId: String = checkNotNull(savedStateHandle["userId"])
        loadUser(userId)
    }

    private fun loadUser(userId: String) {
        viewModelScope.launch {
            _uiState.value = DetailUiState.Loading
            getUserUseCase(userId)
                .onSuccess { user ->
                    _uiState.value = DetailUiState.Success(user)
                }
                .onFailure { error ->
                    _uiState.value = DetailUiState.Error(error.message)
                    _events.emit(DetailEvent.ShowSnackbar(error.message ?: "Unknown error"))
                }
        }
    }

    fun reload() {
        val userId = (_uiState.value as? DetailUiState.Success)?.user?.id ?: return
        loadUser(userId)
    }
}
```

---

## 4. Room Database

### Entities

```kotlin
import androidx.room.*

@Entity(
    tableName = "users",
    indices = [
        Index(value = ["email"], unique = true),
        Index(value = ["created_at"]),
    ],
    foreignKeys = [
        ForeignKey(
            entity = Department::class,
            parentColumns = ["id"],
            childColumns = ["department_id"],
            onDelete = ForeignKey.SET_NULL,
        ),
    ],
)
data class UserEntity(
    @PrimaryKey val id: String,
    @ColumnInfo(name = "email") val email: String,
    @ColumnInfo(name = "name") val name: String,
    @ColumnInfo(name = "department_id") val departmentId: String?,
    @ColumnInfo(name = "created_at") val createdAt: Long,
    @ColumnInfo(name = "updated_at") val updatedAt: Long,
)
```

### DAOs

```kotlin
@Dao
interface UserDao {
    @Query("SELECT * FROM users ORDER BY created_at DESC")
    fun observeAll(): Flow<List<UserEntity>>

    @Query("SELECT * FROM users WHERE id = :id")
    suspend fun getById(id: String): UserEntity?

    @Query("SELECT * FROM users WHERE id = :id")
    fun observeById(id: String): Flow<UserEntity?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(users: List<UserEntity>)

    @Update
    suspend fun update(user: UserEntity)

    @Delete
    suspend fun delete(user: UserEntity)

    @Query("DELETE FROM users WHERE updated_at < :timestamp")
    suspend fun deleteOlderThan(timestamp: Long)

    @Transaction
    @Query("SELECT * FROM users")
    fun observeWithDepartment(): Flow<List<UserWithDepartment>>
}

// Relations
data class UserWithDepartment(
    @Embedded val user: UserEntity,
    @Relation(
        parentColumn = "department_id",
        entityColumn = "id",
    )
    val department: DepartmentEntity?,
)
```

### Migrations

```kotlin
val MIGRATION_1_2 = object : Migration(1, 2) {
    override fun migrate(database: SupportSQLiteDatabase) {
        database.execSQL("ALTER TABLE users ADD COLUMN avatar_url TEXT DEFAULT NULL")
    }
}

val MIGRATION_2_3 = object : Migration(2, 3) {
    override fun migrate(database: SupportSQLiteDatabase) {
        database.execSQL("""
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
    }
}

@Database(
    entities = [UserEntity::class, DepartmentEntity::class, PostEntity::class],
    version = 3,
    exportSchema = true,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun userDao(): UserDao
}
```

---

## 5. Retrofit + OkHttp + Kotlinx Serialization

```kotlin
import retrofit2.Retrofit
import retrofit2.http.*
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

// API Service
interface ApiService {
    @GET("users")
    suspend fun getUsers(
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 20,
    ): ApiResponse<List<UserDto>>

    @GET("users/{id}")
    suspend fun getUser(@Path("id") id: String): UserDto

    @POST("users")
    suspend fun createUser(@Body user: CreateUserRequest): UserDto

    @PUT("users/{id}")
    suspend fun updateUser(@Path("id") id: String, @Body user: UpdateUserRequest): UserDto

    @DELETE("users/{id}")
    suspend fun deleteUser(@Path("id") id: String)

    @Multipart
    @POST("users/{id}/avatar")
    suspend fun uploadAvatar(
        @Path("id") id: String,
        @Part avatar: MultipartBody.Part,
    ): UserDto

    @Streaming
    @GET("files/{name}")
    suspend fun downloadFile(@Path("name") name: String): ResponseBody
}

// Network Module
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun provideJson(): Json = Json {
        ignoreUnknownKeys = true
        coerceInputValues = true
        encodeDefaults = true
        isLenient = true
    }

    @Provides
    @Singleton
    fun provideOkHttpClient(
        authInterceptor: AuthInterceptor,
    ): OkHttpClient = OkHttpClient.Builder()
        .addInterceptor(authInterceptor)
        .addInterceptor(HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) BODY else NONE
        })
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    @Provides
    @Singleton
    fun provideRetrofit(
        okHttpClient: OkHttpClient,
        json: Json,
    ): Retrofit = Retrofit.Builder()
        .baseUrl(BuildConfig.API_BASE_URL)
        .client(okHttpClient)
        .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
        .build()

    @Provides
    @Singleton
    fun provideApiService(retrofit: Retrofit): ApiService =
        retrofit.create(ApiService::class.java)
}
```

---

## 6. Hilt DI

```kotlin
@HiltAndroidApp
class MyApplication : Application()

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MyApp() }
    }
}

// ViewModel
@HiltViewModel
class HomeViewModel @Inject constructor(
    private val getUserUseCase: GetUserUseCase,
    private val analyticsRepo: AnalyticsRepository,
) : ViewModel()

// Fragment
@AndroidEntryPoint
class HomeFragment : Fragment()

// Custom View
@AndroidEntryPoint
class MyCustomView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : ConstraintLayout(context, attrs) {
    @Inject lateinit var analytics: AnalyticsRepository
}

// Scopes
@Module
@InstallIn(SingletonComponent::class)  // App scope
object DatabaseModule {
    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AppDatabase {
        return Room.databaseBuilder(context, AppDatabase::class.java, "app.db")
            .fallbackToDestructiveMigration()
            .build()
    }
}

@InstallIn(ViewModelComponent::class)  // ViewModel scope
object CoroutineModule {
    @Provides
    @ViewModelScoped
    fun provideCoroutineDispatcher(): CoroutineDispatcher = Dispatchers.IO
}
```

---

## 7. Material 3 Theming

```kotlin
@Composable
fun MyAppTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    val colorScheme = when {
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            dynamicColorScheme(darkTheme)
        }
        darkTheme -> darkColorScheme()
        else -> lightColorScheme()
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = AppTypography,
        shapes = AppShapes,
        content = content,
    )
}

// Custom typography
val AppTypography = Typography(
    displayLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold,
        fontSize = 57.sp,
        lineHeight = 64.sp,
    ),
    headlineLarge = TextStyle(
        fontWeight = FontWeight.SemiBold,
        fontSize = 32.sp,
        lineHeight = 40.sp,
    ),
    titleLarge = TextStyle(
        fontWeight = FontWeight.Medium,
        fontSize = 22.sp,
        lineHeight = 28.sp,
    ),
    bodyLarge = TextStyle(
        fontWeight = FontWeight.Normal,
        fontSize = 16.sp,
        lineHeight = 24.sp,
    ),
    labelSmall = TextStyle(
        fontWeight = FontWeight.Medium,
        fontSize = 11.sp,
        lineHeight = 16.sp,
    ),
)

// Custom shapes
val AppShapes = Shapes(
    small = RoundedCornerShape(4.dp),
    medium = RoundedCornerShape(8.dp),
    large = RoundedCornerShape(16.dp),
)
```

---

## 8. Navigation Compose

```kotlin
@Composable
fun AppNavigation() {
    val navController = rememberNavController()

    NavHost(
        navController = navController,
        startDestination = "home",
    ) {
        composable("home") {
            HomeScreen(
                onNavigateToDetail = { userId ->
                    navController.navigate("detail/$userId")
                }
            )
        }

        composable(
            route = "detail/{userId}",
            arguments = listOf(navArgument("userId") { type = NavType.StringType }),
        ) { backStackEntry ->
            val userId = backStackEntry.arguments?.getString("userId") ?: return@composable
            DetailScreen(
                userId = userId,
                onNavigateBack = { navController.popBackStack() }
            )
        }

        // Nested navigation
        navigation(
            route = "settings",
            startDestination = "settings_main",
        ) {
            composable("settings_main") { SettingsScreen() }
            composable("settings_profile") { ProfileSettingsScreen() }
            composable("settings_notifications") { NotificationSettingsScreen() }
        }

        // Deep link
        composable(
            route = "profile/{userId}",
            deepLinks = listOf(
                navDeepLink { uriPattern = "myapp://profile/{userId}" }
            ),
        ) { ProfileScreen() }
    }
}
```

---

## 9. WorkManager

```kotlin
class SyncWorker(
    context: Context,
    workerParams: WorkerParameters,
) : CoroutineWorker(context, workerParams) {

    override suspend fun doWork(): Result {
        return try {
            val syncResult = syncRepository.syncAll()

            if (syncResult.hasConflicts) {
                Result.retry()  // Retry later
            } else {
                Result.success()
            }
        } catch (e: IOException) {
            if (runAttemptCount < 3) {
                Result.retry()
            } else {
                Result.failure()
            }
        }
    }

    override suspend fun getForegroundInfo(): ForegroundInfo {
        return ForegroundInfo(
            notificationId = 1,
            notification = createNotification("Syncing..."),
        )
    }
}

// Schedule
val constraints = Constraints.Builder()
    .setRequiredNetworkType(NetworkType.CONNECTED)
    .setRequiresBatteryNotLow(true)
    .setRequiresStorageNotLow(true)
    .build()

val syncRequest = PeriodicWorkRequestBuilder<SyncWorker>(6, TimeUnit.HOURS)
    .setConstraints(constraints)
    .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 10, TimeUnit.SECONDS)
    .addTag("sync")
    .build()

WorkManager.getInstance(context)
    .enqueueUniquePeriodicWork(
        "sync_work",
        ExistingPeriodicWorkPolicy.KEEP,
        syncRequest,
    )

// Observing
WorkManager.getInstance(context)
    .getWorkInfosByTagLiveData("sync")
    .observe(viewLifecycleOwner) { workInfos ->
        // Update UI based on work status
    }
```

---

## 10. Compose UI Testing

```kotlin
@Test
fun testUserGreeting() {
    composeTestRule.setContent {
        Greeting(name = "Tom")
    }
    composeTestRule.onNodeWithText("Hello, Tom!").assertIsDisplayed()
}

@Test
fun testButtonClick() {
    var clicked = false
    composeTestRule.setContent {
        Button(onClick = { clicked = true }) {
            Text("Submit")
        }
    }
    composeTestRule.onNodeWithText("Submit").performClick()
    assert(clicked)
}

@Test
fun testLazyListScrolling() {
    composeTestRule.setContent {
        LazyColumn {
            items(100) { i -> Text("Item $i") }
        }
    }
    composeTestRule.onNodeWithText("Item 50")
        .performScrollTo()
        .assertIsDisplayed()
}

@Test
fun testNavigation() {
    composeTestRule.setContent {
        AppNavigation()
    }
    composeTestRule.onNodeWithText("Home").assertIsDisplayed()
    composeTestRule.onNodeWithTag("settings_button").performClick()
    composeTestRule.onNodeWithText("Settings").assertIsDisplayed()
}
```

---

## 11. Performance Optimization

```kotlin
// 1. Lazy lists with keys
LazyColumn {
    items(items, key = { it.id }) { item ->  // Keys = stable recomposition
        UserRow(item)
    }
}

// 2. Stable annotations
@Stable
data class User(val id: String, val name: String, val avatarUrl: String)

// 3. Derived state
val filteredList by remember {
    derivedStateOf {
        allUsers.filter { it.name.contains(query, ignoreCase = true) }
    }
}

// 4. Avoid recomposition with remember
@Composable
fun ExpensiveCalculation(input: String): String {
    return remember(input) {
        computeExpensiveResult(input)
    }
}

// 5. Baseline Profiles (app/src/main/baseline-prof.txt)
// Include frequently used classes and methods
Hilt_MainActivity.class
Hilt_MainActivity#onCreate
HomeViewModel.class
HomeViewModel#loadUsers
```

---

## 12. Play Store Deployment

### Build Types

```kotlin
// build.gradle.kts
android {
    buildTypes {
        debug {
            isDebuggable = true
            applicationIdSuffix = ".debug"
            versionNameSuffix = "-debug"
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    signingConfigs {
        create("release") {
            storeFile = file("release.keystore")
            storePassword = System.getenv("KEYSTORE_PASSWORD")
            keyAlias = System.getenv("KEY_ALIAS")
            keyPassword = System.getenv("KEY_PASSWORD")
        }
    }
}
```

### App Bundle

```diff
- APK: android.applicationVariants.configureEach { ... }
+ AAB: Android App Bundle (preferred)
```

### Play Console Checklist

- [ ] App icon (512×512, adaptive icon)
- [ ] Feature graphic (1024×500)
- [ ] Screenshots (phone + tablet + 7" + 10")
- [ ] Privacy policy URL
- [ ] Content rating questionnaire
- [ ] App pricing and distribution
- [ ] In-app products (if any)
- [ ] Crash reporting set up (Firebase)
- [ ] ProGuard/R8 rules optimized
- [ ] App signing key saved securely
