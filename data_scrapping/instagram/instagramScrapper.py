from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
from datetime import datetime, timezone
import re
BUSINESS_USERNAMES = [
    "avsaa_collection",
]
OUTPUT_FILE = "instagram_data.xlsx"
DEBUG_MODE = False
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
def wait_for_manual_login(driver):
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(3)
    print("\n" + "="*50)
    print("Please LOGIN manually in the Chrome window.")
    print("Navigate to your Instagram Home screen to begin scraping.")
    print("Checking every 5 seconds... (waiting indefinitely)\n")
    checks = 0
    while True:
        time.sleep(5)
        url = driver.current_url
        checks += 1
        is_logged_in = (
            "instagram.com" in url
            and "login" not in url
            and "accounts" not in url
            and "challenge" not in url
        )
        is_home_screen = url in ["https://www.instagram.com/", "https://www.instagram.com"]
        if is_logged_in:
            print(f" Login detected at {url}")
            time.sleep(3)
            for _ in range(2):
                try:
                    btn = driver.find_element(By.XPATH,
                        "//button[text()='Not Now' or text()='Not now']")
                    btn.click()
                    time.sleep(2)
                except:
                    break
            if is_home_screen:
                print(" You are on the Home screen! Starting scraper...\n")
                return
            else:
                print(f"... Please navigate to your Home screen (currently at: {url})")
        if checks % 6 == 0:
            print(f"  Waiting... {checks * 5}s elapsed")
def parse_count(raw: str) -> int:
    if not raw:
        return 0
    raw = raw.strip().replace(",", "").replace(" ", "").replace("-", "-")
    if raw.startswith("-"):
        raw = raw[1:]
    multiplier = 1
    if raw.upper().endswith("M"):
        multiplier = 1_000_000
        raw = raw[:-1]
    elif raw.upper().endswith("K"):
        multiplier = 1_000
        raw = raw[:-1]
    if not raw:
        return 0
    try:
        result = int(float(raw) * multiplier)
        return max(0, result)
    except ValueError:
        return 0
def debug_save_page(driver, post_num: int, username: str):
    if not DEBUG_MODE:
        return
    try:
        src = driver.page_source
        filename = f"debug_post_{username}_{post_num}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(src)
        print(f"    [DEBUG] Saved page source to {filename}")
    except:
        pass
def navigate_and_wait(driver, url: str) -> bool:
    driver.get(url)
    try:
        shortcode = url.rstrip("/").split("/")[-1]
        WebDriverWait(driver, 10).until(
            lambda d: shortcode in d.current_url
        )
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "time"))
        )
        WebDriverWait(driver, 8).until(
            lambda d: any(
                re.search(r'\b(like|comment|view)', (el.get_attribute("aria-label") or ""), re.IGNORECASE)
                for el in d.find_elements(By.XPATH, "//*[@aria-label]")
                if el.get_attribute("aria-label")
            )
        )
        time.sleep(3)
        return True
    except Exception as e:
        time.sleep(5)
        return False
