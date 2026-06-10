# macOS Development — Comprehensive Skill Guide

## Table of Contents
1. SwiftUI for macOS (NSViewRepresentable, AppKit Integration)
2. AppKit Essentials (Windows, Panels, Menus, Toolbars)
3. Menu Bar Apps (NSStatusBar, NSMenu)
4. Spotlight Integration (Core Spotlight)
5. File System Access (Sandboxed vs Non-Sandboxed)
6. AppleScript Automation
7. Shortcuts Integration
8. Core ML for Local AI
9. Metal Performance Shaders
10. Notarization and Distribution
11. DMG Packaging

---

## 1. SwiftUI for macOS

### Platform-Specific Considerations

```swift
import SwiftUI

struct ContentView: View {
    @Environment(\.colorScheme) var colorScheme
    @State private var selection: String?
    @State private var columnVisibility = NavigationSplitViewVisibility.all

    var body: some View {
        NavigationSplitView(columnVisibility: $columnVisibility) {
            // Sidebar
            List(Data.sidebarItems, id: \.self, selection: $selection) { item in
                Label(item.name, systemImage: item.icon)
            }
            .listStyle(SidebarListStyle())
            .navigationSplitViewColumnWidth(min: 180, ideal: 200, max: 300)
        } content: {
            // Content (middle column)
            if let selection {
                ContentListView(category: selection)
            }
        } detail: {
            // Detail (right column)
            Text("Select an item")
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button(action: toggleSidebar) {
                    Label("Toggle Sidebar", systemImage: "sidebar.left")
                }
            }

            ToolbarItem(placement: .automatic) {
                SearchField()
            }
        }
        .touchBar {
            // Touch Bar support
            Button("Save", action: save)
            Button("Print", action: print)
        }
        .onCommand(#selector(NSStandardKeyBindingResponding.selectAll(_:))) {
            // Keyboard shortcut handling
        }
    }

    @objc private func toggleSidebar() {
        NSApp.keyWindow?.firstResponder?
            .tryToPerform(#selector(NSSplitViewController.toggleSidebar(_:)), with: nil)
    }
}

// TouchBar customization
extension NSTouchBarItem.Identifier {
    static let save = NSTouchBarItem.Identifier("com.example.save")
}
```

### NSViewRepresentable

```swift
import SwiftUI
import WebKit

struct WebView: NSViewRepresentable {
    let url: URL

    func makeNSView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.preferences.setValue(true, forKey: "developerExtrasEnabled")

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        return webView
    }

    func updateNSView(_ nsView: WKWebView, context: Context) {
        let request = URLRequest(url: url)
        nsView.load(request)
    }

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    class Coordinator: NSObject, WKNavigationDelegate {
        func webView(_ webView: WKWebView,
                     didFinish navigation: WKNavigation!) {
            webView.evaluateJavaScript("document.title") { result, error in
                if let title = result as? String {
                    print("Page title: \(title)")
                }
            }
        }
    }
}
```

### AppKit Integration Points

```swift
// Accessing AppKit from SwiftUI
struct WindowAccessor: NSViewRepresentable {
    @Binding var window: NSWindow?

    func makeNSView(context: Context) -> NSView {
        let view = NSView()
        DispatchQueue.main.async {
            self.window = view.window
        }
        return view
    }

    func updateNSView(_ nsView: NSView, context: Context) {}
}

// Usage
struct MyView: View {
    @State private var window: NSWindow?

    var body: some View {
        Text("Hello")
            .background(WindowAccessor(window: $window))
            .onAppear {
                window?.title = "Custom Window Title"
                window?.titlebarAppearsTransparent = true
                window?.styleMask.insert(.fullSizeContentView)
            }
    }
}
```

---

## 2. AppKit Essentials

### Windows & Panels

