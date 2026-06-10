# Windows Development — Comprehensive Skill Guide

## Table of Contents
1. C# / .NET 8+ (Top-Level Statements, Record Types, Source Generators, AOT)
2. WinUI 3 (XAML, Data Binding, MVVM with CommunityToolkit)
3. WPF (XAML, Data Templates, Triggers, Behaviors)
4. .NET MAUI (Cross-Platform Desktop)
5. Win32 API via P/Invoke
6. DirectX 12
7. MSIX Packaging
8. Windows Installer
9. Auto-Update (Squirrel, WinSparkle)
10. COM Interop
11. Windows Services
12. UWP vs Win32 vs PWA

---

## 1. C# / .NET 8+

### Modern C# Features

```csharp
// Top-level statements (Program.cs)
using System.Text.Json;
using Microsoft.Extensions.DependencyInjection;

var builder = Host.CreateApplicationBuilder(args);
builder.Services.AddSingleton<IDataService, DataService>();
var app = builder.Build();

var service = app.Services.GetRequiredService<IDataService>();
await service.ProcessAsync();

Console.WriteLine("Done!");

// Record types (immutable value objects)
public record User(
    string Id,
    string Name,
    string Email,
    DateTime CreatedAt
);

// Record struct
public readonly record struct Point(int X, int Y);

// Record with validation
public record Temperature
{
    public double Celsius { get; init; }
    public double Fahrenheit => Celsius * 1.8 + 32;

    public Temperature(double celsius)
    {
        ArgumentOutOfRangeException.ThrowIfLessThan(celsius, -273.15);
        Celsius = celsius;
    }
}

// Primary constructors
public class ApiClient(HttpClient httpClient, string baseUrl)
{
    public async Task<T> GetAsync<T>(string endpoint)
    {
        var response = await httpClient.GetAsync($"{baseUrl}/{endpoint}");
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<T>();
    }
}

// Source generators
// [GeneratedRegex] — compile-time regex
[GeneratedRegex(@"^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$")]
private static partial Regex EmailRegex();

// [LibraryImport] — AOT-compatible P/Invoke
[LibraryImport("user32.dll", SetLastError = true)]
private static partial int MessageBoxW(
    IntPtr hWnd, string text, string caption, uint type);

// Required members
public class Configuration
{
    public required string ApiKey { get; init; }
    public required Uri BaseUrl { get; init; }
    public int TimeoutSeconds { get; init; } = 30;
}

// Collection expressions
List<int> numbers = [1, 2, 3, 4, 5];
int[] array = [.. numbers, 6, 7, 8];
Dictionary<string, int> map = ["one" => 1, "two" => 2];
```

### AOT Compilation

```xml
<!-- .csproj -->
<PropertyGroup>
  <PublishAot>true</PublishAot>
  <StripSymbols>true</StripSymbols>
  <OptimizationPreferSize>true</OptimizationPreferSize>
  <IlcOptimizationPreferSize>true</IlcOptimizationPreferSize>
</PropertyGroup>
```

---

## 2. WinUI 3

### XAML & Code-Behind

```xml
<!-- MainPage.xaml -->
<Page x:Class="MyApp.MainPage"
      xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
      xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
      xmlns:controls="using:Microsoft.UI.Xaml.Controls">

    <Grid>
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="*"/>
        </Grid.RowDefinitions>

        <!-- NavigationView -->
        <NavigationView x:Name="NavView"
                        Grid.RowSpan="2"
                        PaneDisplayMode="LeftCompact"
                        ItemInvoked="OnNavItemInvoked">
            <NavigationView.MenuItems>
                <NavigationViewItem Icon="Home" Content="Home" Tag="home"/>
                <NavigationViewItem Icon="People" Content="Users" Tag="users"/>
                <NavigationViewItem Icon="Setting" Content="Settings" Tag="settings"/>
            </NavigationView.MenuItems>

            <ScrollViewer>
                <Frame x:Name="ContentFrame"/>
            </ScrollViewer>
        </NavigationView>
    </Grid>
</Page>
```

