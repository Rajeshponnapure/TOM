# React Native + Mobile UI — Advanced Animation Skill

## Core Stack (2025/2026)
```json
{
  "react-native": "0.74+",
  "react-native-reanimated": "^3.9",
  "react-native-gesture-handler": "^2.16",
  "react-native-screens": "^3.31",
  "react-native-safe-area-context": "^4.10",
  "@react-navigation/native": "^6",
  "@react-navigation/bottom-tabs": "^6",
  "@react-navigation/stack": "^6",
  "moti": "^0.28",
  "react-native-skia": "^1.3",
  "expo-haptics": "~13.0",
  "expo-blur": "~13.0",
  "nativewind": "^4.0",
  "zustand": "^4"
}
```

---

## 1. Reanimated 3 — Worklet Animations

### Why worklets
Worklets run on the UI thread — no JS bridge latency, always 60fps.

```tsx
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withTiming,
  withSequence,
  withRepeat,
  runOnJS,
  interpolate,
  Extrapolation,
} from 'react-native-reanimated';

// Pressable with spring scale
export function AnimatedButton({ label, onPress }: { label: string; onPress: () => void }) {
  const scale = useSharedValue(1);
  const opacity = useSharedValue(1);

  const style = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
    opacity: opacity.value,
  }));

  return (
    <Animated.View style={style}>
      <Pressable
        onPressIn={() => {
          scale.value = withSpring(0.95, { damping: 15 });
          opacity.value = withTiming(0.85, { duration: 100 });
        }}
        onPressOut={() => {
          scale.value = withSpring(1, { damping: 12 });
          opacity.value = withTiming(1, { duration: 150 });
        }}
        onPress={onPress}
        style={{ backgroundColor: '#3B82F6', padding: 16, borderRadius: 12 }}
      >
        <Text style={{ color: '#fff', fontWeight: '600' }}>{label}</Text>
      </Pressable>
    </Animated.View>
  );
}

// Animated counter (number springs to target)
export function AnimatedNumber({ value }: { value: number }) {
  const progress = useSharedValue(0);

  useEffect(() => {
    progress.value = withSpring(value, { damping: 25, stiffness: 120 });
  }, [value]);

  const text = useDerivedValue(() => Math.round(progress.value).toString());

  return (
    <Animated.Text style={{ color: '#E2E8F0', fontSize: 32, fontWeight: '700' }}>
      {text}
    </Animated.Text>
  );
}

// Pulse glow (status indicator)
export function PulseOrb({ color = '#10B981' }: { color?: string }) {
  const scale = useSharedValue(1);

  useEffect(() => {
    scale.value = withRepeat(
      withSequence(
        withTiming(1.3, { duration: 800 }),
        withTiming(1.0, { duration: 800 }),
      ),
      -1,   // infinite
    );
  }, []);

  const style = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
    opacity: interpolate(scale.value, [1, 1.3], [0.8, 0.3], Extrapolation.CLAMP),
  }));

  return (
    <View style={{ width: 12, height: 12 }}>
      <Animated.View style={[StyleSheet.absoluteFill, { borderRadius: 6, backgroundColor: color }, style]} />
      <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: color, margin: 2 }} />
    </View>
  );
}
```

---

## 2. Gesture Handler + Pan Swipe

```tsx
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, { useSharedValue, useAnimatedStyle, withSpring, runOnJS } from 'react-native-reanimated';

const DISMISS_THRESHOLD = 120;

export function SwipeToDismiss({
  children,
  onDismiss,
}: { children: React.ReactNode; onDismiss: () => void }) {
  const translateX = useSharedValue(0);
  const opacity = useSharedValue(1);

  const pan = Gesture.Pan()
    .activeOffsetX([-10, 10])
    .onUpdate((e) => {
      translateX.value = e.translationX;
      opacity.value = 1 - Math.abs(e.translationX) / 300;
    })
    .onEnd((e) => {
      if (Math.abs(e.translationX) > DISMISS_THRESHOLD) {
        translateX.value = withSpring(Math.sign(e.translationX) * 400);
        opacity.value = withSpring(0);
        runOnJS(onDismiss)();
      } else {
        translateX.value = withSpring(0);
        opacity.value = withSpring(1);
      }
    });

  const style = useAnimatedStyle(() => ({
    transform: [{ translateX: translateX.value }],
    opacity: opacity.value,
  }));

  return (
    <GestureDetector gesture={pan}>
      <Animated.View style={style}>{children}</Animated.View>
    </GestureDetector>
  );
}
```

---

## 3. React Native Skia — Custom Graphics