def extract_from_json(driver) -> dict:
    src = driver.page_source
    data = {"likes": 0, "comments": 0, "shares": 0, "views": 0}
    meta_pattern = r'(\d+)\s+likes?,\s+(\d+)\s+comments?'
    meta_match = re.search(meta_pattern, src)
    if meta_match:
        data["likes"] = int(meta_match.group(1))
        data["comments"] = int(meta_match.group(2))
        if DEBUG_MODE:
            print(f"      [DEBUG] Found via meta pattern: likes={data['likes']}, comments={data['comments']}")
        return data
    og_pattern = r'<meta\s+property="og:description"\s+content="([^"]*likes[^"]*)"'
    og_match = re.search(og_pattern, src)
    if og_match:
        og_content = og_match.group(1)
        if DEBUG_MODE:
            print(f"      [DEBUG] Found og:description: {og_content}")
        likes_m = re.search(r'(\d+)\s+likes?', og_content, re.IGNORECASE)
        comments_m = re.search(r'(\d+)\s+comments?', og_content, re.IGNORECASE)
        if likes_m:
            data["likes"] = int(likes_m.group(1))
        if comments_m:
            data["comments"] = int(comments_m.group(1))
        if DEBUG_MODE:
            print(f"      [DEBUG] Extracted from og: likes={data['likes']}, comments={data['comments']}")
        return data
    desc_pattern = r'<meta\s+name="description"\s+content="([^"]*likes[^"]*)"'
    desc_match = re.search(desc_pattern, src)
    if desc_match:
        desc_content = desc_match.group(1)
        if DEBUG_MODE:
            print(f"      [DEBUG] Found description meta: {desc_content}")
        likes_m = re.search(r'(\d+)\s+likes?', desc_content, re.IGNORECASE)
        comments_m = re.search(r'(\d+)\s+comments?', desc_content, re.IGNORECASE)
        if likes_m:
            data["likes"] = int(likes_m.group(1))
        if comments_m:
            data["comments"] = int(comments_m.group(1))
        if DEBUG_MODE:
            print(f"      [DEBUG] Extracted from description: likes={data['likes']}, comments={data['comments']}")
        return data
    if DEBUG_MODE:
        print(f"      [DEBUG] No meta tags found, trying JSON fallback...")
        print(f"      [DEBUG] Page source preview: {src[:100]}")
    patterns = {
        "likes": [r'"like_count"\s*:\s*(\d+)', r'"likes"\s*:\s*\{\s*"count"\s*:\s*(\d+)'],
        "comments": [r'"comment_count"\s*:\s*(\d+)', r'"comments"\s*:\s*\{\s*"count"\s*:\s*(\d+)'],
        "shares": [r'"share_count"\s*:\s*(\d+)'],
        "views": [r'"play_count"\s*:\s*(\d+)', r'"view_count"\s*:\s*(\d+)'],
    }
    for field, pats in patterns.items():
        for pat in pats:
            matches = re.findall(pat, src)
            if matches:
                best = max(int(m) for m in matches)
                if best > 0:
                    data[field] = best
                    if DEBUG_MODE:
                        print(f"      [DEBUG] Found {field} via JSON: {best}")
                    break
    return data
def get_likes(driver, json_data: dict) -> int:
    if DEBUG_MODE:
        print(f"      [DEBUG] Starting get_likes() - looking for text content with like counts")
    try:
        all_text_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'like') or (normalize-space(text()) and string-length(normalize-space(text())) < 10)]")
        if DEBUG_MODE:
            print(f"      [DEBUG] Found {len(all_text_elements)} potential text elements")
        found_numbers = []
        for el in all_text_elements:
            text = el.text.strip()
            if text:
                m = re.search(r'([\d.]+\s*[KkMm]?)\s*likes?', text, re.IGNORECASE)
                if m:
                    val = parse_count(m.group(1))
                    found_numbers.append(val)
                    if DEBUG_MODE:
                        print(f"      [DEBUG] Found text '{text}' -> {val} likes")
                elif re.match(r'^[\d.]+\s*[KkMm]?$', text):
                    val = parse_count(text)
                    found_numbers.append(val)
                    if DEBUG_MODE:
                        print(f"      [DEBUG] Found number '{text}' -> {val}")
        if found_numbers:
            best = max(found_numbers)
            if DEBUG_MODE:
                print(f"      [DEBUG] Selected max from text elements: {best}")
            if best > 0:
                return best
    except Exception as e:
        if DEBUG_MODE:
            print(f"      [DEBUG] Exception in text content extraction: {type(e).__name__}: {e}")
    if json_data.get("likes", 0) > 0:
        if DEBUG_MODE:
            print(f"      [DEBUG] Using cached meta data for likes: {json_data['likes']}")
        return json_data["likes"]
    if DEBUG_MODE:
        print(f"      [DEBUG] No likes found - returning 0")
    return 0
def get_comments(driver, json_data: dict) -> int:
    try:
        for el in driver.find_elements(By.XPATH, "//*[contains(text(), 'comment')]"):
            text = el.text.strip()
            m = re.search(r'([\d.]+\s*[KkMm]?)\s*comments?', text, re.IGNORECASE)
            if m:
                val = parse_count(m.group(1))
                if DEBUG_MODE:
                    print(f"      [DEBUG] Found comment text '{text}' -> {val}")
                if val > 0:
                    return val
        for el in driver.find_elements(By.XPATH,
                "//*[contains(text(),'View all') and contains(text(),'comment')]"):
            m = re.search(r"([\d.]+\s*[KkMm]?)", el.text)
            if m:
                val = parse_count(m.group(1))
                if DEBUG_MODE:
                    print(f"      [DEBUG] Found 'View all' text '{el.text}' -> {val}")
                return val
    except:
        pass
    if json_data.get("comments", 0) > 0:
        if DEBUG_MODE:
            print(f"      [DEBUG] Using cached meta data for comments: {json_data['comments']}")
        return json_data["comments"]
    if DEBUG_MODE:
        print(f"      [DEBUG] No comments found - returning 0")
    return 0
