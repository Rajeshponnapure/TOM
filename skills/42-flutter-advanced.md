# Flutter Desktop & Mobile — Advanced Animation & UI Skill

## Core Dependencies (pubspec.yaml)
```yaml
dependencies:
  flutter:
    sdk: flutter
  flutter_animate: ^4.5.0        # Chainable widget animations
  animations: ^2.0.11            # Material motion system
  rive: ^0.13.0                  # Rive animation runtime
  lottie: ^3.0.0                 # Lottie JSON animations
  window_manager: ^0.3.9         # Desktop window control
  go_router: ^13.0.0             # Declarative routing
  riverpod: ^2.5.1               # State management
  flutter_riverpod: ^2.5.1
  hooks_riverpod: ^2.5.1
  shimmer: ^3.0.0                # Loading skeleton shimmer
  glassmorphism: ^3.0.0          # Frosted glass effect
  animated_text_kit: ^4.2.2      # Text animations

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.0
```

---

## 1. Dark Theme System
```dart
import 'package:flutter/material.dart';

final kDark = ThemeData(
  useMaterial3: true,
  brightness: Brightness.dark,
  colorScheme: const ColorScheme.dark(
    primary: Color(0xFF3B82F6),
    secondary: Color(0xFF06B6D4),
    tertiary: Color(0xFF8B5CF6),
    surface: Color(0xFF0F1624),
    background: Color(0xFF080C14),
    onBackground: Color(0xFFE2E8F0),
    onSurface: Color(0xFFE2E8F0),
  ),
  scaffoldBackgroundColor: const Color(0xFF080C14),
  cardTheme: const CardTheme(
    color: Color(0xFF0F1624),
    elevation: 0,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.all(Radius.circular(12)),
      side: BorderSide(color: Color(0xFF1E2D45)),
    ),
  ),
  textTheme: const TextTheme(
    headlineLarge: TextStyle(color: Color(0xFFE2E8F0), fontWeight: FontWeight.w700),
    bodyMedium: TextStyle(color: Color(0xFF94A3B8)),
  ),
);
```

---

## 2. flutter_animate — Chainable Animations
```dart
import 'package:flutter_animate/flutter_animate.dart';

// Staggered list with fade + slide
Widget buildAnimatedList(List<String> items) {
  return Column(
    children: [
      for (final (i, item) in items.indexed)
        ListTile(title: Text(item))
          .animate(delay: (80 * i).ms)
          .fadeIn(duration: 300.ms, curve: Curves.easeOut)
          .slideY(begin: 0.2, end: 0, duration: 300.ms, curve: Curves.easeOutQuart)
    ],
  );
}

// Shimmer on a card while loading
Widget loadingCard() {
  return Container(
    width: 200, height: 100,
    decoration: BoxDecoration(
      color: const Color(0xFF0F1624),
      borderRadius: BorderRadius.circular(12),
    ),
  ).animate(onPlay: (ctrl) => ctrl.repeat())
   .shimmer(duration: 1200.ms, color: const Color(0xFF1E3A5F));
}

// Pulse glow on a status indicator
Widget statusOrb(Color color) {
  return Container(
    width: 12, height: 12,
    decoration: BoxDecoration(color: color, shape: BoxShape.circle),
  ).animate(onPlay: (ctrl) => ctrl.repeat(reverse: true))
   .scale(begin: const Offset(1, 1), end: const Offset(1.4, 1.4), duration: 800.ms)
   .fadeOut(begin: 1.0, duration: 800.ms);
}
```

---

## 3. Custom Painter — Animated Network Graph
```dart
import 'dart:math';
import 'package:flutter/material.dart';

class NetworkPainter extends CustomPainter {
  final double t;
  final List<Offset> nodes;
  final Color primary;

  const NetworkPainter({required this.t, required this.nodes, required this.primary});

  @override
  void paint(Canvas canvas, Size size) {
    final linePaint = Paint()
      ..color = primary.withOpacity(0.15)
      ..strokeWidth = 1.0
      ..style = PaintingStyle.stroke;

    final nodePaint = Paint()..style = PaintingStyle.fill;

    // Draw connections
    for (int i = 0; i < nodes.length; i++) {
      for (int j = i + 1; j < nodes.length; j++) {
        final dist = (nodes[i] - nodes[j]).distance;
        if (dist < 180) {
          linePaint.color = primary.withOpacity(0.08 + 0.12 * (1 - dist / 180));
          canvas.drawLine(nodes[i], nodes[j], linePaint);
        }
      }
    }

    // Draw nodes with glow
    for (final node in nodes) {
      final pulse = 0.7 + 0.3 * sin(t + node.dx * 0.01);
      for (int r = 3; r >= 1; r--) {
        nodePaint.color = primary.withOpacity(0.05 * r * pulse);
        canvas.drawCircle(node, 4.0 * r, nodePaint);
      }
      nodePaint.color = primary.withOpacity(0.9 * pulse);
      canvas.drawCircle(node, 3, nodePaint);
    }
  }

  @override
  bool shouldRepaint(NetworkPainter oldDelegate) => oldDelegate.t != t;
}

// Usage with AnimationController
class NetworkWidget extends StatefulWidget {
  const NetworkWidget({super.key});
  @override
  State<NetworkWidget> createState() => _NetworkWidgetState();
}

class _NetworkWidgetState extends State<NetworkWidget>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late List<Offset> _nodes;
  final _rand = Random(42);

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(seconds: 10))
      ..repeat();
    _nodes = List.generate(18, (_) => Offset(
      _rand.nextDouble() * 400,
      _rand.nextDouble() * 300,
    ));
  }

  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _ctrl,
      builder: (_, __) => CustomPaint(
        painter: NetworkPainter(
          t: _ctrl.value * pi * 2,
          nodes: _nodes,
          primary: const Color(0xFF3B82F6),
        ),
        size: const Size(400, 300),
      ),
    );
  }
}
```

