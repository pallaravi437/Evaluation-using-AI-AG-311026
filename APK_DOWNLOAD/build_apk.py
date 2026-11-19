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
    
    res_compiled = os.path.join(work_dir, "compiled_res.zip")
    gen_dir = os.path.join(work_dir, "gen")
    classes_dir = os.path.join(work_dir, "classes")
    dex_dir = os.path.join(work_dir, "dex")
    unaligned_apk = os.path.join(work_dir, "unaligned.apk")
    aligned_apk = os.path.join(work_dir, "aligned.apk")
    final_apk = os.path.join(work_dir, "app-debug.apk")
    
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
    
    # 7. Create debug keystore if not exists
    keystore_path = os.path.join(work_dir, "debug.keystore")
    keytool_cmd = (
        f'keytool -genkeypair -v -keystore "{keystore_path}" '
        f'-storepass android -alias androiddebugkey -keypass android '
        f'-keyalg RSA -keysize 2048 -validity 10000 '
        f'-dname "CN=Android Debug,O=Android,C=US"'
    )
    run_cmd(keytool_cmd, "keytool create debug keystore")
    
    # 8. Sign APK with apksigner
    sign_cmd = (
        f'"{apksigner}" sign --ks "{keystore_path}" '
        f'--ks-pass pass:android --key-pass pass:android '
        f'--ks-key-alias androiddebugkey '
        f'--out "{final_apk}" "{aligned_apk}"'
    )
    run_cmd(sign_cmd, "apksigner sign APK")
    
    # 9. Verify APK signature
    verify_cmd = f'"{apksigner}" verify --verbose "{final_apk}"'
    verify_out = run_cmd(verify_cmd, "apksigner verify APK")
    print(verify_out)
    
    apk_size = os.path.getsize(final_apk)
    print(f"[*] Generated real APK size: {apk_size} bytes ({apk_size / (1024*1024):.2f} MB)")
    
    if apk_size < 1024 * 1024:
        raise ValueError(f"APK size is less than 1MB: {apk_size} bytes")
        
    # Copy to destinations requested by user
    dest1 = os.path.abspath(".build-outputs/app-debug.apk")
    dest2 = os.path.abspath("APK_DOWNLOAD/app-debug.apk")
    
    os.makedirs(os.path.dirname(dest1), exist_ok=True)
    os.makedirs(os.path.dirname(dest2), exist_ok=True)
    
    shutil.copy2(final_apk, dest1)
    shutil.copy2(final_apk, dest2)
    print(f"[+] Placed copy at: {dest1}")
    print(f"[+] Placed copy at: {dest2}")
    
    # Clean up work dir
    shutil.rmtree(work_dir, ignore_errors=True)
    return dest2

if __name__ == "__main__":
    out = build_apk()
    print("FINISHED SUCCESSFULLY:", out)