def get_shares(driver, json_data: dict) -> int:
    if json_data.get("shares", 0) > 0:
        return json_data["shares"]
    return 0
def get_views(driver, json_data: dict) -> int:
    if json_data.get("views", 0) > 0:
        return json_data["views"]
    try:
        for el in driver.find_elements(By.XPATH, "//*[@aria-label]"):
            label = (el.get_attribute("aria-label") or "").strip()
            if re.search(r"\bview", label, re.IGNORECASE) and "like" not in label.lower():
                m = re.search(r"([\d,]+\.?\d*\s*[KkMm]?)\s*(?:people?|user)?.*view", label, re.IGNORECASE)
                if m:
                    val = parse_count(m.group(1))
                    if val > 0:
                        return val
    except:
        pass
    try:
        for el in driver.find_elements(By.XPATH,
                "//*[contains(text(),'view') or contains(text(),'View')]"):
            text = el.text.strip()
            m = re.match(r"^([\d,]+\.?\d*\s*[KkMm]?)\s+views?", text, re.IGNORECASE)
            if m:
                val = parse_count(m.group(1))
                if val > 0:
                    return val
    except:
        pass
    return 0
def get_post_time(driver) -> datetime:
    try:
        time_el = driver.find_element(By.TAG_NAME, "time")
        dt_str  = time_el.get_attribute("datetime")
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except:
        return datetime.now(timezone.utc)
def get_content_type(driver, url: str) -> str:
    if "/reel/" in url:
        return "Reel"
    try:
        if driver.find_elements(By.XPATH, "//video"):
            return "Video"
        if driver.find_elements(By.XPATH,
                "//button[@aria-label='Next'] | //button[@aria-label='next']"):
            return "Carousel"
    except:
        pass
    return "Image"
def get_caption(driver) -> str:
    try:
        caption_els = driver.find_elements(By.XPATH,
            "//article//span[contains(@class, 'html')] | //article//h1/../following-sibling::*//span")
        for el in caption_els:
            text = el.text.strip()
            if text and len(text) > 5:
                return text
        article = driver.find_element(By.XPATH, "//article | //main")
        return article.text.strip() if article else ""
    except:
        return ""
def count_hashtags(caption: str) -> int:
    if not caption:
        return 0
    return len(re.findall(r'#\w+', caption))
def get_followers(driver) -> int:
    try:
        for span in driver.find_elements(By.XPATH, "//span[@title]"):
            title = span.get_attribute("title").replace(",", "").replace(".", "")
            if title.isdigit():
                return int(title)
    except:
        pass
    try:
        el  = driver.find_element(By.XPATH, "//a[contains(@href,'followers')]//span")
        val = (el.get_attribute("title") or el.text).replace(",","").replace(".","").strip()
        if val.isdigit():
            return int(val)
    except:
        pass
    return 0
def get_post_count(driver) -> int:
    try:
        for el in driver.find_elements(By.XPATH,
                "//*[contains(translate(text(),'POSTS','posts'),'posts')]"):
            m = re.match(r"^([\d,]+)\s+posts?", el.text.strip(), re.IGNORECASE)
            if m:
                return parse_count(m.group(1))
    except:
        pass
    try:
        for span in driver.find_elements(By.XPATH,
                "//header//li//span | //header//ul//span"):
            txt = (span.get_attribute("title") or span.text or "").strip()
            if txt.replace(",", "").isdigit():
                val = parse_count(txt)
                if val > 0:
                    return val
    except:
        pass
    return 0
