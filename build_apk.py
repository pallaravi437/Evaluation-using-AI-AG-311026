import os
import subprocess
import shutil
import zipfile

def run_cmd(cmd, description):
    print(f"[*] Running: {description}...")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[!] Error in {description}:")
        print(res.stderr)
        print(res.stdout)
        raise RuntimeError(f"Command failed: {description}")
    print(f"[+] Success: {description}")
    return res.stdout

def build_apk():
    sdk_dir = "C:/Users/anusha/Android/Sdk"
    build_tools = os.path.join(sdk_dir, "build-tools/34.0.0")
    android_jar = os.path.join(sdk_dir, "platforms/android-34/android.jar")
    
    aapt2 = os.path.join(build_tools, "aapt2.exe")
    d8 = os.path.join(build_tools, "d8.bat")
    zipalign = os.path.join(build_tools, "zipalign.exe")
    apksigner = os.path.join(build_tools, "apksigner.bat")
    
    work_dir = os.path.abspath("android_build_temp")
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir, exist_ok=True)
    
    # 0. Sync fresh static assets to android_app/app/src/main/assets
    assets_static = os.path.abspath("android_app/app/src/main/assets/static")
    src_static = os.path.abspath("static")
    if os.path.exists(src_static):
        os.makedirs(assets_static, exist_ok=True)
        for item in ["css", "js", "icons", "images"]:
            s = os.path.join(src_static, item)
            d = os.path.join(assets_static, item)
            if os.path.exists(s):
                if os.path.exists(d):
                    shutil.rmtree(d)
                shutil.copytree(s, d)
        for f in ["sw.js", "manifest.json"]:
            sf = os.path.join(src_static, f)
            df = os.path.join(assets_static, f)
            if os.path.exists(sf):
                shutil.copy2(sf, df)
        print("[+] Synced latest web assets to Android assets directory")

    res_compiled = os.path.join(work_dir, "compiled_res.zip")
    gen_dir = os.path.join(work_dir, "gen")
    classes_dir = os.path.join(work_dir, "classes")
    dex_dir = os.path.join(work_dir, "dex")
    unaligned_apk = os.path.join(work_dir, "unaligned.apk")
    aligned_apk = os.path.join(work_dir, "aligned.apk")
    debug_apk = os.path.join(work_dir, "app-debug.apk")
    release_apk = os.path.join(work_dir, "app-release.apk")
    
    os.makedirs(gen_dir, exist_ok=True)
    os.makedirs(classes_dir, exist_ok=True)
    os.makedirs(dex_dir, exist_ok=True)
    
    # 1. Compile Resources with aapt2
    res_dir = os.path.abspath("android_app/app/src/main/res")
    run_cmd(f'"{aapt2}" compile --dir "{res_dir}" -o "{res_compiled}"', "aapt2 compile resources")
    
    # 2. Link Resources and Generate R.java
    manifest_xml = os.path.abspath("android_app/app/src/main/AndroidManifest.xml")
    assets_dir = os.path.abspath("android_app/app/src/main/assets")
    
    link_cmd = (
        f'"{aapt2}" link -o "{unaligned_apk}" '
        f'-I "{android_jar}" '
        f'--manifest "{manifest_xml}" '
        f'--java "{gen_dir}" '
        f'-A "{assets_dir}" '
        f'--auto-add-overlay '
        f'"{res_compiled}"'
    )
    run_cmd(link_cmd, "aapt2 link")
    
    # 3. Compile Java Source Files
    java_files = []
    for r, d, fs in os.walk(gen_dir):
        for f in fs:
            if f.endswith(".java"):
                java_files.append(os.path.join(r, f))
                
    src_dir = os.path.abspath("android_app/app/src/main/java")
    for r, d, fs in os.walk(src_dir):
        for f in fs:
            if f.endswith(".java"):
                java_files.append(os.path.join(r, f))
                
    java_sources_str = " ".join(f'"{f}"' for f in java_files)
    javac_cmd = f'javac -source 1.8 -target 1.8 -cp "{android_jar}" -d "{classes_dir}" {java_sources_str}'
    run_cmd(javac_cmd, "javac compile Java files")
    
    # 4. Generate DEX with d8
    class_files = []
    for r, d, fs in os.walk(classes_dir):
        for f in fs:
            if f.endswith(".class"):
                class_files.append(os.path.join(r, f))
                
    classes_str = " ".join(f'"{f}"' for f in class_files)
    d8_cmd = f'"{d8}" --output "{dex_dir}" --lib "{android_jar}" {classes_str}'
    run_cmd(d8_cmd, "d8 generate classes.dex")
    
    # 5. Add classes.dex into unaligned APK
    classes_dex = os.path.join(dex_dir, "classes.dex")
    with zipfile.ZipFile(unaligned_apk, "a") as zf:
        zf.write(classes_dex, arcname="classes.dex")
    print("[+] Added classes.dex into APK archive")
    
    # 6. Align APK with zipalign
    zipalign_cmd = f'"{zipalign}" -v -p 4 "{unaligned_apk}" "{aligned_apk}"'
    run_cmd(zipalign_cmd, "zipalign APK")
    
    # 7. Create debug keystore & sign app-debug.apk
    debug_keystore = os.path.join(work_dir, "debug.keystore")
    keytool_debug_cmd = (
        f'keytool -genkeypair -v -keystore "{debug_keystore}" '
        f'-storepass android -alias androiddebugkey -keypass android '
        f'-keyalg RSA -keysize 2048 -validity 10000 '
        f'-dname "CN=Android Debug,O=Android,C=US"'
    )
    run_cmd(keytool_debug_cmd, "keytool create debug keystore")
    
    sign_debug_cmd = (
        f'"{apksigner}" sign --ks "{debug_keystore}" '
        f'--ks-pass pass:android --key-pass pass:android '
        f'--ks-key-alias androiddebugkey '
        f'--out "{debug_apk}" "{aligned_apk}"'
    )
    run_cmd(sign_debug_cmd, "apksigner sign debug APK")
    
    # 8. Create release keystore & sign app-release.apk
    release_keystore = os.path.join(work_dir, "release.keystore")
    keytool_release_cmd = (
        f'keytool -genkeypair -v -keystore "{release_keystore}" '
        f'-storepass aievaluator2026 -alias aievaluatorkey -keypass aievaluator2026 '
        f'-keyalg RSA -keysize 2048 -validity 10000 '
        f'-dname "CN=AI Evaluator Production,O=BEA Educational Systems,C=IN"'
    )
    run_cmd(keytool_release_cmd, "keytool create production release keystore")
    
    sign_release_cmd = (
        f'"{apksigner}" sign --ks "{release_keystore}" '
        f'--ks-pass pass:aievaluator2026 --key-pass pass:aievaluator2026 '
        f'--ks-key-alias aievaluatorkey '
        f'--out "{release_apk}" "{aligned_apk}"'
    )
    run_cmd(sign_release_cmd, "apksigner sign release APK")
    
    # 9. Verify APK signatures
    verify_cmd = f'"{apksigner}" verify --verbose "{release_apk}"'
    verify_out = run_cmd(verify_cmd, "apksigner verify release APK")
    print(verify_out)
    
    # Copy both APKs to output folders
    out_dirs = [
        os.path.abspath(".build-outputs"),
        os.path.abspath("APK_DOWNLOAD")
    ]
    for d in out_dirs:
        os.makedirs(d, exist_ok=True)
        shutil.copy2(debug_apk, os.path.join(d, "app-debug.apk"))
        shutil.copy2(release_apk, os.path.join(d, "app-release.apk"))
        print(f"[+] Placed app-debug.apk & app-release.apk at: {d}")
        
    debug_size = os.path.getsize(debug_apk)
    release_size = os.path.getsize(release_apk)
    print(f"[*] Debug APK Size: {debug_size / (1024*1024):.2f} MB")
    print(f"[*] Release APK Size: {release_size / (1024*1024):.2f} MB")
    
    # Clean up temp
    shutil.rmtree(work_dir, ignore_errors=True)
    return {
        "debug_apk": os.path.join(out_dirs[1], "app-debug.apk"),
        "release_apk": os.path.join(out_dirs[1], "app-release.apk")
    }

if __name__ == "__main__":
    out = build_apk()
    print("FINISHED ALL BUILDS SUCCESSFULLY:", out)