```csharp
// MainPage.xaml.cs
public sealed partial class MainPage : Page
{
    public MainPage()
    {
        this.InitializeComponent();
        ContentFrame.Navigate(typeof(HomePage));
    }

    private void OnNavItemInvoked(NavigationView sender,
                                  NavigationViewItemInvokedEventArgs args)
    {
        if (args.InvokedItemContainer?.Tag is string tag)
        {
            ContentFrame.Navigate(tag switch
            {
                "home" => typeof(HomePage),
                "users" => typeof(UsersPage),
                "settings" => typeof(SettingsPage),
                _ => typeof(HomePage)
            });
        }
    }
}
```

### MVVM with CommunityToolkit

```csharp
// ViewModel
public partial class UsersViewModel : ObservableObject
{
    private readonly IUserService _userService;

    [ObservableProperty]
    private bool _isLoading;

    [ObservableProperty]
    private string? _searchQuery;

    public ObservableCollection<User> Users { get; } = new();

    public UsersViewModel(IUserService userService)
    {
        _userService = userService;
    }

    [RelayCommand]
    private async Task LoadUsersAsync()
    {
        IsLoading = true;
        try
        {
            var users = await _userService.GetUsersAsync();
            Users.Clear();
            foreach (var user in users)
            {
                Users.Add(user);
            }
        }
        finally
        {
            IsLoading = false;
        }
    }

    [RelayCommand]
    private async Task SearchAsync()
    {
        if (string.IsNullOrWhiteSpace(SearchQuery)) return;

        IsLoading = true;
        try
        {
            var results = await _userService.SearchAsync(SearchQuery);
            Users.Clear();
            foreach (var user in results)
            {
                Users.Add(user);
            }
        }
        finally
        {
            IsLoading = false;
        }
    }

    partial void OnSearchQueryChanged(string value)
    {
        _ = SearchAsync();
    }
}

// XAML binding
<Page x:Class="MyApp.Views.UsersPage"
      xmlns:vm="using:MyApp.ViewModels">
    <Page.DataContext>
        <vm:UsersViewModel/>
    </Page.DataContext>

    <Grid>
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="*"/>
        </Grid.RowDefinitions>

        <TextBox Text="{x:Bind ViewModel.SearchQuery, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
                 PlaceholderText="Search users..."/>

        <ListView Grid.Row="1"
                  ItemsSource="{x:Bind ViewModel.Users, Mode=OneWay}"
                  SelectedItem="{x:Bind ViewModel.SelectedUser, Mode=TwoWay}">
            <ListView.ItemTemplate>
                <DataTemplate>
                    <StackPanel>
                        <TextBlock Text="{Binding Name}" FontWeight="Bold"/>
                        <TextBlock Text="{Binding Email}" Foreground="Gray"/>
                    </StackPanel>
                </DataTemplate>
            </ListView.ItemTemplate>
        </ListView>

        <Button Command="{x:Bind ViewModel.LoadUsersCommand}"
                Content="Load"/>
    </Grid>
</Page>
```

---

## 3. WPF

### XAML Features

