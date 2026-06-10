# iOS Development — Comprehensive Skill Guide

## Table of Contents
1. Swift Concurrency (async/await, Task, MainActor, AsyncSequence, AsyncStream)
2. SwiftUI (ViewBuilder, Property Wrappers, Preference System, Layout)
3. Combine Framework (Publishers, Subscribers, Subjects, Operators)
4. Core Data / SwiftData
5. URLSession + Codable
6. Keychain Integration
7. Core ML
8. Metal for GPU Compute
9. WidgetKit
10. App Clips
11. SiriKit
12. HealthKit
13. ARKit
14. TestFlight Distribution
15. App Store Connect

---

## 1. Swift Concurrency

### async/await

```swift
import SwiftUI

// Async function
func fetchUsers() async throws -> [User] {
    let url = URL(string: "https://api.example.com/users")!
    let (data, response) = try await URLSession.shared.data(from: url)

    guard let httpResponse = response as? HTTPURLResponse,
          httpResponse.statusCode == 200 else {
        throw APIError.invalidResponse
    }

    return try JSONDecoder().decode([User].self, from: data)
}

// Concurrent calls
func loadDashboard() async throws -> DashboardData {
    async let users = fetchUsers()
    async let posts = fetchPosts()
    async let metrics = fetchMetrics()

    return try await DashboardData(
        users: users,
        posts: posts,
        metrics: metrics
    )
}

// Task
Task {
    do {
        let users = try await fetchUsers()
        await MainActor.run { self.users = users }
    } catch {
        await MainActor.run { self.errorMessage = error.localizedDescription }
    }
}

// Task with priority
Task(priority: .userInitiated) {
    let result = await performCriticalOperation()
}

// TaskGroup for dynamic concurrency
func processAll(items: [Item]) async throws -> [ProcessedItem] {
    try await withThrowingTaskGroup(of: ProcessedItem.self) { group in
        for item in items {
            group.addTask {
                try await processItem(item)
            }
        }

        var results = [ProcessedItem]()
        for try await result in group {
            results.append(result)
        }
        return results
    }
}
```

### Actors

```swift
// Actor — protects mutable state
actor UserCache {
    private var cache: [String: User] = [:]
    private var lastAccessed: [String: Date] = [:]

    func getUser(id: String) -> User? {
        lastAccessed[id] = Date()
        return cache[id]
    }

    func setUser(_ user: User) {
        cache[user.id] = user
        lastAccessed[user.id] = Date()
    }

    func evictOlderThan(_ date: Date) {
        for (id, accessed) in lastAccessed where accessed < date {
            cache.removeValue(forKey: id)
            lastAccessed.removeValue(forKey: id)
        }
    }
}

// Usage
let cache = UserCache()
Task {
    await cache.setUser(user)
    let cached = await cache.getUser(id: "123")
}
```

### MainActor

```swift
@MainActor
class ViewModel: ObservableObject {
    @Published var users: [User] = []
    @Published var isLoading = false

    func loadUsers() async {
        isLoading = true
        defer { isLoading = false }

        do {
            let fetched = try await fetchUsers()
            users = fetched  // MainActor ensures UI update on main thread
        } catch {
            print("Error: \(error)")
        }
    }
}
```

### AsyncSequence & AsyncStream

```swift
// AsyncSequence
let notifications = NotificationCenter.default
    .notifications(named: .dataDidUpdate)
    .map { notification in
        notification.userInfo?["data"] as? Data
    }

for await data in notifications {
    processData(data)
}

// AsyncStream — custom async sequence
func produceEvents() -> AsyncStream<Event> {
    AsyncStream { continuation in
        let handler = EventHandler { event in
            continuation.yield(event)
            if event.isFinal {
                continuation.finish()
            }
        }
        startListening(handler)

        continuation.onTermination = { _ in
            stopListening()
        }
    }
}

for await event in produceEvents() {
    handleEvent(event)
}
```

---

## 2. SwiftUI

### ViewBuilder & Property Wrappers

