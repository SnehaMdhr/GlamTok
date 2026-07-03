from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import re
import json
from datetime import datetime, timezone
BUSINESS_USERNAMES = [
    "lambdafashion",
    "shibistyling",
    "prasuna.np",
    "naqabs786",
    "ktmcty",
    "trendzbiz_women",
    "reve.np",
    "warsa__",
    "ajmera.nepali",
    "topshopkathmandu1",
    "officialpranucollection",
]
OUTPUT_FILE = "tiktok_data1.xlsx"
CUTOFF_DATE = datetime(2024, 1, 1, tzinfo=timezone.utc)
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver
def parse_number(text: str) -> int:
    if not text:
        return 0
    text = str(text).strip().replace(",", "").replace(" ", "").upper()
    multiplier = 1
    if text.endswith("M"):
        multiplier = 1_000_000
        text = text[:-1]
    elif text.endswith("K"):
        multiplier = 1_000
        text = text[:-1]
    try:
        return max(0, int(float(text) * multiplier)) if text else 0
    except ValueError:
        return 0
def wait_for_page_data(driver, timeout=15) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        src = driver.page_source
        if '"createTime"' in src or '"create_time"' in src:
            return src
        time.sleep(1)
    return driver.page_source
def extract_from_universal_data(page_source: str, video_url: str) -> dict:
    result = {
        "likes": 0, "comments": 0, "shares": 0,
        "views": 0, "saves": 0, "duration": 0,
        "hashtag_count": 0, "caption_length": 0,
        "post_time": None,
    }
    try:
        match = re.search(
            r'<script[^>]*id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
            page_source, re.DOTALL
        )
        if not match:
            match = re.search(
                r'window\.__UNIVERSAL_DATA_FOR_REHYDRATION__\s*=\s*(\{.*?\});',
                page_source, re.DOTALL
            )
        if match:
            raw_json = match.group(1)
            data = json.loads(raw_json)
            default_scope = data.get("__DEFAULT_SCOPE__", {})
            video_detail  = default_scope.get("webapp.video-detail", {})
            item_info     = video_detail.get("itemInfo", {})
            item          = item_info.get("itemStruct", {})
            if item:
                stats = item.get("stats", item.get("statsV2", {}))
                result["likes"]    = int(stats.get("diggCount",    0))
                result["comments"] = int(stats.get("commentCount", 0))
                result["shares"]   = int(stats.get("shareCount",   0))
                result["views"]    = int(stats.get("playCount",    0))
                result["saves"]    = int(stats.get("collectCount", 0))
                video_info = item.get("video", {})
                result["duration"] = int(video_info.get("duration", 0))
                create_time = item.get("createTime", 0)
                if create_time:
                    ts = int(create_time)
                    if ts > 1e12:
                        ts = ts // 1000
                    result["post_time"] = datetime.fromtimestamp(ts, tz=timezone.utc)
                desc = item.get("desc", "")
                result["caption_length"] = len(desc)
                result["hashtag_count"]  = len(re.findall(r"#\w+", desc))
                return result
    except Exception as e:
        pass
    return result
def extract_by_regex_first(page_source: str) -> dict:
    result = {
        "likes": 0, "comments": 0, "shares": 0,
        "views": 0, "saves": 0, "duration": 0,
        "hashtag_count": 0, "caption_length": 0,
        "post_time": None,
    }
    field_patterns = {
        "likes":    r'"diggCount"\s*:\s*(\d+)',
        "comments": r'"commentCount"\s*:\s*(\d+)',
        "shares":   r'"shareCount"\s*:\s*(\d+)',
        "views":    r'"playCount"\s*:\s*(\d+)',
        "saves":    r'"collectCount"\s*:\s*(\d+)',
        "duration": r'"duration"\s*:\s*(\d+)',
    }
    for field, pattern in field_patterns.items():
        m = re.search(pattern, page_source)
        if m:
            result[field] = int(m.group(1))
    for pattern in [
        r'"createTime"\s*:\s*"?(\d{10})"?',
        r'"create_time"\s*:\s*"?(\d{10})"?',
        r'"createTime"\s*:\s*"?(\d{13})"?',
    ]:
        m = re.search(pattern, page_source)
        if m:
            ts = int(m.group(1))
            if ts > 1e12:
                ts = ts // 1000
            if 1_500_000_000 < ts < 2_000_000_000:
                result["post_time"] = datetime.fromtimestamp(ts, tz=timezone.utc)
                break
    m = re.search(r'"desc"\s*:\s*"([^"]{5,})"', page_source)
    if m:
        caption = m.group(1)
        result["caption_length"] = len(caption)
        result["hashtag_count"]  = len(re.findall(r"#\w+", caption))
    return result
def extract_video_data(page_source: str, video_url: str) -> dict:
    data = extract_from_universal_data(page_source, video_url)
    if data["post_time"] is not None and data["likes"] >= 0:
        return data
    return extract_by_regex_first(page_source)
def get_followers(driver) -> int:
    try:
        els = driver.find_elements(By.XPATH, "//*[contains(text(),'Followers')]")
        for el in els:
            m = re.search(r"([\d.]+[KMkm]?)\s*Followers", el.text)
            if m:
                return parse_number(m.group(1))
    except:
        pass
    try:
        els = driver.find_elements(By.XPATH, "//strong | //span")
        numbers = []
        for el in els:
            t = el.text.strip()
            if re.match(r"^[\d.,]+[KMkm]?$", t):
                numbers.append(parse_number(t))
        if len(numbers) >= 2:
            return numbers[1]
    except:
        pass
    return 0