```tsx
import { Canvas, Circle, Path, LinearGradient, vec, Skia } from '@shopify/react-native-skia';
import { useSharedValue, useDerivedValue } from 'react-native-reanimated';

// Animated donut chart
export function DonutChart({ progress }: { progress: number }) {
  const animatedProgress = useSharedValue(0);

  useEffect(() => {
    animatedProgress.value = withTiming(progress, { duration: 1200 });
  }, [progress]);

  const path = useDerivedValue(() => {
    const r = 80;
    const cx = 110, cy = 110;
    const angle = animatedProgress.value * 2 * Math.PI;
    const x = cx + r * Math.sin(angle);
    const y = cy - r * Math.cos(angle);
    const largeArc = animatedProgress.value > 0.5 ? 1 : 0;
    const p = Skia.Path.Make();
    p.moveTo(cx, cy - r);
    p.arcToOval({ x: cx - r, y: cy - r, width: r * 2, height: r * 2 }, -90, animatedProgress.value * 360, false);
    return p;
  });

  return (
    <Canvas style={{ width: 220, height: 220 }}>
      {/* Track */}
      <Circle cx={110} cy={110} r={80} color="rgba(30,45,69,1)" style="stroke" strokeWidth={12} />
      {/* Progress arc */}
      <Path path={path} color="transparent" style="stroke" strokeWidth={12} strokeCap="round">
        <LinearGradient
          start={vec(110, 30)}
          end={vec(110, 190)}
          colors={['#3B82F6', '#06B6D4']}
        />
      </Path>
    </Canvas>
  );
}
```

---

## 4. Navigation — Bottom Tabs + Stack

```tsx
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { BlurView } from 'expo-blur';

const Tab = createBottomTabNavigator();

export function AppNavigator() {
  return (
    <NavigationContainer>
      <Tab.Navigator
        screenOptions={{
          headerShown: false,
          tabBarStyle: {
            position: 'absolute',
            backgroundColor: 'transparent',
            borderTopWidth: 0,
            elevation: 0,
          },
          tabBarBackground: () => (
            <BlurView intensity={80} tint="dark" style={StyleSheet.absoluteFill} />
          ),
          tabBarActiveTintColor: '#3B82F6',
          tabBarInactiveTintColor: '#475569',
          tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
        }}
      >
        <Tab.Screen name="Home"     component={HomeScreen} />
        <Tab.Screen name="Chat"     component={ChatScreen} />
        <Tab.Screen name="Settings" component={SettingsScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
```

---

## 5. Chat Bubble Component

```tsx
import Animated, { FadeIn, SlideInLeft, SlideInRight } from 'react-native-reanimated';

interface MessageProps {
  text: string;
  role: 'user' | 'assistant';
  timestamp: string;
}

export function ChatMessage({ text, role, timestamp }: MessageProps) {
  const isUser = role === 'user';

  return (
    <Animated.View
      entering={isUser ? SlideInRight.duration(280) : SlideInLeft.duration(280)}
      style={{
        alignSelf: isUser ? 'flex-end' : 'flex-start',
        maxWidth: '80%',
        marginVertical: 4,
        marginHorizontal: 16,
      }}
    >
      <View
        style={{
          backgroundColor: isUser ? '#1E3A5F' : '#0F1624',
          borderRadius: 16,
          borderBottomRightRadius: isUser ? 4 : 16,
          borderBottomLeftRadius: isUser ? 16 : 4,
          borderWidth: 1,
          borderColor: isUser ? '#253550' : '#1E2D45',
          padding: 12,
        }}
      >
        <Text style={{ color: '#E2E8F0', fontSize: 14, lineHeight: 20 }}>{text}</Text>
        <Text style={{ color: '#475569', fontSize: 10, marginTop: 4, alignSelf: 'flex-end' }}>
          {timestamp}
        </Text>
      </View>
    </Animated.View>
  );
}
```

---

## 6. Haptic Feedback Integration

```tsx
import * as Haptics from 'expo-haptics';

// On button tap
const onTap = async () => {
  await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
  // do work
};

// On success
const onSuccess = async () => {
  await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
};

// On error
const onError = async () => {
  await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
};
```

---

## 7. Dark Theme NativeWind Setup

```tsx
// NativeWind v4 + dark theme
import { View, Text } from 'react-native';
import { styled } from 'nativewind';

const StyledView = styled(View);
const StyledText = styled(Text);

export function Card({ title, value, color }: { title: string; value: string; color: string }) {
  return (
    <StyledView className="rounded-xl bg-slate-900 border border-slate-800 p-4 mb-3">
      <StyledText className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-1">
        {title}
      </StyledText>
      <StyledText className="text-2xl font-bold" style={{ color }}>
        {value}
      </StyledText>
    </StyledView>
  );
}
```

---

## 8. Performance Rules

### Critical worklet rules
- Never import from the JS thread inside a worklet — `'worklet'` directive means it runs on UI thread
- Side effects inside worklets must use `runOnJS(fn)(args)` — direct function calls crash
- `useAnimatedStyle` return value must be a plain object — no arrays, no computed keys

### New Architecture (RN 0.74+)
- `fabric` renderer + `JSI` = no bridge → `withSpring()` etc. are now truly synchronous
- `turbo-modules` replaces legacy native modules — upgrade carefully
- `react-native-reanimated` ≥ 3.6 is required for New Architecture compatibility

### Layout animations
- `Animated.FlatList` + `itemLayoutAnimation` for smooth list reorders
- `LayoutAnimationConfig` wraps screens for automatic enter/exit transitions
- Avoid mixing old `LayoutAnimation` API with Reanimated 3

### iOS vs Android
- Use `Platform.OS` to adjust spring physics — Android needs `damping` ≈ 20-25, iOS ≈ 12-15
- `Keyboard.addListener` to shift layout on keyboard appear/dismiss
- `StatusBar.setStyle('light-content')` for dark-themed apps on both platforms