```swift
struct ProfileView: View {
    // Property wrappers
    @State private var isEditing = false
    @StateObject private var viewModel = ProfileViewModel()
    @ObservedObject var externalModel: ExternalModel
    @EnvironmentObject var appState: AppState
    @Environment(\.colorScheme) var colorScheme
    @Environment(\.dismiss) var dismiss
    @AppStorage("username") var username = "Guest"
    @ScaledMetric private var avatarSize: CGFloat = 60
    @Binding var isPresented: Bool

    var body: some View {
        VStack(spacing: 16) {
            HeaderView()

            Group {
                if isEditing {
                    EditProfileView(viewModel: viewModel)
                } else {
                    ProfileContent(user: viewModel.user)
                }
            }
            .transition(.slide)
        }
        .padding()
        .background(colorScheme == .dark ? Color.black : Color.white)
        .task {
            await viewModel.loadProfile()
        }
    }

    @ViewBuilder
    private func HeaderView() -> some View {
        HStack {
            AsyncImage(url: viewModel.user.avatarURL) { phase in
                switch phase {
                case .success(let image):
                    image
                        .resizable()
                        .frame(width: avatarSize, height: avatarSize)
                        .clipShape(Circle())
                case .failure:
                    Image(systemName: "person.circle.fill")
                        .font(.system(size: avatarSize))
                case .empty:
                    ProgressView()
                @unknown default:
                    EmptyView()
                }
            }

            VStack(alignment: .leading) {
                Text(viewModel.user.name)
                    .font(.title2).bold()
                Text(viewModel.user.bio)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
        }
    }
}
```

### Preference System

```swift
// Custom preference key
struct ScrollOffsetPreference: PreferenceKey {
    static var defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = nextValue()
    }
}

// Reading preference
struct ScrollViewOffsetReader: View {
    var body: some View {
        GeometryReader { proxy in
            Color.clear
                .preference(
                    key: ScrollOffsetPreference.self,
                    value: proxy.frame(in: .named("scroll")).minY
                )
        }
        .frame(height: 0)
    }
}

// Using the preference
struct ParallaxHeader: View {
    @State private var scrollOffset: CGFloat = 0

    var body: some View {
        ScrollView {
            ScrollViewOffsetReader()
            VStack {
                // Content
            }
        }
        .coordinateSpace(name: "scroll")
        .onPreferenceChange(ScrollOffsetPreference.self) { offset in
            scrollOffset = offset
        }
    }
}
```

### Layout System

```swift
// Custom layout
struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(
        proposal: ProposedViewSize,
        subviews: Subviews,
        cache: inout Void
    ) -> CGSize {
        let sizes = subviews.map { $0.sizeThatFits(.unspecified) }
        var width: CGFloat = 0
        var height: CGFloat = 0
        var x: CGFloat = 0
        var y: CGFloat = 0

        for size in sizes {
            if x + size.width > (proposal.width ?? .infinity) {
                y += size.height + spacing
                x = 0
            }
            x += size.width + spacing
            width = max(width, x)
            height = max(height, y + size.height)
        }

        return CGSize(width: width, height: height)
    }

    func placeSubviews(
        in bounds: CGRect,
        proposal: ProposedViewSize,
        subviews: Subviews,
        cache: inout Void
    ) {
        let sizes = subviews.map { $0.sizeThatFits(.unspecified) }
        var x = bounds.minX
        var y = bounds.minY

        for (index, subview) in subviews.enumerated() {
            let size = sizes[index]
            if x + size.width > bounds.maxX {
                y += size.height + spacing
                x = bounds.minX
            }
            subview.place(at: CGPoint(x: x, y: y), proposal: .unspecified)
            x += size.width + spacing
        }
    }
}
```

---

## 3. Combine Framework

```swift
import Combine

class SearchViewModel: ObservableObject {
    @Published var searchQuery = ""
    @Published var results: [SearchResult] = []
    @Published var isSearching = false

    private var cancellables = Set<AnyCancellable>()

    init() {
        $searchQuery
            .debounce(for: .milliseconds(300), scheduler: DispatchQueue.main)
            .removeDuplicates()
            .filter { $0.count >= 2 }
            .flatMap { query -> AnyPublisher<[SearchResult], Never> in
                self.isSearching = true
                return self.searchAPI(query: query)
                    .catch { _ in Just([]) }
                    .eraseToAnyPublisher()
            }
            .receive(on: DispatchQueue.main)
            .sink { [weak self] results in
                self?.results = results
                self?.isSearching = false
            }
            .store(in: &cancellables)
    }

    private func searchAPI(query: String) -> AnyPublisher<[SearchResult], Error> {
        let url = URL(string: "https://api.example.com/search?q=\(query)")!
        return URLSession.shared.dataTaskPublisher(for: url)
            .map(\.data)
            .decode(type: [SearchResult].self, decoder: JSONDecoder())
            .eraseToAnyPublisher()
    }
}

// Subjects
let passthroughSubject = PassthroughSubject<String, Never>()
let currentValueSubject = CurrentValueSubject<Int, Int>(0)

// Custom publisher
extension NotificationCenter {
    var keyboardWillShowPublisher: AnyPublisher<CGFloat, Never> {
        publishers(for: UIResponder.keyboardWillShowNotification)
            .map { notification in
                (notification.userInfo?[UIResponder.keyboardFrameEndUserInfoKey]
                    as? CGRect)?.height ?? 0
            }
            .eraseToAnyPublisher()
    }
}
```