```swift
import AppKit

class MainWindowController: NSWindowController {
    convenience init() {
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1200, height: 800),
            styleMask: [.titled, .closable, .miniaturizable,
                       .resizable, .fullSizeContentView],
            backing: .buffered,
            defer: false
        )
        window.title = "My App"
        window.titlebarAppearsTransparent = true
        window.isMovableByWindowBackground = true
        window.center()

        self.init(window: window)
        self.contentViewController = MainViewController()
    }
}

// Custom panel
class InspectorPanel: NSPanel {
    init() {
        super.init(
            contentRect: NSRect(x: 0, y: 0, width: 300, height: 600),
            styleMask: [.titled, .closable, .resizable, .utilityWindow],
            backing: .buffered,
            defer: false
        )
        self.title = "Inspector"
        self.isFloatingPanel = true
        self.becomesKeyOnlyIfNeeded = true
        self.hidesOnDeactivate = false
    }
}
```

### Menus

```swift
// Main menu setup
@main
struct MyApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .commands {
            // Application menu
            CommandGroup(after: .appInfo) {
                Button("Check for Updates...") {
                    checkForUpdates()
                }
            }

            // File menu
            CommandGroup(replacing: .newItem) {
                Button("New Document") {
                    createDocument()
                }
                .keyboardShortcut("n", modifiers: .command)

                Button("New Window") {
                    createWindow()
                }
                .keyboardShortcut("n", modifiers: [.command, .shift])
            }

            // Custom menu
            CommandMenu("Tools") {
                Button("Analyze") {
                    analyze()
                }
                .keyboardShortcut("a", modifiers: [.command, .shift])

                Divider()

                Menu("Export") {
                    Button("As PDF") { exportPDF() }
                    Button("As CSV") { exportCSV() }
                }
            }

            // Sidebar
            SidebarCommands()
        }

        // Settings window
        Settings {
            SettingsView()
        }
    }
}

// Contextual menu
extension NSView {
    func setupContextMenu() {
        let menu = NSMenu()
        menu.addItem(NSMenuItem(title: "Copy", action: #selector(copy), keyEquivalent: "c"))
        menu.addItem(NSMenuItem(title: "Paste", action: #selector(paste), keyEquivalent: "v"))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Delete", action: #selector(delete), keyEquivalent: ""))
        self.menu = menu
    }
}
```

### Toolbars

```swift
// NSToolbar integration
class MainViewController: NSViewController, NSToolbarDelegate {
    override func viewDidLoad() {
        super.viewDidLoad()
        setupToolbar()
    }

    private func setupToolbar() {
        let toolbar = NSToolbar(identifier: "main-toolbar")
        toolbar.delegate = self
        toolbar.allowsUserCustomization = true
        toolbar.autosavesConfiguration = true
        toolbar.displayMode = .iconAndLabel
        view.window?.toolbar = toolbar
    }

    func toolbarAllowedItemIdentifiers(_ toolbar: NSToolbar) -> [NSToolbarItem.Identifier] {
        return [.toggleSidebar, .add, .remove, .flexibleSpace, .cloudSharing]
    }

    func toolbarDefaultItemIdentifiers(_ toolbar: NSToolbar) -> [NSToolbarItem.Identifier] {
        return [.toggleSidebar, .flexibleSpace, .add, .remove]
    }

    func toolbar(_ toolbar: NSToolbar,
                 itemForItemIdentifier itemIdentifier: NSToolbarItem.Identifier,
                 willBeInsertedIntoToolbar flag: Bool) -> NSToolbarItem? {
        let item = NSToolbarItem(itemIdentifier: itemIdentifier)
        item.label = "Custom"
        item.image = NSImage(systemSymbolName: "wand.and.stars", accessibilityDescription: nil)
        item.action = #selector(customAction)
        return item
    }
}
```

---

## 3. Menu Bar Apps

### NSStatusBar