```xml
<Window x:Class="MyWpfApp.MainWindow"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        xmlns:local="clr-namespace:MyWpfApp"
        Title="My WPF App" Height="600" Width="800">

    <Window.Resources>
        <!-- Data Templates -->
        <DataTemplate x:Key="UserTemplate">
            <Border BorderBrush="Gray" BorderThickness="1" CornerRadius="4" Padding="8">
                <StackPanel>
                    <TextBlock Text="{Binding Name}" FontSize="16" FontWeight="Bold"/>
                    <TextBlock Text="{Binding Email}" Foreground="Gray"/>
                    <TextBlock Text="{Binding Role, StringFormat='Role: {0}'}"/>
                </StackPanel>
            </Border>
        </DataTemplate>

        <!-- Converters -->
        <local:BoolToVisibilityConverter x:Key="BoolToVis"/>
        <local:StatusToColorConverter x:Key="StatusToColor"/>

        <!-- Styles -->
        <Style x:Key="PrimaryButton" TargetType="Button">
            <Setter Property="Background" Value="#0078D4"/>
            <Setter Property="Foreground" Value="White"/>
            <Setter Property="Padding" Value="12,8"/>
            <Setter Property="FontSize" Value="14"/>
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="Button">
                        <Border Background="{TemplateBinding Background}"
                                CornerRadius="4">
                            <ContentPresenter HorizontalAlignment="Center"
                                              VerticalAlignment="Center"/>
                        </Border>
                        <ControlTemplate.Triggers>
                            <Trigger Property="IsMouseOver" Value="True">
                                <Setter Property="Background" Value="#106EBE"/>
                            </Trigger>
                            <Trigger Property="IsPressed" Value="True">
                                <Setter Property="Background" Value="#005A9E"/>
                            </Trigger>
                        </ControlTemplate.Triggers>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>

        <!-- Data Triggers -->
        <Style TargetType="TextBlock">
            <Style.Triggers>
                <DataTrigger Binding="{Binding Status}" Value="Error">
                    <Setter Property="Foreground" Value="Red"/>
                    <Setter Property="FontWeight" Value="Bold"/>
                </DataTrigger>
                <DataTrigger Binding="{Binding Status}" Value="Success">
                    <Setter Property="Foreground" Value="Green"/>
                </DataTrigger>
            </Style.Triggers>
        </Style>
    </Window.Resources>

    <Grid>
        <Grid.ColumnDefinitions>
            <ColumnDefinition Width="250"/>
            <ColumnDefinition Width="*"/>
        </Grid.ColumnDefinitions>

        <!-- User List -->
        <ListBox ItemsSource="{Binding Users}"
                 ItemTemplate="{StaticResource UserTemplate}"
                 SelectedItem="{Binding SelectedUser}"/>

        <!-- Detail Panel -->
        <StackPanel Grid.Column="1" Margin="16"
                    DataContext="{Binding SelectedUser}"
                    Visibility="{Binding IsSelected, Converter={StaticResource BoolToVis}}">
            <TextBlock Text="{Binding Name}" FontSize="24"/>
            <TextBlock Text="{Binding Email}" Margin="0,8,0,0"/>
            <TextBlock Text="{Binding Status}"
                       Foreground="{Binding Status, Converter={StaticResource StatusToColor}}"
                       FontSize="18" Margin="0,16,0,0"/>
        </StackPanel>
    </Grid>
</Window>
```

### Behaviors

```csharp
// Attached behavior
public static class DragBehavior
{
    public static readonly DependencyProperty IsDraggableProperty =
        DependencyProperty.RegisterAttached(
            "IsDraggable",
            typeof(bool),
            typeof(DragBehavior),
            new PropertyMetadata(false, OnIsDraggableChanged));

    public static void SetIsDraggable(UIElement element, bool value)
        => element.SetValue(IsDraggableProperty, value);

    public static bool GetIsDraggable(UIElement element)
        => (bool)element.GetValue(IsDraggableProperty);

    private static void OnIsDraggableChanged(DependencyObject d,
                                              DependencyPropertyChangedEventArgs e)
    {
        if (d is Window window && (bool)e.NewValue)
        {
            window.MouseDown += (s, args) =>
            {
                if (args.LeftButton == MouseButtonState.Pressed)
                    window.DragMove();
            };
        }
    }
}

// Usage: <Window local:DragBehavior.IsDraggable="True"/>
```

---

## 4. .NET MAUI (Cross-Platform Desktop)