def collect_post_links(driver, target: int) -> list[str]:
    post_links   = []
    seen         = set()
    no_new_count = 0
    MAX_NO_NEW   = 8
    print(f"  Scrolling to collect {target} post/reel links...")
    while len(post_links) < target and no_new_count < MAX_NO_NEW:
        anchors   = driver.find_elements(By.XPATH,
            "//a[contains(@href,'/p/') or contains(@href,'/reel/')]")
        new_found = 0
        for a in anchors:
            href = a.get_attribute("href")
            if href and href not in seen and ("/p/" in href or "/reel/" in href):
                seen.add(href)
                post_links.append(href)
                new_found += 1
        if new_found == 0:
            no_new_count += 1
        else:
            no_new_count = 0
            print(f"    {len(post_links)}/{target} links collected...")
        driver.execute_script("window.scrollBy(0, 900);")
        time.sleep(2)
        if no_new_count % 3 == 0:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
    if len(post_links) < target:
        print(f"   Collected {len(post_links)} (profile shows {target}).")
    else:
        print(f"   Collected all {len(post_links)} links.")
    return post_links[:target]
def scrape_instagram():
    print("Opening Chrome...")
    driver    = setup_driver()
    all_posts = []
    wait_for_manual_login(driver)
    for username in BUSINESS_USERNAMES:
        print(f"\n{'='*50}")
        print(f"Scraping: @{username}")
        print(f"{'='*50}")
        try:
            driver.get(f"https://www.instagram.com/{username}/")
            time.sleep(5)
            followers   = get_followers(driver)
            total_posts = get_post_count(driver)
            print(f"  Followers  : {followers:,}")
            print(f"  Total posts: {total_posts}")
            if total_posts == 0:
                print("  Could not read post count - skipping.")
                continue
            target_posts = min(total_posts, 2000)
            post_links  = collect_post_links(driver, target_posts)
            posts_saved = 0
            for i, link in enumerate(post_links):
                try:
                    loaded = navigate_and_wait(driver, link)
                    if not loaded:
                        print(f"  [{i+1}]  Page load timeout, scraping anyway...")
                    json_data    = extract_from_json(driver)
                    if DEBUG_MODE and i < 3:
                        debug_save_page(driver, i+1, username)
                    post_time    = get_post_time(driver)
                    cutoff_date = datetime(2025, 11, 19, tzinfo=timezone.utc)
                    if post_time < cutoff_date:
                        print(f"  [{i+1}] Post from {post_time.strftime('%Y-%m-%d')} is older than Nov 19, 2025. Moving to next business...")
                        break
                    likes        = get_likes(driver, json_data)
                    comments     = get_comments(driver, json_data)
                    shares       = get_shares(driver, json_data)
                    content_type = get_content_type(driver, link)
                    engagement   = likes + comments + shares
                    eng_rate     = round((engagement / followers * 100), 4) if followers > 0 else 0
                    all_posts.append({
                        "Platform":          "Instagram",
                        "Business":          username,
                        "Followers":         followers,
                        "Post_Date":         post_time.strftime("%Y-%m-%d"),
                        "Post_Time":         post_time.strftime("%H:%M"),
                        "Hour":              post_time.hour,
                        "Minute":            post_time.minute,
                        "Day_of_Week":       post_time.strftime("%A"),
                        "Day_Number":        post_time.weekday(),
                        "Month":             post_time.strftime("%B"),
                        "Likes":             likes,
                        "Comments":          comments,
                        "Shares":            shares,
                        "Total_Engagement":  engagement,
                        "Engagement_Rate_%": eng_rate,
                        "Content_Type":      content_type,
                        "Post_URL":          link,
                    })
                    posts_saved += 1
                    print(f"  [{i+1}/{len(post_links)}]  {post_time.strftime('%Y-%m-%d %H:%M')} | "
                          f"Likes: {likes} | Comments: {comments} | "
                          f"Shares: {shares} | {content_type}")
                except Exception as e:
                    print(f"  [{i+1}] ERROR: {e}")
                    continue
            print(f"  -> Done: {posts_saved}/{total_posts} posts saved for @{username}")
        except Exception as e:
            print(f"  ERROR on @{username}: {e}")
        time.sleep(5)
    driver.quit()
    if all_posts:
        df = pd.DataFrame(all_posts)
        from datetime import timedelta
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=180)).strftime("%Y-%m-%d")
        df = df[df["Post_Date"] >= cutoff_date]
        print(f"  Filtering to last 6 months (since {cutoff_date})...")
        df.to_excel(OUTPUT_FILE, index=False)
        df.to_csv("instagram_data.csv", index=False)
        print(f"\n Done! Saved {len(df)} posts (last 6 months) to {OUTPUT_FILE}")
        print(df[["Business","Post_Date","Likes","Comments","Shares","Content_Type"]].head(15))
    else:
        print("\nNo data collected.")
if __name__ == "__main__":
    scrape_instagram()