```swift
import AppKit

class MenuBarController: NSObject {
    private var statusItem: NSStatusItem!
    private var popover: NSPopover!

    func setup() {
        // Create status item
        statusItem = NSStatusBar.system.statusItem(
            withLength: NSStatusItem.variableLength
        )

        if let button = statusItem.button {
            button.image = NSImage(systemSymbolName: "star.fill",
                                  accessibilityDescription: "App")
            button.action = #selector(togglePopover)
            button.target = self
        }

        // Create menu
        let menu = NSMenu()
        menu.addItem(NSMenuItem(title: "Open App", action: #selector(openApp), keyEquivalent: "o"))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Preferences...", action: #selector(openPreferences), keyEquivalent: ","))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Quit", action: #selector(NSApp.terminate), keyEquivalent: "q"))

        statusItem.menu = menu

        // Create popover (alternative to menu)
        popover = NSPopover()
        popover.contentViewController = PopoverViewController()
        popover.behavior = .transient
    }

    @objc private func togglePopover() {
        guard let button = statusItem.button else { return }

        if popover.isShown {
            popover.performClose(nil)
        } else {
            popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
            popover.contentViewController?.view.window?.becomeKey()
        }
    }

    @objc private func openApp() {
        NSApp.activate(ignoringOtherApps: true)
    }
}
```

### NSMenu Details

```swift
// Dynamic menu items
func updateMenu() {
    let menu = statusItem.menu!

    // Clear existing dynamic items
    while menu.items.count > 2 {
        menu.removeItem(at: 0)
    }

    // Add current items
    for item in currentItems {
        let menuItem = NSMenuItem(title: item.name,
                                 action: #selector(selectItem(_:)),
                                 keyEquivalent: "")
        menuItem.representedObject = item
        menuItem.state = item.isSelected ? .on : .off
        menu.insertItem(menuItem, at: 0)
    }
}

// Submenu
let submenu = NSMenu(title: "Recent Files")
submenu.addItem(NSMenuItem(title: "Document 1", action: nil, keyEquivalent: ""))
submenu.addItem(NSMenuItem(title: "Document 2", action: nil, keyEquivalent: ""))

let parentItem = NSMenuItem(title: "Open Recent", action: nil, keyEquivalent: "")
parentItem.submenu = submenu
```

---

## 4. Spotlight Integration

```swift
import CoreSpotlight
import MobileCoreServices

class SpotlightIndexer {
    static let domainIdentifier = "com.example.app.items"

    static func indexItem(_ item: IndexableItem) {
        let attributeSet = CSSearchableItemAttributeSet(
            contentType: UTType.data.identifier
        )
        attributeSet.title = item.title
        attributeSet.contentDescription = item.description
        attributeSet.keywords = item.keywords
        attributeSet.thumbnailData = item.thumbnailData
        attributeSet.contentCreationDate = item.createdAt

        let searchableItem = CSSearchableItem(
            uniqueIdentifier: item.id,
            domainIdentifier: domainIdentifier,
            attributeSet: attributeSet
        )
        searchableItem.expirationDate = .distantFuture

        CSSearchableIndex.default().indexSearchableItems([searchableItem]) { error in
            if let error = error {
                print("Indexing error: \(error)")
            }
        }
    }

    static func deleteAllItems() {
        CSSearchableIndex.default().deleteAllSearchableItems { error in
            if let error = error {
                print("Delete error: \(error)")
            }
        }
    }

    static func handleSpotlightOpen(_ userActivity: NSUserActivity) {
        guard userActivity.activityType == CSSearchableItemActionType,
              let identifier = userActivity.userInfo?[CSSearchableItemActivityIdentifier] as? String else {
            return
        }
        // Navigate to the item
        navigateToItem(id: identifier)
    }
}

// Handle in AppDelegate
func application(_ application: NSApplication,
                 continue userActivity: NSUserActivity,
                 restorationHandler: @escaping ([NSUserActivityRestoring]) -> Void) -> Bool {
    SpotlightIndexer.handleSpotlightOpen(userActivity)
    return true
}
```

---

## 5. File System Access

### Sandboxed App (App Store)