```xml
<!-- MainPage.xaml -->
<ContentPage xmlns="http://schemas.microsoft.com/dotnet/2021/maui"
             xmlns:x="http://schemas.microsoft.com/winfx/2009/xaml"
             x:Class="MyMauiApp.MainPage">

    <Grid RowDefinitions="Auto,*,Auto"
          Padding="20" RowSpacing="16">

        <SearchBar x:Name="SearchBar"
                   Placeholder="Search..."
                   TextChanged="OnSearchTextChanged"/>

        <CollectionView Grid.Row="1"
                        ItemsSource="{Binding FilteredItems}">
            <CollectionView.ItemTemplate>
                <DataTemplate>
                    <Frame Margin="0,4" Padding="12" CornerRadius="8"
                           BorderColor="LightGray">
                        <Grid ColumnDefinitions="*,Auto">
                            <StackPanel>
                                <Label Text="{Binding Name}" FontSize="16"/>
                                <Label Text="{Binding Description}"
                                       FontSize="13" TextColor="Gray"/>
                            </StackPanel>
                            <Button Grid.Column="1"
                                    Text="Detail"
                                    Command="{Binding Source={RelativeSource AncestorType={x:Type ContentPage}}, Path=BindingContext.DetailCommand}"
                                    CommandParameter="{Binding .}"/>
                        </Grid>
                    </Frame>
                </DataTemplate>
            </CollectionView.ItemTemplate>
        </CollectionView>

        <ActivityIndicator Grid.Row="1"
                           IsRunning="{Binding IsLoading}"
                           IsVisible="{Binding IsLoading}"/>

        <Button Grid.Row="2"
                Text="Add New Item"
                Command="{Binding AddCommand}"
                BackgroundColor="{StaticResource Primary}"
                TextColor="White"
                CornerRadius="8"/>
    </Grid>
</ContentPage>
```

---

## 5. Win32 API via P/Invoke

```csharp
using System.Runtime.InteropServices;

public static class NativeMethods
{
    // Windows API declarations
    [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern IntPtr FindWindow(string className, string windowName);

    [DllImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern IntPtr GetConsoleWindow();

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool AllocConsole();

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool FreeConsole();

    [DllImport("shell32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern IntPtr ShellExecute(
        IntPtr hwnd,
        string lpOperation,
        string lpFile,
        string lpParameters,
        string lpDirectory,
        int nShowCmd
    );

    public const int SW_HIDE = 0;
    public const int SW_SHOW = 5;
    public const int SW_RESTORE = 9;

    // Struct marshalling
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    [DllImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

    // Callback
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern int GetWindowText(IntPtr hWnd,
                                          StringBuilder lpString,
                                          int nMaxCount);
}

// Usage
public static class WindowManager
{
    public static IntPtr FindWindowByTitle(string title)
    {
        IntPtr found = IntPtr.Zero;
        NativeMethods.EnumWindows((hWnd, lParam) =>
        {
            var sb = new StringBuilder(256);
            NativeMethods.GetWindowText(hWnd, sb, sb.Capacity);
            if (sb.ToString().Contains(title))
            {
                found = hWnd;
                return false;
            }
            return true;
        }, IntPtr.Zero);
        return found;
    }
}
```

---

## 6. DirectX 12

```cpp
// DirectX 12 initialization (C++/WinRT)
#include <d3d12.h>
#include <dxgi1_6.h>

class D3D12Renderer {
    ComPtr<ID3D12Device> device;
    ComPtr<ID3D12CommandQueue> commandQueue;
    ComPtr<IDXGISwapChain3> swapChain;
    ComPtr<ID3D12DescriptorHeap> rtvHeap;

    void Initialize(HWND hwnd, int width, int height) {
        // Enable debug layer
        ComPtr<ID3D12Debug> debugController;
        D3D12GetDebugInterface(IID_PPV_ARGS(&debugController));
        debugController->EnableDebugLayer();

        // Create device
        CreateDXGIFactory1(IID_PPV_ARGS(&factory));
        D3D12CreateDevice(nullptr, D3D_FEATURE_LEVEL_12_0,
                          IID_PPV_ARGS(&device));

        // Create command queue
        D3D12_COMMAND_QUEUE_DESC queueDesc = {};
        queueDesc.Type = D3D12_COMMAND_LIST_TYPE_DIRECT;
        device->CreateCommandQueue(&queueDesc,
                                   IID_PPV_ARGS(&commandQueue));

        // Create swap chain
        DXGI_SWAP_CHAIN_DESC1 swapChainDesc = {};
        swapChainDesc.BufferCount = 3;
        swapChainDesc.Width = width;
        swapChainDesc.Height = height;
        swapChainDesc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
        swapChainDesc.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
        swapChainDesc.SwapEffect = DXGI_SWAP_EFFECT_FLIP_DISCARD;
        swapChainDesc.SampleDesc.Count = 1;

        ComPtr<IDXGISwapChain1> tempSwapChain;
        factory->CreateSwapChainForHwnd(
            commandQueue.Get(), hwnd, &swapChainDesc,
            nullptr, nullptr, &tempSwapChain);
        tempSwapChain.As(&swapChain);
    }
};
```