---

## 4. Page Transitions — Shared Element & Fade
```dart
import 'package:animations/animations.dart';
import 'package:go_router/go_router.dart';

// Shared axis transition (horizontal slide)
CustomTransitionPage<T> sharedAxisPage<T>({
  required LocalKey key,
  required Widget child,
  SharedAxisTransitionType type = SharedAxisTransitionType.horizontal,
}) {
  return CustomTransitionPage(
    key: key,
    child: child,
    transitionsBuilder: (ctx, anim, secAnim, child) =>
      SharedAxisTransition(
        animation: anim,
        secondaryAnimation: secAnim,
        transitionType: type,
        child: child,
      ),
  );
}

// OpenContainer for hero-like expansion
Widget heroCard({required Widget closedChild, required Widget openChild}) {
  return OpenContainer(
    closedColor: const Color(0xFF0F1624),
    openColor: const Color(0xFF080C14),
    closedElevation: 0,
    closedShape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    transitionDuration: const Duration(milliseconds: 350),
    closedBuilder: (ctx, open) => InkWell(onTap: open, child: closedChild),
    openBuilder: (ctx, _) => openChild,
  );
}
```

---

## 5. Desktop Window Control
```dart
import 'package:window_manager/window_manager.dart';

Future<void> setupWindow() async {
  await windowManager.ensureInitialized();
  await windowManager.waitUntilReadyToShow(
    const WindowOptions(
      size: Size(1400, 900),
      minimumSize: Size(1100, 700),
      center: true,
      backgroundColor: Colors.transparent,
      skipTaskbar: false,
      titleBarStyle: TitleBarStyle.hidden,  // custom title bar
    ),
    () async {
      await windowManager.show();
      await windowManager.focus();
    },
  );
}

// Draggable custom title bar
class DragToMoveArea extends StatelessWidget {
  const DragToMoveArea({required this.child, super.key});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onPanStart: (_) => windowManager.startDragging(),
      child: child,
    );
  }
}
```

---

## 6. Mobile — Bottom Sheet Drag UI
```dart
import 'package:flutter/material.dart';

class DraggableSheet extends StatelessWidget {
  const DraggableSheet({super.key});

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.4,
      minChildSize: 0.15,
      maxChildSize: 0.92,
      snap: true,
      snapSizes: const [0.15, 0.4, 0.92],
      builder: (ctx, scrollCtrl) => Container(
        decoration: const BoxDecoration(
          color: Color(0xFF0F1624),
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
          border: Border(
            top: BorderSide(color: Color(0xFF1E2D45)),
            left: BorderSide(color: Color(0xFF1E2D45)),
            right: BorderSide(color: Color(0xFF1E2D45)),
          ),
        ),
        child: Column(children: [
          // Drag handle
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Container(
              width: 36, height: 4,
              decoration: BoxDecoration(
                color: const Color(0xFF475569),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          Expanded(
            child: ListView.builder(
              controller: scrollCtrl,
              itemBuilder: (_, i) => ListTile(title: Text('Item $i')),
            ),
          ),
        ]),
      ),
    );
  }
}
```

---

## 7. Performance Rules

### Flutter
- Use `const` constructors everywhere — avoids unnecessary rebuilds
- `RepaintBoundary` isolates expensive animated widgets from the rest of the tree
- `ListView.builder` + `SliverList` for long lists — never `Column` with children
- Profile with `flutter run --profile` and DevTools → Performance tab
- Avoid `setState()` in build → use `AnimatedBuilder`, `ValueListenableBuilder`, or Riverpod
- `AnimationController.dispose()` in every `State.dispose()` — no exceptions
- For 60fps custom painters: `shouldRepaint` must return `false` when data unchanged

### Mobile-specific
- Target 16.67ms frame budget (60fps) — check with DevTools
- Use `InteractiveViewer` for zoom/pan gestures (built-in, no custom GestureDetector)
- `HapticFeedback.lightImpact()` on button presses for native feel
- `SafeArea` wraps every scaffold to avoid notch/home-bar overlap
- Test on both notched (Dynamic Island) and notchless devices

---

## 8. Glassmorphism Card
```dart
import 'dart:ui';

Widget glassCard({required Widget child, double blur = 20, double opacity = 0.1}) {
  return ClipRRect(
    borderRadius: BorderRadius.circular(16),
    child: BackdropFilter(
      filter: ImageFilter.blur(sigmaX: blur, sigmaY: blur),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(opacity),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withOpacity(0.2)),
        ),
        child: child,
      ),
    ),
  );
}
```