```swift
// Entitlements
// com.apple.security.app-sandbox = true
// com.apple.security.files.user-selected.read-write
// com.apple.security.files.downloads.read-write

// Document-scoped bookmarks for persistent access
class FileAccessManager {
    static func saveBookmark(for url: URL) throws -> Data {
        return try url.bookmarkData(
            options: .suitableForBookmarkFile,
            includingResourceValuesForKeys: nil,
            relativeTo: nil
        )
    }

    static func restoreURL(from bookmarkData: Data) -> URL? {
        var isStale = false
        return try? URL(
            resolvingBookmarkData: bookmarkData,
            options: .withoutUI,
            relativeTo: nil,
            bookmarkDataIsStale: &isStale
        )
    }
}

// Security-scoped access
func accessFile(at url: URL) throws {
    guard url.startAccessingSecurityScopedResource() else {
        throw FileError.accessDenied
    }
    defer { url.stopAccessingSecurityScopedResource() }

    let data = try Data(contentsOf: url)
}
```

### Non-Sandboxed App (Developer ID)

```swift
// Full file system access
func readPreferences() -> [String: Any]? {
    let path = "/Users/\(NSUserName())/Library/Preferences/com.example.app.plist"
    return NSDictionary(contentsOfFile: path) as? [String: Any]
}

// File monitoring with DispatchSource
class FileMonitor {
    private var source: DispatchSourceFileSystemObject?

    func monitor(file url: URL, handler: @escaping () -> Void) {
        let fd = open(url.path, O_EVTONLY)
        guard fd >= 0 else { return }

        source = DispatchSource.makeFileSystemObjectSource(
            fileDescriptor: fd,
            eventMask: [.write, .rename, .delete]
        )

        source?.setEventHandler(handler: handler)
        source?.setCancelHandler { close(fd) }
        source?.resume()
    }

    func stop() {
        source?.cancel()
        source = nil
    }
}
```

---

## 6. AppleScript Automation

```swift
import AppleScriptObjC

// Execute AppleScript
func runAppleScript(_ source: String) async throws -> String? {
    let script = NSAppleScript(source: source)!

    var error: NSDictionary?
    let result = script.executeAndReturnError(&error)

    if let error = error {
        throw ScriptError.executionFailed(error["NSAppleScriptErrorMessage"] as? String ?? "Unknown error")
    }

    return result.stringValue
}

// Register as scriptable application (sdef file)
// MyApp.sdef
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE dictionary SYSTEM "file://localhost/System/Library/DTDs/sdef.dtd">
<dictionary title="MyApp Terminology">
    <suite name="MyApp Suite" code="MyAp">
        <command name="create document" code="MyApCrDo" description="Create a new document">
            <cocoa class="MyApplication" method="handleCreateDocument:"/>
        </command>

        <class name="document" code="Docu" description="A document">
            <element type="document">
                <cocoa key="documents"/>
            </element>
            <property name="name" code="pNam" type="text" description="The document name">
                <cocoa key="name"/>
            </property>
        </class>
    </suite>
</dictionary>
```

---

## 7. Shortcuts Integration

```swift
import AppIntents

// Define an App Intent
struct CreateNoteIntent: AppIntent {
    static var title: LocalizedStringResource = "Create Note"
    static var description = IntentDescription("Creates a new note")

    @Parameter(title: "Title")
    var title: String

    @Parameter(title: "Content")
    var content: String?

    static var parameterSummary: some ParameterSummary {
        Summary("Create \(\.$title) note")
    }

    @MainActor
    func perform() async throws -> some IntentResult & ProvidesDialog {
        let note = Note(title: title, content: content ?? "")
        try await NoteManager.shared.save(note)

        return .result(dialog: "Created note: \(note.title)")
    }
}

// Shortcuts app integration
struct NoteShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: CreateNoteIntent(),
            phrases: [
                "Create a note with \(\.$title) in \(\.$appName)",
                "Make a new note called \(\.$title)",
            ],
            shortTitle: "Create Note",
            systemImageName: "note.text"
        )
    }
}
```

---

## 8. Core ML for Local AI

