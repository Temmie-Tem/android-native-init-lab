#!/system/bin/sh
# ====================================================================
# Package Scanner - 설치된 패키지 분석 스크립트
# ====================================================================
# 목적: 실제 설치된 패키지를 카테고리별로 스캔 및 분류
# 사용법: adb shell sh /data/local/tmp/scan_packages.sh
# ====================================================================

LOGFILE="/data/local/tmp/package_scan.log"
PKGLIST="/data/local/tmp/package_list.txt"

# ====================================================================
# 로그 초기화
# ====================================================================

echo "=========================================" > "$LOGFILE"
echo "Package Scanner" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "Started: $(date)" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# 전체 패키지 목록 수집
# ====================================================================

echo "Collecting all installed packages..." | tee -a "$LOGFILE"
pm list packages | sed 's/^package://' | sort > "$PKGLIST"

TOTAL_COUNT=$(wc -l < "$PKGLIST")
echo "Total packages: $TOTAL_COUNT" | tee -a "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# 카테고리별 분류 함수
# ====================================================================

scan_category() {
    CATEGORY_NAME="$1"
    PATTERN="$2"

    echo "----------------------------------------" >> "$LOGFILE"
    echo "$CATEGORY_NAME" | tee -a "$LOGFILE"
    echo "----------------------------------------" >> "$LOGFILE"

    COUNT=0
    while IFS= read -r pkg; do
        case "$pkg" in
            $PATTERN)
                echo "  - $pkg" >> "$LOGFILE"
                COUNT=$((COUNT + 1))
                ;;
        esac
    done < "$PKGLIST"

    echo "" >> "$LOGFILE"
    echo "Total: $COUNT packages" | tee -a "$LOGFILE"
    echo "" >> "$LOGFILE"

    return $COUNT
}

# ====================================================================
# 1. GUI Components (SystemUI, Launcher, Keyboard)
# ====================================================================

echo "" | tee -a "$LOGFILE"
echo "=========================================" | tee -a "$LOGFILE"
echo "1. GUI Components" | tee -a "$LOGFILE"
echo "=========================================" | tee -a "$LOGFILE"
echo "" >> "$LOGFILE"

GUI_COUNT=0

echo "SystemUI:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "systemui|statusbar|notification" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
    GUI_COUNT=$((GUI_COUNT + 1))
done
echo "" >> "$LOGFILE"

echo "Launchers:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "launcher|home" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
    GUI_COUNT=$((GUI_COUNT + 1))
done
echo "" >> "$LOGFILE"

echo "Keyboards:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "keyboard|inputmethod|honeyboard" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
    GUI_COUNT=$((GUI_COUNT + 1))
done
echo "" >> "$LOGFILE"

# ====================================================================
# 2. Samsung Services
# ====================================================================

echo "=========================================" | tee -a "$LOGFILE"
echo "2. Samsung Services" | tee -a "$LOGFILE"
echo "=========================================" | tee -a "$LOGFILE"
echo "" >> "$LOGFILE"

echo "Bixby:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "bixby" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

echo "Knox:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "knox" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

echo "Samsung Account & Cloud:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "osp\.app|samsungaccount|scloud|samsungpass" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

echo "Samsung Pay:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "spay|pay\.stub" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

echo "Game Services:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "game" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

echo "Theme Store:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "theme" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

echo "Other Samsung Services:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "com\.samsung\.android\.(app|service)" "$PKGLIST" | \
    grep -v -E "wifi|bluetooth|nfc|settings|systemui|incallui|phone|contacts|messaging|dialer|camera|gallery|music|video|calendar|email|browser" | \
    while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

# ====================================================================
# 3. Google Services
# ====================================================================

echo "=========================================" | tee -a "$LOGFILE"
echo "3. Google Services" | tee -a "$LOGFILE"
echo "=========================================" | tee -a "$LOGFILE"
echo "" >> "$LOGFILE"

echo "Google Play Services:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "com\.google\.android\.gms|com\.google\.android\.gsf|com\.android\.vending" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

echo "Google Apps:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "com\.google\.android\.(apps|youtube|chrome)" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

# ====================================================================
# 4. Media & Entertainment
# ====================================================================

echo "=========================================" | tee -a "$LOGFILE"
echo "4. Media & Entertainment" | tee -a "$LOGFILE"
echo "=========================================" | tee -a "$LOGFILE"
echo "" >> "$LOGFILE"

echo "Music:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "music|soundalive|spotify" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

echo "Video:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "video|netflix" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

echo "Camera:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "camera" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