---

## 4. Core Data / SwiftData

### SwiftData (iOS 17+)

```swift
import SwiftData

@Model
final class User {
    var name: String
    var email: String
    @Attribute(.unique) var id: String
    @Relationship(inverse: \Post.author) var posts: [Post]
    @Attribute(.externalStorage) var avatarData: Data?

    init(name: String, email: String) {
        self.name = name
        self.email = email
        self.id = UUID().uuidString
        self.posts = []
    }
}

@Model
final class Post {
    var title: String
    var content: String
    var createdAt: Date
    var author: User?

    init(title: String, content: String, author: User?) {
        self.title = title
        self.content = content
        self.createdAt = Date()
        self.author = author
    }
}

// Usage in SwiftUI
struct ContentView: View {
    @Environment(\.modelContext) private var modelContext
    @Query(sort: \User.name, order: .forward) private var users: [User]

    var body: some View {
        List(users) { user in
            Text(user.name)
        }
        .toolbar {
            Button("Add") {
                let user = User(name: "New", email: "new@example.com")
                modelContext.insert(user)
            }
        }
    }
}
```

---

## 5. URLSession + Codable

```swift
// Network layer
protocol APIClient {
    func request<T: Decodable>(_ endpoint: Endpoint) async throws -> T
}

final class NetworkClient: APIClient {
    private let session: URLSession
    private let decoder: JSONDecoder

    init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.waitsForConnectivity = true
        self.session = URLSession(configuration: config)
        self.decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601
    }

    func request<T: Decodable>(_ endpoint: Endpoint) async throws -> T {
        var request = URLRequest(url: endpoint.url)
        request.httpMethod = endpoint.method.rawValue
        request.allHTTPHeaderFields = endpoint.headers
        request.httpBody = endpoint.body

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw NetworkError.invalidResponse
        }

        switch httpResponse.statusCode {
        case 200...299:
            return try decoder.decode(T.self, from: data)
        case 401:
            throw NetworkError.unauthorized
        case 429:
            throw NetworkError.rateLimited
        default:
            throw NetworkError.serverError(httpResponse.statusCode)
        }
    }
}

// Endpoint definition
struct Endpoint {
    let path: String
    let method: HTTPMethod
    let queryItems: [URLQueryItem]?
    let headers: [String: String]?
    let body: Data?

    var url: URL {
        var components = URLComponents(string: "https://api.example.com")!
        components.path = path
        components.queryItems = queryItems
        return components.url!
    }
}
```

---

## 6. Keychain Integration

```swift
import Security

final class KeychainManager {
    static let shared = KeychainManager()

    func save(key: String, data: Data) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
        ]

        SecItemDelete(query as CFDictionary)
        let status = SecItemAdd(query as CFDictionary, nil)

        guard status == errSecSuccess else {
            throw KeychainError.saveFailed(status)
        }
    }

    func read(key: String) throws -> Data {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess, let data = result as? Data else {
            throw KeychainError.readFailed(status)
        }

        return data
    }

    func delete(key: String) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
        ]

        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainError.deleteFailed(status)
        }
    }
}
```

---

## 7. Core ML

```swift
import CoreML
import Vision

// Image classification
func classifyImage(_ image: UIImage) async throws -> String {
    guard let ciImage = CIImage(image: image) else {
        throw MLError.invalidImage
    }

    let config = MLModelConfiguration()
    let model = try VNCoreMLModel(for: MobileNetV2(configuration: config).model)

    let request = VNCoreMLRequest(model: model)
    request.imageCropAndScaleOption = .centerCrop

    let handler = VNImageRequestHandler(ciImage: ciImage)
    try handler.perform([request])

    guard let results = request.results as? [VNClassificationObservation],
          let topResult = results.first else {
        throw MLError.noResults
    }

    return topResult.identifier
}

// Natural language
import NaturalLanguage

let tagger = NLTagger(tagSchemes: [.nameType])
tagger.string = "Tim Cook visited Apple Park"
tagger.enumerateTags(in: text.startIndex..<text.endIndex,
                     unit: .word,
                     scheme: .nameType) { tag, range in
    print("\(text[range]): \(tag?.rawValue ?? "none")")
    return true
}
```