---

## 7. MSIX Packaging

```xml
<!-- Package.appxmanifest -->
<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
         xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
         xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
         IgnorableNamespaces="uap rescap">

    <Identity Name="MyApp" Publisher="CN=Publisher" Version="1.0.0.0"/>
    <Properties>
        <DisplayName>My App</DisplayName>
        <PublisherDisplayName>Publisher</PublisherDisplayName>
        <Logo>Assets\StoreLogo.png</Logo>
    </Properties>

    <Dependencies>
        <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.17763.0" MaxVersionTested="10.0.22621.0"/>
    </Dependencies>

    <Resources>
        <Resource Language="en-us"/>
    </Resources>

    <Applications>
        <Application Id="App" Executable="MyApp.exe" EntryPoint="Windows.FullTrustApplication">
            <uap:VisualElements DisplayName="My App"
                               Description="My application"
                               Square150x150Logo="Assets\Square150x150Logo.png"
                               Square44x44Logo="Assets\Square44x44Logo.png"
                               BackgroundColor="transparent">
                <uap:DefaultTile Wide310x150Logo="Assets\Wide310x150Logo.png"
                                Square71x71Logo="Assets\SmallTile.png"/>
            </uap:VisualElements>
        </Application>
    </Applications>

    <Capabilities>
        <rescap:Capability Name="runFullTrust"/>
        <Capability Name="internetClient"/>
    </Capabilities>
</Package>
```

---

## 8. Windows Installer (WiX)

```xml
<!-- Product.wxs -->
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
    <Product Id="*" Name="MyApp" Language="1033"
             Version="1.0.0.0" Manufacturer="My Company"
             UpgradeCode="YOUR-GUID-HERE">

        <Package InstallerVersion="200" Compressed="yes"
                 InstallScope="perMachine"/>

        <MajorUpgrade DowngradeErrorMessage="A newer version is already installed."/>
        <MediaTemplate EmbedCab="yes"/>

        <Directory Id="TARGETDIR" Name="SourceDir">
            <Directory Id="ProgramFiles64Folder">
                <Directory Id="APPLICATIONFOLDER" Name="MyApp">
                    <Component Id="MainExecutable" Guid="YOUR-GUID">
                        <File Id="MyAppEXE" Name="MyApp.exe"
                              Source="$(var.BuildDir)\MyApp.exe"/>
                        <Shortcut Id="StartMenuShortcut"
                                  Directory="ProgramMenuFolder"
                                  Name="MyApp"
                                  WorkingDirectory="APPLICATIONFOLDER"
                                  Advertise="yes"/>
                    </Component>
                </Directory>
            </Directory>
        </Directory>

        <Feature Id="MainFeature" Title="Main" Level="1">
            <ComponentRef Id="MainExecutable"/>
        </Feature>
    </Product>
</Wix>
```

---

## 9. Auto-Update (Squirrel)