```swift
import CoreML

class LocalInference {
    private let model: MLModel?

    init(modelName: String) {
        guard let modelURL = Bundle.main.url(forResource: modelName,
                                              withExtension: "mlmodelc") else {
            self.model = nil
            return
        }
        self.model = try? MLModel(contentsOf: modelURL)
    }

    func predict(input: [String: Any]) -> [String: Any]? {
        guard let model = model else { return nil }

        let inputFeatures = try? MLMultiArray(shape: [1, 768], dataType: .float32)
        // Populate input features...

        let inputProvider = try? MLDictionaryFeatureProvider(dictionary: [
            "input": inputFeatures!
        ])

        guard let output = try? model.prediction(from: inputProvider!) else {
            return nil
        }

        return output.featureValue(for: "output")?.multiArrayValue?.toArray()
    }
}
```

---

## 9. Metal Performance Shaders

```swift
import MetalPerformanceShaders

class ImageProcessor {
    private let device: MTLDevice
    private let commandQueue: MTLCommandQueue

    init() {
        self.device = MTLCreateSystemDefaultDevice()!
        self.commandQueue = device.makeCommandQueue()!
    }

    func applyFilter(to texture: MTLTexture) -> MTLTexture {
        let descriptor = MTLTextureDescriptor.texture2DDescriptor(
            pixelFormat: texture.pixelFormat,
            width: texture.width,
            height: texture.height,
            mipmapped: false
        )
        descriptor.usage = [.shaderRead, .shaderWrite]

        let outputTexture = device.makeTexture(descriptor: descriptor)!

        let commandBuffer = commandQueue.makeCommandBuffer()!

        // Gaussian blur
        let blur = MPSImageGaussianBlur(device: device, sigma: 5.0)
        blur.encode(commandBuffer: commandBuffer,
                    sourceTexture: texture,
                    destinationTexture: outputTexture)

        commandBuffer.commit()
        commandBuffer.waitUntilCompleted()

        return outputTexture
    }
}
```

---

## 10. Notarization and Distribution

### Code Signing & Notarization

```bash
# Sign the app
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: Your Name (TEAMID)" \
  --options runtime \
  --entitlements entitlements.plist \
  MyApp.app

# Zip for notarization
ditto -c -k --sequesterRsrc --keepParent MyApp.app MyApp.zip

# Submit for notarization
xcrun notarytool submit MyApp.zip \
  --apple-id your@email.com \
  --team-id TEAMID \
  --password @keychain:NOTARY_PASSWORD \
  --wait

# Staple the ticket
xcrun stapler staple MyApp.app

# Verify
spctl -a -vvvv MyApp.app
```

### Developer ID vs Mac App Store

| Feature | Developer ID (Direct) | Mac App Store |
|---------|----------------------|---------------|
| Distribution | Anywhere | App Store only |
| Sandbox | Not required | Required |
| Review process | None (notarization only) | Full review |
| Updates | Self-managed | Automatic |
| Pricing | Any | Commission applies |
| Entitlements | Full access | Limited |
| Installation | Gatekeeper | One-click |

---

## 11. DMG Packaging

```bash
# Create DMG
create-dmg \
  --volname "MyApp" \
  --volicon "icon.icns" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "MyApp.app" 175 190 \
  --hide-extension "MyApp.app" \
  --app-drop-link 425 190 \
  --background "background.png" \
  --no-internet-enable \
  "MyApp-1.0.0.dmg" \
  "build/Release/MyApp.app"

# Alternative using hdiutil
hdiutil create -volname "MyApp" \
  -srcfolder "build/Release/MyApp.app" \
  -ov -format UDZO \
  -size 100m \
  "MyApp-1.0.0.dmg"
```

---

## Distribution Checklist

- [ ] App signed with Developer ID certificate
- [ ] Hardened Runtime enabled
- [ ] Notarization submitted and passed
- [ ] Stapled ticket attached
- [ ] DMG created with proper layout
- [ ] App icon (512×512, all sizes)
- [ ] `CFBundleVersion` and `CFBundleShortVersionString` set
- [ ] `LSMinimumSystemVersion` set correctly
- [ ] Sparkle or other update framework integrated
- [ ] Crash reporter configured
- [ ] Analytics integrated
- [ ] Help book included (optional)