---

## 8. Metal GPU Compute

```swift
import Metal

class GPULibrary {
    private let device: MTLDevice
    private let commandQueue: MTLCommandQueue

    init?() {
        guard let device = MTLCreateSystemDefaultDevice(),
              let commandQueue = device.makeCommandQueue() else {
            return nil
        }
        self.device = device
        self.commandQueue = commandQueue
    }

    func performCompute(data: [Float]) -> [Float] {
        let buffer = device.makeBuffer(
            bytes: data,
            length: data.count * MemoryLayout<Float>.stride,
            options: .storageModeShared
        )

        let library = device.makeDefaultLibrary()
        let function = library?.makeFunction(name: "compute_kernel")
        let pipeline = try? device.makeComputePipelineState(function: function!)

        let commandBuffer = commandQueue.makeCommandBuffer()
        let encoder = commandBuffer?.makeComputeCommandEncoder()

        encoder?.setBuffer(buffer, offset: 0, index: 0)
        // Configure threadgroups and dispatch
        encoder?.endEncoding()
        commandBuffer?.commit()
        commandBuffer?.waitUntilCompleted()

        return Array(UnsafeBufferPointer(
            start: buffer?.contents().assumingMemoryBound(to: Float.self),
            count: data.count
        ))
    }
}
```

---

## 9. WidgetKit

```swift
import WidgetKit
import SwiftUI

struct Provider: TimelineProvider {
    func placeholder(in context: Context) -> SimpleEntry {
        SimpleEntry(date: Date(), taskCount: 5)
    }

    func getSnapshot(in context: Context, completion: @escaping (SimpleEntry) -> Void) {
        let entry = SimpleEntry(date: Date(), taskCount: 5)
        completion(entry)
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<SimpleEntry>) -> Void) {
        let currentDate = Date()
        let entry = SimpleEntry(date: currentDate, taskCount: TaskManager.shared.count)
        let nextUpdate = Calendar.current.date(byAdding: .hour, value: 1, to: currentDate)!
        let timeline = Timeline(entries: [entry], policy: .after(nextUpdate))
        completion(timeline)
    }
}

struct SimpleEntry: TimelineEntry {
    let date: Date
    let taskCount: Int
}

struct WidgetEntryView: View {
    var entry: Provider.Entry

    var body: some View {
        VStack {
            Text("Tasks: \(entry.taskCount)")
                .font(.headline)
            Text(entry.date, style: .time)
                .font(.caption)
        }
        .containerBackground(.fill.tertiary, for: .widget)
    }
}

struct TaskWidget: Widget {
    let kind: String = "com.example.TaskWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: Provider()) { entry in
            WidgetEntryView(entry: entry)
        }
        .configurationDisplayName("Task Count")
        .description("Shows the number of pending tasks")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}
```

---

## 10. App Clips

```swift
import AppClip

// Invocation
// <meta name="apple-itunes-app" content="app-clip-bundle-id=com.example.Clip">
// Universal link: https://example.com/order?id=123

// App Clip experience
struct OrderAppClip: App {
    var body: some Scene {
        WindowGroup {
            NavigationView {
                OrderDetailView()
            }
            .onContinueUserActivity(NSUserActivityTypeBrowsingWeb) { activity in
                // Handle the URL from the App Clip invocation
                guard let url = activity.webpageURL else { return }
                handleAppClipInvocation(url)
            }
        }
    }

    private func handleAppClipInvocation(_ url: URL) {
        let components = URLComponents(url: url, resolvingAgainstBaseURL: true)
        if let orderId = components?.queryItems?.first(where: { $0.name == "id" })?.value {
            // Load the order
            loadOrder(orderId)
        }
    }
}
```

---

## 11. SiriKit