```csharp
// Squirrel.Windows integration
public class Program
{
    [STAThread]
    static void Main(string[] args)
    {
        // Handle Squirrel events
        SquirrelAwareApp.HandleEvents(
            onInitialInstall: OnInstall,
            onAppUninstall: OnUninstall,
            onEveryRun: OnEveryRun
        );

        Application.Run(new MainForm());
    }

    private static void OnInstall(SemanticVersion version, IAppTools tools)
    {
        tools.CreateShortcutForThisExe(ShortcutLocation.StartMenu);
        tools.CreateShortcutForThisExe(ShortcutLocation.Desktop);
    }

    private static void OnUninstall(SemanticVersion version, IAppTools tools)
    {
        tools.RemoveShortcutForThisExe(ShortcutLocation.StartMenu);
        tools.RemoveShortcutForThisExe(ShortcutLocation.Desktop);
    }

    private static async Task OnEveryRun(SemanticVersion version,
                                          IAppTools tools, bool firstRun)
    {
        // Check for updates in background
        using var mgr = await UpdateManager.GitHubUpdateManager(
            "https://github.com/username/repo");
        var updateInfo = await mgr.CheckForUpdate();

        if (updateInfo.ReleasesToApply.Any())
        {
            await mgr.DownloadReleases(updateInfo.ReleasesToApply);
            await mgr.ApplyReleases(updateInfo);
            UpdateManager.RestartApp();
        }
    }
}
```

---

## 10. COM Interop

```csharp
// Import COM type library
// Add reference to COM library or use dynamic

// Late binding (no compile-time reference)
Type? excelType = Type.GetTypeFromProgID("Excel.Application");
if (excelType != null)
{
    dynamic excel = Activator.CreateInstance(excelType);
    excel.Visible = true;
    excel.Workbooks.Add();
    dynamic sheet = excel.ActiveSheet;
    sheet.Cells[1, 1] = "Hello, Excel!";
}

// COM Callable Wrapper (CCW) — expose .NET to COM
[ComVisible(true)]
[Guid("YOUR-GUID-HERE")]
[InterfaceType(ComInterfaceType.InterfaceIsDual)]
public interface IMyComInterface
{
    string ProcessData(string input);
}

[ComVisible(true)]
[Guid("YOUR-GUID-HERE")]
[ClassInterface(ClassInterfaceType.None)]
[ProgId("MyApp.MyComClass")]
public class MyComClass : IMyComInterface
{
    public string ProcessData(string input)
    {
        return $"Processed: {input}";
    }
}
```

---

## 11. Windows Services

```csharp
using Microsoft.Extensions.Hosting;

public class MyService : BackgroundService
{
    private readonly ILogger<MyService> _logger;

    public MyService(ILogger<MyService> logger)
    {
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Service starting");

        while (!stoppingToken.IsCancellationRequested)
        {
            _logger.LogInformation("Service running at: {Time}", DateTimeOffset.Now);
            await Task.Delay(TimeSpan.FromMinutes(1), stoppingToken);
        }

        _logger.LogInformation("Service stopping");
    }
}

// Program.cs
using var host = Host.CreateDefaultBuilder(args)
    .UseWindowsService(options =>
    {
        options.ServiceName = "My Windows Service";
    })
    .ConfigureServices(services =>
    {
        services.AddHostedService<MyService>();
    })
    .Build();

await host.RunAsync();
```

---

## 12. UWP vs Win32 vs PWA Comparison

| Feature | UWP | Win32 (Desktop) | PWA |
|---------|-----|-----------------|-----|
| Distribution | Store | MSI, MSIX, Store | Web |
| APIs | Windows Runtime | Full Win32 | Web APIs |
| Sandbox | Yes | Optional | Browser sandbox |
| Installation | Store install | Various | Browser + manifest |
| Updates | Automatic | Manual/Store | Automatic |
| Background tasks | Limited | Full | Limited |
| File access | App-specific | Full | Browser |
| Performance | Good | Native | Limited |
| UI framework | WinUI, XAML | WinUI, WPF, WinForms | Web tech |
| Code sharing | .NET Native | .NET | JavaScript |
| Best for | Store apps | Full-featured desktop | Cross-platform |