def collect_video_links(driver, username: str) -> list:
    post_links   = []
    seen         = set()
    no_new_count = 0
    print(f"  Collecting video links )...")
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
    except:
        pass
    time.sleep(3)
    for scroll_attempt in range(30):
        anchors = driver.find_elements(By.XPATH, "//a[contains(@href,'/video/')]")
        if not anchors:
            anchors = driver.find_elements(By.XPATH,
                f"//a[contains(@href,'@{username}')]")
        if not anchors:
            anchors = driver.find_elements(By.TAG_NAME, "a")
        new_found = 0
        for a in anchors:
            try:
                href = a.get_attribute("href") or ""
                if "/video/" in href and href not in seen:
                    seen.add(href)
                    post_links.append(href)
                    new_found += 1
            except:
                continue
        if new_found > 0:
            print(f"    Scroll {scroll_attempt+1}: {len(post_links)} links collected")
            no_new_count = 0
        else:
            no_new_count += 1
        if no_new_count >= 6:
            print(f"    No new links after {no_new_count} attempts - stopping")
            break
        driver.execute_script("window.scrollBy(0, 600);")
        time.sleep(1.5)
        if scroll_attempt % 5 == 4:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
    if not post_links:
        print("  Trying page source extraction...")
        src = driver.page_source
        video_ids = re.findall(r'"id"\s*:\s*"(\d{15,20})"', src)
        for vid_id in set(video_ids):
            link = f"https://www.tiktok.com/@{username}/video/{vid_id}"
            if link not in seen:
                seen.add(link)
                post_links.append(link)
        if post_links:
            print(f"  Found {len(post_links)} links via page source")
    print(f"  Total: {len(post_links)} video links found")
    return post_links
def scrape_tiktok():
    print("Opening Chrome...")
    driver    = setup_driver()
    all_posts = []
    for username in BUSINESS_USERNAMES:
        print(f"\n{'='*50}")
        print(f"Scraping TikTok: @{username}")
        print(f"{'='*50}")
        try:
            driver.get(f"https://www.tiktok.com/@{username}")
            time.sleep(5)
            followers = get_followers(driver)
            print(f"  Followers: {followers:,}")
            post_links = collect_video_links(driver, username)
            if not post_links:
                print(f"   No videos found for @{username} - skipping")
                continue
            posts_saved = 0
            for i, link in enumerate(post_links):
                try:
                    driver.get(link)
                    try:
                        WebDriverWait(driver, 8).until(
                            EC.presence_of_element_located((By.TAG_NAME, "video"))
                        )
                    except:
                        pass
                    page_source = wait_for_page_data(driver, timeout=15)
                    data = extract_video_data(page_source, link)
                    post_time = data["post_time"]
                    if post_time is None:
                        print(f"  [{i+1}]  No timestamp - skipping")
                        continue
                    if post_time < CUTOFF_DATE:
                        print(f"  [{i+1}] {post_time.strftime('%Y-%m-%d')} is before cutoff.")
                        print("  Moving to next account...")
                        break
                    likes      = data["likes"]
                    comments   = data["comments"]
                    shares     = data["shares"]
                    views      = data["views"]
                    saves      = data["saves"]
                    engagement = likes + comments + shares + saves
                    eng_rate   = round((engagement / followers * 100), 4) if followers > 0 else 0
                    all_posts.append({
                        "Platform":           "TikTok",
                        "Business":           username,
                        "Followers":          followers,
                        "Post_Date":          post_time.strftime("%Y-%m-%d"),
                        "Post_Time":          post_time.strftime("%H:%M"),
                        "Hour":               post_time.hour,
                        "Minute":             post_time.minute,
                        "Day_of_Week":        post_time.strftime("%A"),
                        "Day_Number":         post_time.weekday(),
                        "Month":              post_time.strftime("%B"),
                        "Views":              views,
                        "Likes":              likes,
                        "Comments":           comments,
                        "Shares":             shares,
                        "Saves":              saves,
                        "Total_Engagement":   engagement,
                        "Engagement_Rate_%":  eng_rate,
                        "Content_Type":       "Video",
                        "Video_Duration_Sec": data["duration"],
                        "Caption_Length":     data["caption_length"],
                        "Hashtag_Count":      data["hashtag_count"],
                        "Post_URL":           link,
                    })
                    posts_saved += 1
                    print(f"  [{i+1}/{len(post_links)}] "
                          f"{post_time.strftime('%Y-%m-%d %H:%M')} | "
                          f"Views: {views:,} | Likes: {likes:,} | "
                          f"Comments: {comments} | Shares: {shares}")
                    time.sleep(2)
                except Exception as e:
                    print(f"  [{i+1}] ERROR: {e}")
                    continue
            print(f"   Done: {posts_saved} videos saved for @{username}")
        except Exception as e:
            print(f"  ERROR on @{username}: {e}")
        time.sleep(5)
    driver.quit()
    if all_posts:
        df = pd.DataFrame(all_posts)
        try:
            df.to_excel(OUTPUT_FILE, index=False)
            excel_file = OUTPUT_FILE
        except PermissionError:
            from datetime import datetime as dt
            timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
            excel_file = f"tiktok_data_{timestamp}.i wantx"
            df.to_excel(excel_file, index=False)
            print(f"  Main file locked. Saved to: {excel_file}")
        try:
            df.to_csv("tiktok_data.csv", index=False)
        except:
            pass
        print(f"\n{'='*50}")
        print(f" SUCCESS! Saved {len(df)} videos -> {excel_file}")
        print(f"{'='*50}")
        print(df[["Business","Post_Date","Post_Time",
                   "Views","Likes","Comments","Shares"]].head(15))
    else:
        print("\n No data collected.")
if __name__ == "__main__":
    scrape_tiktok()