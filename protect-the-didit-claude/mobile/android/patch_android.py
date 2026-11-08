"""Run after `npx cap add android`: landscape only + fullscreen (no status / navigation bars) + notch support."""
import os
import re
import sys

base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "android", "app", "src", "main")
man = os.path.join(base, "AndroidManifest.xml")
s = open(man, encoding="utf-8").read()
if "screenOrientation" not in s:
    s = s.replace("<activity", '<activity\n            android:screenOrientation="sensorLandscape"', 1)
    open(man, "w", encoding="utf-8").write(s)

sty = os.path.join(base, "res", "values", "styles.xml")
t = open(sty, encoding="utf-8").read()
extra = ('    <item name="android:windowFullscreen">true</item>\n'
         '    <item name="android:windowLayoutInDisplayCutoutMode">shortEdges</item>\n')
if "windowFullscreen" not in t:
    t = re.sub(r'(<style name="AppTheme\.NoActionBarLaunch"[^>]*>)', r"\1\n" + extra, t)
    t = re.sub(r'(<style name="AppTheme\.NoActionBar"[^>]*>)', r"\1\n" + extra, t)
    open(sty, "w", encoding="utf-8").write(t)

main_java = None
for root, _, files in os.walk(os.path.join(base, "java")):
    if "MainActivity.java" in files:
        main_java = os.path.join(root, "MainActivity.java")
if main_java:   # immersive mode: hide the system bars for good
    j = open(main_java, encoding="utf-8").read()
    if "setSystemUiVisibility" not in j:
        j = j.replace("public class MainActivity extends BridgeActivity {}", """public class MainActivity extends BridgeActivity {
    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            getWindow().getDecorView().setSystemUiVisibility(
                android.view.View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY | android.view.View.SYSTEM_UI_FLAG_FULLSCREEN
                | android.view.View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | android.view.View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                | android.view.View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION | android.view.View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN);
        }
    }
}""")
        open(main_java, "w", encoding="utf-8").write(j)
print("android project patched")
sys.exit(0)