echo "Gallery:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "gallery" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

# ====================================================================
# 5. Communication
# ====================================================================

echo "=========================================" | tee -a "$LOGFILE"
echo "5. Communication" | tee -a "$LOGFILE"
echo "=========================================" | tee -a "$LOGFILE"
echo "" >> "$LOGFILE"

echo "Phone & Dialer:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "phone|dialer|incallui" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

echo "Messaging:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "messaging|mms|sms" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

echo "Contacts:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "contacts" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

echo "Email:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "email" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

# ====================================================================
# 6. Productivity
# ====================================================================

echo "=========================================" | tee -a "$LOGFILE"
echo "6. Productivity" | tee -a "$LOGFILE"
echo "=========================================" | tee -a "$LOGFILE"
echo "" >> "$LOGFILE"

echo "Browser:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "browser|chrome" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

echo "Calendar:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "calendar" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

echo "Notes & Memo:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "notes|memo" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

echo "File Manager:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "myfiles|filemanager" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

# ====================================================================
# 7. System & Essential (⚠️ DO NOT DISABLE)
# ====================================================================

echo "=========================================" | tee -a "$LOGFILE"
echo "7. System & Essential (DO NOT TOUCH)" | tee -a "$LOGFILE"
echo "=========================================" | tee -a "$LOGFILE"
echo "" >> "$LOGFILE"

echo "Core System:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "^com\.android\.server|^android$|^com\.android\.providers" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg (ESSENTIAL)" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

echo "Settings:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "settings" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg (ESSENTIAL)" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

echo "WiFi & Network:" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"
grep -E "wifi|bluetooth|nfc" "$PKGLIST" | while read -r pkg; do
    echo "  - $pkg (ESSENTIAL)" >> "$LOGFILE"
done
echo "" >> "$LOGFILE"

# ====================================================================
# 결과 요약
# ====================================================================

echo "" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "Scan Completed" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "Finished: $(date)" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "Total packages scanned: $TOTAL_COUNT" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "Category breakdown:" >> "$LOGFILE"
echo "1. GUI Components: $(grep -E "systemui|launcher|keyboard|inputmethod|honeyboard" "$PKGLIST" | wc -l)" >> "$LOGFILE"
echo "2. Samsung Services: $(grep -E "bixby|knox|osp\.app|scloud|spay|game|theme" "$PKGLIST" | wc -l)" >> "$LOGFILE"
echo "3. Google Services: $(grep -E "com\.google\." "$PKGLIST" | wc -l)" >> "$LOGFILE"
echo "4. Media: $(grep -E "music|video|camera|gallery" "$PKGLIST" | wc -l)" >> "$LOGFILE"
echo "5. Communication: $(grep -E "phone|dialer|messaging|contacts|email" "$PKGLIST" | wc -l)" >> "$LOGFILE"
echo "6. Productivity: $(grep -E "browser|calendar|notes|memo|myfiles" "$PKGLIST" | wc -l)" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "Full package list saved to: $PKGLIST" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# 화면 출력
# ====================================================================

echo ""
echo "========================================="
echo "Package Scan Summary"
echo "========================================="
echo ""
echo "Total packages: $TOTAL_COUNT"
echo ""
echo "Category breakdown:"
echo "1. GUI: $(grep -E "systemui|launcher|keyboard|inputmethod|honeyboard" "$PKGLIST" | wc -l) packages"
echo "2. Samsung: $(grep -E "bixby|knox|osp\.app|scloud|spay|game|theme" "$PKGLIST" | wc -l) packages"
echo "3. Google: $(grep -E "com\.google\." "$PKGLIST" | wc -l) packages"
echo "4. Media: $(grep -E "music|video|camera|gallery" "$PKGLIST" | wc -l) packages"
echo "5. Communication: $(grep -E "phone|dialer|messaging|contacts|email" "$PKGLIST" | wc -l) packages"
echo "6. Productivity: $(grep -E "browser|calendar|notes|memo|myfiles" "$PKGLIST" | wc -l) packages"
echo ""
echo "Full report: $LOGFILE"
echo "Package list: $PKGLIST"
echo ""
echo "Next steps:"
echo "1. Review the detailed report:"
echo "   adb pull /data/local/tmp/package_scan.log ./package_scan.log"
echo "   cat package_scan.log"
echo ""
echo "2. Review the package list:"
echo "   adb pull /data/local/tmp/package_list.txt ./package_list.txt"
echo "   cat package_list.txt"
echo ""
echo "3. Adjust disable scripts based on actual packages"
echo ""