```swift
import Intents

// Define an intent
class OrderStatusIntentHandler: NSObject, OrderStatusIntentHandling {
    func handle(intent: OrderStatusIntent,
                completion: @escaping (OrderStatusIntentResponse) -> Void) {
        let orderID = intent.orderID ?? ""
        // Fetch order status
        completion(OrderStatusIntentResponse.success(orderStatus: "Shipped"))
    }
}

// Register in AppDelegate
func application(_ application: UIApplication,
                 didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
    INPreferences.requestSiriAuthorization { status in }
    return true
}
```

---

## 12. HealthKit

```swift
import HealthKit

class HealthManager {
    let healthStore = HKHealthStore()

    func requestAuthorization() async throws {
        let typesToRead: Set = [
            HKObjectType.quantityType(forIdentifier: .stepCount)!,
            HKObjectType.quantityType(forIdentifier: .heartRate)!,
            HKObjectType.quantityType(forIdentifier: .activeEnergyBurned)!,
        ]
        let typesToWrite: Set = [
            HKObjectType.quantityType(forIdentifier: .stepCount)!,
        ]

        try await healthStore.requestAuthorization(
            toShare: typesToWrite,
            read: typesToRead
        )
    }

    func fetchSteps() async throws -> Double {
        let type = HKQuantityType(.stepCount)
        let predicate = HKQuery.predicateForSamples(
            withStart: Calendar.current.startOfDay(for: Date()),
            end: Date()
        )

        let result = try await withCheckedThrowingContinuation {
            (continuation: CheckedContinuation<Double, Error>) in

            let query = HKStatisticsQuery(
                quantityType: type,
                quantitySamplePredicate: predicate,
                options: .cumulativeSum
            ) { _, statistics, error in
                if let error = error {
                    continuation.resume(throwing: error)
                    return
                }
                let value = statistics?.sumQuantity()?.doubleValue(for: .count()) ?? 0
                continuation.resume(returning: value)
            }
            healthStore.execute(query)
        }

        return result
    }
}
```

---

## 13. ARKit

```swift
import ARKit
import RealityKit

struct ARContentView: View {
    var body: some View {
        ARViewContainer()
            .edgesIgnoringSafeArea(.all)
    }
}

struct ARViewContainer: UIViewRepresentable {
    func makeUIView(context: Context) -> ARView {
        let arView = ARView(frame: .zero)

        // Configure AR session
        let config = ARWorldTrackingConfiguration()
        config.planeDetection = [.horizontal, .vertical]
        config.environmentTexturing = .automatic

        arView.session.run(config)
        arView.debugOptions = [.showFeaturePoints]

        // Add a box
        let box = ModelEntity(mesh: .generateBox(size: 0.1),
                             materials: [SimpleMaterial(color: .blue, isMetallic: false)])
        let anchor = AnchorEntity(plane: .horizontal)
        anchor.addChild(box)
        arView.scene.anchors.append(anchor)

        return arView
    }

    func updateUIView(_ uiView: ARView, context: Context) {}
}
```

---

## 14. TestFlight Distribution

1. Archive in Xcode (Product → Archive)
2. Upload to App Store Connect (Distribute App → App Store Connect)
3. Add testers in App Store Connect → TestFlight
4. Manage build groups and internal/external testing
5. Collect crash reports and feedback

**TestFlight Checklist:**
- [ ] Beta app review completed (external testing)
- [ ] Export Compliance answered
- [ ] App icon and screenshots for beta
- [ ] Test information filled in (what to test)
- [ ] Crash logs symbolicated
- [ ] Feedback mechanism in app

---

## 15. App Store Connect

### Distribution Checklist

- [ ] App Store icon (1024×1024, no transparency)
- [ ] Screenshots for all required devices
- [ ] App preview video (30s max, optional)
- [ ] Description (4000 chars max)
- [ ] Keywords (100 chars max)
- [ ] Support URL
- [ ] Marketing URL (optional)
- [ ] Privacy policy URL
- [ ] App review information (login, notes)
- [ ] Content rights (if applicable)
- [ ] Export compliance (ITAR, encryption)
- [ ] Age rating
- [ ] Pricing and availability
- [ ] In-app purchases configured (if any)

### Version Submission

```xml
<!-- Info.plist keys -->
<key>ITSAppUsesNonExemptEncryption</key>
<false/>
<key>UIRequiredDeviceCapabilities</key>
<array>
    <string>arm64</string>
</array>
<key>LSApplicationCategoryType</key>
<string>public.app-category.developer-tools</string>
```
