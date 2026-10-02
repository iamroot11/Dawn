import 'package:flutter/material.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const App());
}

class App extends StatelessWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Dawn',
      theme: ThemeData(
        fontFamily: "GoogleSans",
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blueAccent),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        fontFamily: "GoogleSans",
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blueAccent),
        useMaterial3: true,
      ),
      themeMode: ThemeMode.dark,
      initialRoute: '/',
      routes: {},
    );
  }
}

class ResponsiveWidget extends StatelessWidget {
  final Widget mobileBody;
  final Widget desktopBody;
  final int mobileBreakpoint; // Define the breakpoint

  const ResponsiveWidget({
    super.key,
    required this.mobileBody,
    required this.desktopBody,
    this.mobileBreakpoint = 600, // Default breakpoint (in pixels)
  });

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        if (constraints.maxWidth < mobileBreakpoint) {
          return mobileBody;
        } else {
          return desktopBody;
        }
      },
    );
  }
}
