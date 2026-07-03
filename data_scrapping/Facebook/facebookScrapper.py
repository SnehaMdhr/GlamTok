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

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
BUSINESS_PAGES = [
    # Facebook page usernames or IDs (the part after facebook.com/)
    "profile.php?id=61557708038765",
]

MAX_POSTS   = 80
OUTPUT_FILE = "facebook_data.xlsx"
from datetime import timedelta
CUTOFF_DATE = datetime.now(tz=timezone.utc) - timedelta(days=183)

# Global flags for debug file saving
first_post_saved = False
first_reel_saved = False


# ─────────────────────────────────────────────
# DRIVER
# ─────────────────────────────────────────────
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # Enable logging of network responses
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    # Enable CDP network tracking
    driver.execute_cdp_cmd("Network.enable", {})
    return driver


# ─────────────────────────────────────────────
# MANUAL LOGIN
# Waits until the Facebook home feed is fully
# rendered - not just until the URL changes.
# ─────────────────────────────────────────────

# XPaths that only exist on a loaded home feed
_HOME_FEED_SIGNALS = [
    # Stories row (desktop)
    "//div[@aria-label='Stories']",
    # "What's on your mind?" composer
    "//*[contains(@aria-label=\"What's on your mind\")]",
    # Newsfeed navigation link (always present when logged in)
    "//a[@aria-label='Home']",
    # Left nav "Feed" label
    "//span[text()='Feed']",
    # Right-side "Sponsored" or ad rail (appears after full load)
    "//span[text()='Sponsored']",
]

def _home_feed_loaded(driver) -> bool:
    """Return True only when the home feed DOM is actually rendered and user is LOGGED IN."""
    url = driver.current_url
    
    # Must be on facebook.com home and NOT on login/checkpoint/recover pages
    if not ("facebook.com" in url
            and "login"      not in url
            and "checkpoint" not in url
            and "recover"    not in url
            and "signup"     not in url):
        return False
    
    # If redirected to /feed or /home, likely logged in
    if "/feed" in url or "/home" in url or url == "https://www.facebook.com/":
        # Additional check: look for logged-in profile/name indicators
        try:
            src = driver.page_source
            # Check for presence of user profile data or navigation
            if ('aria-label="Your profile"' in src or 
                'aria-label="Account"' in src or
                'data-testid="royal_header_profile_icon"' in src or
                '"isLoggedIn":true' in src or
                'id="navLabel_' in src):  # FB nav elements only appear when logged in
                return True
        except:
            pass

    # Check for at least TWO home-feed DOM signals (stricter check)
    signal_count = 0
    for xpath in _HOME_FEED_SIGNALS:
        try:
            els = driver.find_elements(By.XPATH, xpath)
            if els:
                signal_count += 1
        except:
            pass
    
    if signal_count >= 2:
        return True

    return False


def wait_for_manual_login(driver):
    driver.get("https://www.facebook.com/login")
    time.sleep(3)

    print("\n" + "="*50)
    print("Facebook login page is open in Chrome!")
    print("="*50)
    print("Please LOGIN manually:")
    print("  1. Enter your email/phone and password")
    print("  2. Complete any 2FA / CAPTCHA if asked")
    print("  3. Complete TWO-FACTOR AUTHENTICATION if prompted")
    print("  4. Wait for the Facebook HOME FEED to fully load")
    print("     (you should see Stories and the post composer)")
    print("="*50)
    print("Script checks every 5 seconds... (3 minutes max)\n")

    for i in range(36):
        time.sleep(5)
        if _home_feed_loaded(driver):
            print("\n" + "="*50)
            print("✅ HOME FEED LOADED! Login successful!")
            print("✅ All CAPTCHAs completed!")
            print("="*50)
            print("Waiting for full page rendering (5 seconds)...\n")
            time.sleep(5)   # longer pause for all JS and lazy-loaded content to settle
            
            print("="*50)
            print("🚀 SCRAPER STARTING NOW!")
            print("="*50 + "\n")
            return
        url = driver.current_url
        if "checkpoint" in url:
            print(f"  ⚠ Security checkpoint detected - please complete it in the browser...")
        else:
            print(f"  Waiting for home feed... {(i+1)*5}s")

    print("⚠ Timed out waiting for home feed - continuing anyway...\n")


# ─────────────────────────────────────────────
# NUMBER PARSER
# ─────────────────────────────────────────────
def parse_number(text: str) -> int:
    if not text:
        return 0
    text = str(text).strip().replace(",", "").replace(" ", "").replace("\u00a0", "").upper()
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
def scrape_reel_from_dom(driver) -> dict:
    """
    Scrapes reel engagement by reading the visible rendered text beside each
    action button - the only reliable source for shares/views on Reels.

    Facebook Reel layout (right-side panel, top→bottom):
        [Like icon]    <count>   ← reactions
        [Comment icon] <count>   ← comments
        [Share icon]   <count>   ← shares
    Views appear as overlay text directly on the video ("3.9K views").

    Strategy (in priority order):
      1. aria-label on the button/icon elements  (most reliable)
      2. Text node adjacent to each known button (catches what aria misses)
      3. Page-source JSON patterns               (fallback)
      4. Filtered span scan                      (last resort, no positional guessing)
    """
    result = {"likes": 0, "comments": 0, "shares": 0, "views": 0, "reactions": 0}
    KNOWN_UI_JUNK = {0, 16, 15}   # values confirmed to be UI constants, not real counts

    print("    [REEL-DOM] Starting reel metric extraction...")

    try:
        driver.execute_script("window.scrollBy(0, 100);")
        time.sleep(1.5)
    except:
        pass

    page_source = driver.page_source

    # ── PASS 1: aria-label on ALL elements ───────────────────────────────────
    # FB puts counts in aria-labels like:
    #   "1.2K people reacted"  · "Like: 1.2K"
    #   "455 comments"         · "Comment: 455"
    #   "43 shares"            · "Share: 43"
    #   "3.9K views"           · "3,900 plays"
    try:
        for el in driver.find_elements(By.XPATH, "//*[@aria-label]"):
            aria = (el.get_attribute("aria-label") or "").strip()
            if not aria:
                continue

            if result["reactions"] == 0:
                m = (re.search(r'([\d,\.]+\s*[KMkm]?)\s*(?:people\s+react|reaction)', aria, re.I)
                     or re.search(r'(?:^|\b)like\b[^a-zA-Z]*?([\d,\.]+\s*[KMkm]?)', aria, re.I))
                if m:
                    v = parse_number(m.group(1))
                    if v > 0 and v not in KNOWN_UI_JUNK:
                        result["reactions"] = result["likes"] = v
                        print(f"    [REEL-DOM] ✓ reactions={v}  aria='{aria[:70]}'")

            if result["comments"] == 0:
                m = (re.search(r'([\d,\.]+\s*[KMkm]?)\s*comment', aria, re.I)
                     or re.search(r'(?:^|\b)comment\b[^a-zA-Z]*?([\d,\.]+\s*[KMkm]?)', aria, re.I))
                if m:
                    v = parse_number(m.group(1))
                    if v > 0 and v not in KNOWN_UI_JUNK:
                        result["comments"] = v
                        print(f"    [REEL-DOM] ✓ comments={v}  aria='{aria[:70]}'")

            if result["shares"] == 0:
                m = (re.search(r'([\d,\.]+\s*[KMkm]?)\s*share', aria, re.I)
                     or re.search(r'(?:^|\b)share\b[^a-zA-Z]*?([\d,\.]+\s*[KMkm]?)', aria, re.I))
                if m:
                    v = parse_number(m.group(1))
                    if v > 0 and v not in KNOWN_UI_JUNK:
                        result["shares"] = v
                        print(f"    [REEL-DOM] ✓ shares={v}  aria='{aria[:70]}'")

            if result["views"] == 0:
                m = re.search(r'([\d,\.]+\s*[KMkm]?)\s*(?:view|play|watch)', aria, re.I)
                if m:
                    v = parse_number(m.group(1))
                    if v > 0 and v not in KNOWN_UI_JUNK:
                        result["views"] = v
                        print(f"    [REEL-DOM] ✓ views={v}  aria='{aria[:70]}'")

    except Exception as e:
        print(f"    [REEL-DOM] aria pass failed: {e}")

    # ── PASS 2: sibling text-node scan beside action buttons ─────────────────
    # For each button whose aria-label names an action (like/comment/share),
    # look at the immediately following sibling <span> for the count text.
    # This catches cases where FB puts the count OUTSIDE the button element.
    BUTTON_XPATHS = {
        "reactions": [
            "//div[@aria-label[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'like')]]",
            "//span[@aria-label[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'like')]]",
        ],
        "comments": [
            "//div[@aria-label[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'comment')]]",
            "//span[@aria-label[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'comment')]]",
        ],
        "shares": [
            "//div[@aria-label[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'share')]]",
            "//span[@aria-label[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'share')]]",
        ],
    }

    for field, xpaths in BUTTON_XPATHS.items():
        if result[field] != 0:
            continue
        for xpath in xpaths:
            try:
                buttons = driver.find_elements(By.XPATH, xpath)
                for btn in buttons:
                    # Try the button's own text first
                    btn_text = btn.text.strip()
                    m = re.search(r'([\d,\.]+\s*[KMkm]?)', btn_text)
                    if m:
                        v = parse_number(m.group(1))
                        if v > 0 and v not in KNOWN_UI_JUNK:
                            result[field] = v
                            if field == "reactions":
                                result["likes"] = v
                            print(f"    [REEL-DOM] ✓ {field}={v}  button.text='{btn_text[:50]}'")
                            break

                    # Try following sibling spans (the count lives next to the icon)
                    siblings = driver.execute_script("""
                        var el = arguments[0];
                        var results = [];
                        var sib = el.nextElementSibling;
                        for (var i = 0; i < 3 && sib; i++) {
                            results.push(sib.innerText || sib.textContent || '');
                            sib = sib.nextElementSibling;
                        }
                        return results;
                    """, btn)
                    for sib_text in (siblings or []):
                        sib_text = (sib_text or "").strip()
                        if not sib_text:
                            continue
                        m = re.search(r'^([\d,\.]+\s*[KMkm]?)$', sib_text)
                        if m:
                            v = parse_number(m.group(1))
                            if v > 0 and v not in KNOWN_UI_JUNK:
                                result[field] = v
                                if field == "reactions":
                                    result["likes"] = v
                                print(f"    [REEL-DOM] ✓ {field}={v}  sibling='{sib_text}'")
                                break
                    if result[field] != 0:
                        break
            except Exception as e:
                print(f"    [REEL-DOM] sibling scan failed for {field}: {e}")
            if result[field] != 0:
                break

    # ── PASS 3: views overlay text on the video element ──────────────────────
    # Views are shown as overlay text ON the video (e.g. "3.9K views").
    # Check the video container's parent/sibling nodes and visible text near <video>.
    if result["views"] == 0:
        try:
            video_els = driver.find_elements(By.TAG_NAME, "video")
            for video in video_els:
                # Walk up to find the containing div, then search its text
                container_text = driver.execute_script("""
                    var el = arguments[0];
                    // walk up max 5 levels
                    for (var i = 0; i < 5; i++) {
                        el = el.parentElement;
                        if (!el) break;
                        var txt = el.innerText || '';
                        if (/[\\d][\\d,\\.]*\\s*[KMkm]?\\s*(view|play)/i.test(txt)) return txt;
                    }
                    return '';
                """, video)
                if container_text:
                    m = re.search(r'([\d,\.]+\s*[KMkm]?)\s*(?:view|play)', container_text, re.I)
                    if m:
                        v = parse_number(m.group(1))
                        if v > 0 and v not in KNOWN_UI_JUNK:
                            result["views"] = v
                            print(f"    [REEL-DOM] ✓ views={v}  video container text")
                            break
        except Exception as e:
            print(f"    [REEL-DOM] video container scan failed: {e}")

    # ── PASS 4: page-source JSON patterns ────────────────────────────────────
    # Only for fields still missing - fast regex over the raw HTML.
    JSON_PATTERNS = {
        "reactions": [
            r'"reaction_count"\s*:\s*\{"count"\s*:\s*(\d+)',
            r'"reactionCount"\s*:\s*(\d+)',
            r'"reaction_count"\s*:\s*(\d+)',
            r'"likeCount"\s*:\s*(\d+)',
            r'([\d,]+[KMkm]?)\s*people\s+react',
        ],
        "comments": [
            r'"comments"\s*:\s*\{"total_count"\s*:\s*(\d+)',
            r'"commentCount"\s*:\s*(\d+)',
            r'"comment_count"\s*:\s*(\d+)',
            r'([\d,]+[KMkm]?)\s*comment',
        ],
        "shares": [
            r'"share_count"\s*:\s*\{"count"\s*:\s*(\d+)',
            r'"shareCount"\s*:\s*(\d+)',
            r'"share_count"\s*:\s*(\d+)',
            r'"shares_count"\s*:\s*(\d+)',
            r'([\d,]+[KMkm]?)\s*share',
        ],
        "views": [
            r'"video_view_count"\s*:\s*(\d+)',
            r'"viewCount"\s*:\s*(\d+)',
            r'"view_count"\s*:\s*(\d+)',
            r'([\d,]+[KMkm]?)\s*view',
            r'([\d,]+[KMkm]?)\s*play',
        ],
    }

    for field, patterns in JSON_PATTERNS.items():
        if result[field] != 0:
            continue
        for pat in patterns:
            m = re.search(pat, page_source, re.I)
            if m:
                v = parse_number(m.group(1))
                if v > 0 and v not in KNOWN_UI_JUNK:
                    result[field] = v
                    if field == "reactions":
                        result["likes"] = v
                    print(f"    [REEL-DOM] ✓ {field}={v}  json pattern")
                    break

    # ── PASS 5: filtered span scan - absolute last resort ────────────────────
    # Only runs if all above passes failed for a field.
    # Completely avoids positional guessing - just collects clean numeric spans
    # in document order and tries to match them by their surrounding context.
    missing = [k for k in ("reactions", "comments", "shares", "views") if result[k] == 0]
    if missing:
        print(f"    [REEL-DOM] Last-resort span scan for: {missing}")
        try:
            # Collect spans that contain ONLY a number (with optional K/M suffix)
            # and whose parent element has an aria-label hinting at the metric
            spans = driver.find_elements(By.XPATH, "//span[normalize-space(text())]")
            for span in spans:
                try:
                    t = span.text.strip()
                    if not re.match(r'^[\d][\d,\.]*\s*[KMkm]?$', t):
                        continue
                    v = parse_number(t)
                    if v <= 0 or v in KNOWN_UI_JUNK or v < 10:
                        continue

                    # Check parent/ancestor for context clues
                    context = driver.execute_script("""
                        var el = arguments[0];
                        var texts = [];
                        for (var i = 0; i < 4; i++) {
                            el = el.parentElement;
                            if (!el) break;
                            var a = el.getAttribute('aria-label') || '';
                            if (a) texts.push(a.toLowerCase());
                        }
                        return texts.join(' ');
                    """, span)
                    context = (context or "").lower()

                    if "like" in context or "react" in context:
                        if result["reactions"] == 0:
                            result["reactions"] = result["likes"] = v
                            print(f"    [REEL-DOM] ✓ reactions={v}  span+context")
                    elif "comment" in context:
                        if result["comments"] == 0:
                            result["comments"] = v
                            print(f"    [REEL-DOM] ✓ comments={v}  span+context")
                    elif "share" in context:
                        if result["shares"] == 0:
                            result["shares"] = v
                            print(f"    [REEL-DOM] ✓ shares={v}  span+context")
                    elif "view" in context or "play" in context:
                        if result["views"] == 0:
                            result["views"] = v
                            print(f"    [REEL-DOM] ✓ views={v}  span+context")
                except:
                    continue
        except Exception as e:
            print(f"    [REEL-DOM] span scan failed: {e}")

    print(f"    [REEL-DOM] ✅ Final → reactions={result['reactions']}  "
          f"comments={result['comments']}  shares={result['shares']}  views={result['views']}")
    return result

def extract_reel_metrics_from_network(driver) -> dict:
    """Kept for compatibility - now just calls the DOM scraper."""
    return scrape_reel_from_dom(driver)# ─────────────────────────────────────────────
# GET PAGE FOLLOWERS / LIKES
# ─────────────────────────────────────────────
def get_followers(driver) -> int:
    """
    Tries several approaches to extract the follower/like count
    from a Facebook page's intro section.
    """
    page_source = driver.page_source
    
    # Method 1: Look in page source for JSON patterns with follower/fan count
    print(f"    [DEBUG] Searching for followers/likes count...")
    
    # Facebook stores counts in JSON like: "fan_count":1234 or similar
    json_patterns = [
        r'"fan_count"\s*:\s*(\d+)',
        r'"follower_count"\s*:\s*(\d+)',
        r'"followers"\s*:\s*(\d+)',
        r'"likes"\s*:\s*(\d+)',
        r'"like_count"\s*:\s*(\d+)',
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, page_source)
        if matches:
            # Get the largest number (usually the page count)
            for val_str in sorted(matches, key=int, reverse=True):
                val = int(val_str)
                if val > 100:  # Real follower counts are typically > 100
                    print(f"    [DEBUG] ✓ Followers found in page source (JSON): {val:,}")
                    return val
    
    # Method 2: DOM XPath selectors
    selectors = [
        # Modern layout - "X followers" text
        "//span[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'follower')]",
        # Older layout - "X people like this"
        "//span[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'people like')]",
        # Like/follow count in About section
        "//div[contains(@class,'x9f619')]//span[contains(text(),'like') or contains(text(),'follow')]",
        # Try generic span with numbers followed by follower/like keywords
        "//span[contains(., 'follower') or contains(., 'Follower') or contains(., 'like') or contains(., 'Like')]",
    ]

    for xpath in selectors:
        try:
            els = driver.find_elements(By.XPATH, xpath)
            for el in els:
                text = el.text.strip()
                m = re.search(r"([\d,. ]+[KMkm]?)\s*(?:follower|like|people)", text, re.IGNORECASE)
                if m:
                    val = parse_number(m.group(1))
                    if val > 100:
                        print(f"    [DEBUG] ✓ Followers found via DOM: {val:,}")
                        return val
        except:
            pass

    # Fallback 1: Look for large standalone numbers in the page header/About box
    try:
        candidates = driver.find_elements(
            By.XPATH,
            "//div[contains(@class,'x9f619') or contains(@class,'xu3j5b3')]//span"
        )
        for el in candidates:
            t = el.text.strip()
            if re.match(r"^[\d,.]+[KMkm]?$", t) and len(t) <= 12:
                val = parse_number(t)
                if val > 500:  # Real page follower counts are typically > 500
                    print(f"    [DEBUG] ✓ Followers found via large number: {val:,}")
                    return val
    except:
        pass

    # Fallback 2: Search page source for common patterns
    # Look for text like "12,345 people like this" or "12,345 followers"
    try:
        m = re.search(r"([\d,]+(?:\.\d+)?[KMkm]?)\s*(?:people\s+like|follower|fan)", page_source, re.IGNORECASE)
        if m:
            val = parse_number(m.group(1))
            if val > 100:
                print(f"    [DEBUG] ✓ Followers found via page source text: {val:,}")
                return val
    except:
        pass

    # Fallback 3: Look in meta tags for og:description which might contain follower info
    try:
        m = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', page_source)
        if m:
            desc = m.group(1)
            m = re.search(r"([\d,]+[KMkm]?)\s*(?:follower|like|fan)", desc, re.IGNORECASE)
            if m:
                val = parse_number(m.group(1))
                if val > 100:
                    print(f"    [DEBUG] ✓ Followers found in meta description: {val:,}")
                    return val
    except:
        pass

    print(f"    [DEBUG] ⚠ Followers count not found - returning 0")
    return 0

def debug_dump_reel_keywords(driver):
    """Dumps any line containing engagement-related keywords from network logs."""
    try:
        logs = driver.get_log("performance")
    except:
        return

    keywords = ["reaction", "comment", "share", "view", "like", "play", "count", "engagement"]
    found_lines = []

    for entry in logs:
        try:
            msg = json.loads(entry["message"])["message"]
            if msg.get("method") != "Network.responseReceived":
                continue
            url = msg.get("params", {}).get("response", {}).get("url", "")
            if not any(x in url.lower() for x in ["graphql", "ajax", "api"]):
                continue
            request_id = msg["params"]["requestId"]
            try:
                body = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id}).get("body", "")
                for line in body.splitlines():
                    line_lower = line.lower()
                    if any(kw in line_lower for kw in keywords):
                        found_lines.append(f"URL: {url[:80]}\nLINE: {line[:500]}\n")
            except:
                continue
        except:
            continue

    import os
    os.makedirs("facebook_debug_pages", exist_ok=True)
    with open("facebook_debug_pages/KEYWORD_DUMP.txt", "w", encoding="utf-8") as f:
        f.write(f"Total keyword-matching lines: {len(found_lines)}\n\n")
        for l in found_lines[:50]:  # first 50 matches
            f.write("="*60 + "\n")
            f.write(l + "\n")
    print(f"    [DUMP] Saved {len(found_lines)} keyword lines to KEYWORD_DUMP.txt")

# ─────────────────────────────────────────────
# NAVIGATE AND WAIT FOR POST TO LOAD
# ─────────────────────────────────────────────
def navigate_and_wait(driver, url: str, is_reel: bool = False) -> bool:
    if not url or not url.startswith("https://www.facebook.com/"):
        print(f"    [NAV] Skipping invalid URL: {url[:70]}")
        return False

    if not is_reel:
        try:
            driver.get_log("performance")
        except:
            pass

    try:
        driver.get(url)
    except Exception as e:
        print(f"    [NAV] driver.get() failed: {e}")
        return False

    try:
        # Extract a SAFE post_id - only use the path portion, never query strings
        # because query string values like "pfbid02Xs..." cause ChromeDriver crashes
        path_only = url.split("?")[0].rstrip("/")
        post_id   = path_only.split("/")[-1]

        # Final safety check: post_id must look like a real ID (digits or alphanumeric)
        # If it looks weird (e.g. empty, or "php"), fall back to just waiting for FB domain
        if not post_id or len(post_id) < 4 or post_id.endswith(".php"):
            post_id = "facebook.com"

        WebDriverWait(driver, 10).until(
            lambda d: "facebook.com" in d.current_url
        )

        if is_reel:
            try:
                WebDriverWait(driver, 12).until(
                    lambda d: (
                        d.find_elements(By.TAG_NAME, "video") or
                        d.find_elements(By.TAG_NAME, "time") or
                        "reel" in d.current_url.lower()
                    )
                )
            except:
                pass
            time.sleep(6)
        else:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "time"))
                )
            except:
                pass
            try:
                WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.TAG_NAME, "article"))
                )
            except:
                pass
            time.sleep(2)

        return True

    except Exception as e:
        time.sleep(3)
        try:
            if driver.find_elements(By.TAG_NAME, "time"):
                return True
            if is_reel and driver.find_elements(By.TAG_NAME, "video"):
                return True
        except:
            pass
        return False


# ─────────────────────────────────────────────
# COLLECT POST LINKS
# ─────────────────────────────────────────────
def collect_post_links(driver, page_name: str, max_posts: int) -> list:
    """
    Scrolls through the page's posts tab and collects unique post URLs.
    Facebook post URLs contain '/posts/', '/videos/', '/reel/', or '/photos/'.
    """
    post_links   = []
    seen         = set()
    no_new_count = 0

    print(f"  Collecting post links (target: {max_posts})...")

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
    except:
        pass
    time.sleep(3)

    # Facebook post URL patterns - STRICT to avoid help/info pages
    POST_PATTERNS = re.compile(
        r"https://www\.facebook\.com/(?!help|info|support|page|pages|groups|watch\?|photo\.php)([^/]+)/(?:posts|videos?|reel|reels|photos?|story|watch|permalink\.php|share)/[^\s\"'?]+",
        re.IGNORECASE
    )
    # Additional pattern for FB URLs with just ID (but not help pages)
    ALT_PATTERNS = re.compile(
        r"https://www\.facebook\.com/(?!help|info|support)(?:pages/)?([^/]+)/[0-9]+/?(?:\?|$)",
        re.IGNORECASE
    )

    for scroll_attempt in range(400):
        # Method 1: <a> tags
        anchors = driver.find_elements(By.TAG_NAME, "a")
        new_found = 0

        for a in anchors:
            try:
                href = a.get_attribute("href") or ""
                # Normalise - strip query strings
                href = href.split("?")[0].rstrip("/")
                
                # Try main pattern
                if POST_PATTERNS.match(href) and href not in seen:
                    # Deduplicate: skip /videos/ URL if we already have the /reel/ version
                    # Facebook creates both URLs for the same reel content
                    reel_equivalent = href.replace("/videos/", "/reel/")
                    if reel_equivalent in seen:
                        continue
                    seen.add(href)
                    post_links.append(href)
                    new_found += 1

                # Try alternative pattern for ID-based URLs
                elif ALT_PATTERNS.match(href) and href not in seen and "/photos/" not in href:
                    seen.add(href)
                    post_links.append(href)
                    new_found += 1
            except:
                continue

        # Method 2: Scan page source for post URLs
        if new_found == 0:
            src = driver.page_source
            found_urls = POST_PATTERNS.findall(src)
            for url in found_urls:
                url = url.split("?")[0].rstrip("/")
                if url not in seen:
                    seen.add(url)
                    post_links.append(url)
                    new_found += 1
            
            # Also try alternative patterns in page source
            if new_found < 3:
                alt_urls = ALT_PATTERNS.findall(src)
                for url in alt_urls:
                    url = url.split("?")[0].rstrip("/")
                    if url not in seen and "/photos/" not in url:
                        seen.add(url)
                        post_links.append(url)
                        new_found += 1

        if new_found > 0:
            print(f"    Scroll {scroll_attempt+1}: {len(post_links)} links collected ({new_found} new)")
            no_new_count = 0
        else:
            no_new_count += 1

        if len(post_links) >= max_posts:
            break

        if no_new_count >= 12:
            print(f"    No new links after {no_new_count} attempts - stopping")
            break

        driver.execute_script("window.scrollBy(0, 700);")
        
        # Slow down when FB isn't loading new content
        if no_new_count >= 6:
            time.sleep(4)
        else:
            time.sleep(2)

        if scroll_attempt % 5 == 4:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)

    print(f"  Total: {len(post_links)} post links found")
    return post_links[:max_posts]


# ─────────────────────────────────────────────
# DETERMINE CONTENT TYPE FROM URL
# ─────────────────────────────────────────────
def get_content_type(url: str, driver=None, page_source: str = "") -> str:
    """
    Determines content type from URL patterns and fallback page source analysis.
    Returns: "Video", "Reel", "Photo", or "Post"
    Priority: Photo > Reel > Video > Post
    """
    url_lower = url.lower()
    
    # PRIMARY: Check URL patterns (most reliable)
    # Check Photo FIRST (before video check)
    if "/photos/" in url_lower or "/photo/" in url_lower:
        print(f"    [TYPE] Detected 'Photo' from URL pattern")
        return "Photo"
    
    if "/reel/" in url_lower or "/reels/" in url_lower:
        print(f"    [TYPE] Detected 'Reel' from URL pattern")
        return "Reel"
    
    if "/videos/" in url_lower or "/video/" in url_lower:
        print(f"    [TYPE] Detected 'Video' from URL pattern")
        return "Video"
    
    # SECONDARY: Check page source for more specific indicators
    if page_source:
        page_lower = page_source.lower()
        
        # Check for image/photo indicators FIRST
        if '"__typename":"photo"' in page_lower or '"__typename":"image"' in page_lower:
            print(f"    [TYPE] Detected 'Photo' from page source")
            return "Photo"
        
        # Check if it's specifically a reel (not just any video)
        # Reels have specific reel_tv or InstagramReel type indicators
        if '"reels_tv"' in page_lower or '"instagramreel"' in page_lower or '"__typename":"reels_tv_video"' in page_lower:
            print(f"    [TYPE] Detected 'Reel' from page source (reel_tv)")
            return "Reel"
        
        # Check for general video indicators
        if '"video"' in page_lower or '"__typename":"video"' in page_lower or '<video' in page_lower:
            # Make sure it's not a photo carousel
            if 'carousel' not in page_lower or 'video' in page_lower:
                print(f"    [TYPE] Detected 'Video' from page source (video element)")
                return "Video"
    
    # TERTIARY: Check with driver if available
    if driver:
        try:
            # Look for photo/image first
            photo_elements = driver.find_elements(By.XPATH, "//img[@src] | //img[@data-src]")
            video_elements = driver.find_elements(By.TAG_NAME, "video")
            
            # If we have a video player
            if video_elements:
                # Check if it's a reel (look for reel-specific indicators)
                try:
                    reel_container = driver.find_elements(
                        By.XPATH, 
                        "//*[contains(@class, 'reels_tv') or contains(@class, 'reel_player') or contains(@aria-label, 'reel')]"
                    )
                    if reel_container:
                        print(f"    [TYPE] Detected 'Reel' from driver (reel_player class)")
                        return "Reel"
                except:
                    pass
                
                print(f"    [TYPE] Detected 'Video' from driver (video element)")
                return "Video"
            
            # If we have images but no video, it's a photo/carousel
            if photo_elements:
                print(f"    [TYPE] Detected 'Photo' from driver (image elements)")
                return "Photo"
        except:
            pass
    
    # DEFAULT: Return "Post" if no specific type found
    print(f"    [TYPE] Defaulting to 'Post'")
    return "Post"


# ─────────────────────────────────────────────
# PARSE FACEBOOK POST PAGE
# ─────────────────────────────────────────────
def parse_post_page(driver, post_url: str, is_reel: bool = False) -> dict:
    """
    Extracts engagement metrics and metadata from an open Facebook post page.
    Uses a combination of aria-label scraping and page-source JSON extraction.
    """
    result = {
        "likes": 0, "comments": 0, "shares": 0,
        "views": 0, "reactions": 0,
        "post_time": None,
        "caption_length": 0,
        "hashtag_count": 0,
    }

    page_source = driver.page_source
    
    # Save first reel page source for debugging
    global first_reel_saved
    if is_reel and not first_reel_saved:
        try:
            import os
            debug_dir = "facebook_debug_pages"
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir)
            debug_file = f"{debug_dir}/FIRST_REEL_STRUCTURE.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(page_source)
            print(f"    [DEBUG] ✓ First reel structure saved to: {debug_file}")
            first_reel_saved = True
        except Exception as e:
            print(f"    [DEBUG] Failed to save first reel: {e}")
    
    # Debug: uncomment to see page source snippets
    # print(f"\n[DEBUG] Page source length: {len(page_source)}")
    # print(f"[DEBUG] Looking for engagement metrics...")

    # ── Timestamp ──────────────────────────────
    # Facebook encodes post time in a <abbr> or <time> element or as a data attribute
    # It also appears in the JSON embedded in the page

    # 1) Try <abbr title="..."> or data-utime
    for pattern in [
        r'data-utime="(\d{10})"',
        r'"publish_time"\s*:\s*(\d{10})',
        r'"creation_time"\s*:\s*(\d{10})',
        r'"created_time"\s*:\s*"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^"]*)"',
    ]:
        m = re.search(pattern, page_source)
        if m:
            val = m.group(1)
            try:
                if val.isdigit():
                    result["post_time"] = datetime.fromtimestamp(int(val), tz=timezone.utc)
                else:
                    result["post_time"] = datetime.fromisoformat(val.replace("Z", "+00:00"))
                break
            except:
                pass

    # 2) Try the <abbr> tag visible in DOM
    if result["post_time"] is None:
        try:
            abbrs = driver.find_elements(By.TAG_NAME, "abbr")
            for abbr in abbrs:
                title = abbr.get_attribute("data-utime") or abbr.get_attribute("title") or ""
                m = re.search(r"\d{10}", title)
                if m:
                    result["post_time"] = datetime.fromtimestamp(int(m.group()), tz=timezone.utc)
                    break
        except:
            pass

    # 3) Try <time datetime="...">
    if result["post_time"] is None:
        try:
            times = driver.find_elements(By.TAG_NAME, "time")
            for t in times:
                dt_str = t.get_attribute("datetime") or ""
                if dt_str:
                    try:
                        result["post_time"] = datetime.fromisoformat(
                            dt_str.replace("Z", "+00:00")
                        )
                        break
                    except:
                        pass
        except:
            pass

    # ── Reactions / Likes ──────────────────────
    # Facebook groups all reactions (Like, Love, Haha, Wow, Sad, Angry) under one count
    print(f"    [DEBUG] Searching for likes/reactions...")
    
    for pattern in [
        r'"reaction_count"\s*:\s*\{"count"\s*:\s*(\d+)',
        r'"reactionCount"\s*:\s*(\d+)',
        r'"reaction_count"\s*:\s*(\d+)',
        r'"likeCount"\s*:\s*(\d+)',
        r'"like_count"\s*:\s*(\d+)',
        r'"engagement"[^}]*"reaction_count"\s*:\s*(\d+)',
        # Reel-specific patterns - more flexible
        r'"reels_tv_video"[^}]*"reactionCount"\s*:\s*(\d+)',
        r'"engagement"[^}]*"count"\s*:\s*(\d+)',
        # Try to match any reactionCount in the page
        r'"reactionCount"\s*:\s*(\d+)',
        # Video engagement object
        r'"video"[^}]*"reaction_count"\s*:\s*(\d+)',
        r'(\d+)\s*(?:reaction|people reacted|people like)',
        r'"aggregated_reactions"\s*:\s*\{"totalCount"\s*:\s*(\d+)',
        # Fallback: look for any large number near "reaction" keyword
        r'"reaction[^:]*":\s*(\d{1,7})',
    ]:
        m = re.search(pattern, page_source, re.IGNORECASE)
        if m:
            result["reactions"] = parse_number(m.group(1))
            result["likes"] = result["reactions"]
            print(f"    [DEBUG] ✓ Likes found via JSON: {result['reactions']}")
            break

    # Fallback 1: Direct DOM inspection
    if result["reactions"] == 0:
        try:
            print(f"    [DEBUG] Trying DOM inspection for likes...")
            all_buttons = driver.find_elements(By.XPATH, "//button | //div[@role='button']")
            for el in all_buttons[:20]:
                try:
                    text = el.text.strip()
                    aria = el.get_attribute("aria-label") or ""
                    for check_text in [text, aria]:
                        m = re.search(r"([\d,]+(?:\.\d+)?[KMkm]?)\s*(?:reaction|like|people)", check_text, re.IGNORECASE)
                        if m:
                            result["reactions"] = parse_number(m.group(1))
                            result["likes"] = result["reactions"]
                            print(f"    [DEBUG] ✓ Likes found via button text: {result['reactions']}")
                            break
                    if result["reactions"] > 0:
                        break
                except:
                    pass
        except Exception as e:
            print(f"    [DEBUG] DOM inspection failed: {e}")

    # Fallback 2: Search page source
    if result["reactions"] == 0:
        try:
            print(f"    [DEBUG] Trying page source search for likes...")
            m = re.search(r'([\d,]+[KMkm]?)\s*(?:reaction|people|like)', page_source, re.IGNORECASE)
            if m:
                result["reactions"] = parse_number(m.group(1))
                result["likes"] = result["reactions"]
                print(f"    [DEBUG] ✓ Likes found via page source: {result['reactions']}")
        except Exception as e:
            print(f"    [DEBUG] Page source search failed: {e}")

    if result["reactions"] == 0:
        print(f"    [DEBUG] ⚠ No likes found")
        
        # Last resort for reels: Extract numbers from engagement-related JSON
        if is_reel:
            try:
                print(f"    [DEBUG] Trying reel fallback - extracting from engagement areas...")
                # Look for engagement objects with counts - be very specific
                patterns = [
                    r'"engagement"\s*:\s*\{[^}]*"count"\s*:\s*(\d{1,7})',  # engagement object with count
                    r'"reaction_count"\s*:\s*(\d{1,7})',  # reaction count standalone
                    r'reactionCount["\']?\s*:\s*(\d{1,7})',  # alternate format
                    r'"count"\s*:\s*(\d{1,7})(?!\d)',  # count field (1-7 digits max, not longer)
                ]
                for pat in patterns:
                    m = re.search(pat, page_source, re.IGNORECASE)
                    if m:
                        val = int(m.group(1))
                        if 5 <= val <= 1000000000:  # Reasonable range for engagement (5 to 1 billion)
                            result["reactions"] = val
                            result["likes"] = val
                            print(f"    [DEBUG] ✓ Likes found via reel fallback: {result['reactions']}")
                            break
            except Exception as e:
                print(f"    [DEBUG] Reel fallback failed: {e}")

    # ── Comments ──────────────────────────────
    print(f"    [DEBUG] Searching for comments...")
    
    # PRIMARY: Look for comment count - CORRECT PATTERN: "comments":{"total_count":VALUE}
    for pattern in [
        r'"comments"\s*:\s*\{"total_count"\s*:\s*(\d+)',  # MAIN PATTERN - works!
        r'"comment_count"\s*:\s*\{"total_count"\s*:\s*(\d+)',
        r'"commentCount"\s*:\s*(\d+)',
        r'"comment_count"\s*:\s*(\d+)',
        r'"comments_count"\s*:\s*(\d+)',
        # Reel-specific patterns
        r'"reels_tv_video"[^}]*"commentCount"\s*:\s*(\d+)',
        r'"engagement"[^}]*"comment_count"\s*:\s*(\d+)',
        r'"comment"\s*:\s*\{"total_count"\s*:\s*(\d+)',
    ]:
        m = re.search(pattern, page_source, re.IGNORECASE)
        if m:
            val = parse_number(m.group(1))
            # Only accept if it's NOT 15 (which appears to be a template constant)
            if val != 15:
                result["comments"] = val
                print(f"    [DEBUG] ✓ Comments found via JSON: {result['comments']}")
                break

    # Fallback 1: Look for comment count in the engagement metrics bar
    # Facebook shows: "X reactions · Y comments · Z shares" 
    if result["comments"] == 0 or result["comments"] == 15:
        try:
            print(f"    [DEBUG] Looking in engagement bar...")
            
            # Get the engagement section (usually near the bottom of post)
            engagement_section = re.search(
                r'(\d+\s*(?:reaction|comment|share).*?){2,}',
                page_source,
                re.IGNORECASE
            )
            
            if engagement_section:
                section_text = engagement_section.group(0)
                # Now extract comment count from this section
                m = re.search(r'(\d+)\s*comment', section_text, re.IGNORECASE)
                if m:
                    val = parse_number(m.group(1))
                    if val != 15:  # Skip the constant
                        result["comments"] = val
                        print(f"    [DEBUG] ✓ Comments found in engagement bar: {result['comments']}")
        except Exception as e:
            print(f"    [DEBUG] Engagement bar search failed: {e}")

    # Fallback 2: Direct DOM inspection - find comment button with visible text
    if result["comments"] == 0 or result["comments"] == 15:
        try:
            print(f"    [DEBUG] Trying DOM inspection for comments...")
            # Look specifically for engagement button bar (reactions · comments · shares)
            # Try multiple XPath strategies
            xpaths_to_try = [
                "//*[@aria-label and 'comment' in translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')]",
                "//div[@role='button' and @aria-label]",
                "//button[@aria-label]",
                "//span[contains(text(), 'comment') or contains(text(), 'Comment')]",
            ]
            
            for xpath in xpaths_to_try:
                try:
                    els = driver.find_elements(By.XPATH, xpath)
                    for el in els:
                        try:
                            text = el.text.strip()
                            aria = el.get_attribute("aria-label") or ""
                            
                            for check_text in [text, aria]:
                                if check_text and 'comment' in check_text.lower():
                                    # Extract only number followed by "comment"
                                    m = re.search(r'([\d,]+[KMkm]?)\s*comment', check_text, re.IGNORECASE)
                                    if m:
                                        val = parse_number(m.group(1))
                                        if val > 0 and val != 15:
                                            result["comments"] = val
                                            print(f"    [DEBUG] ✓ Comments found via DOM: {result['comments']}")
                                            break
                            if result["comments"] > 0 and result["comments"] != 15:
                                break
                        except:
                            pass
                    if result["comments"] > 0 and result["comments"] != 15:
                        break
                except:
                    pass
        except Exception as e:
            print(f"    [DEBUG] DOM inspection failed: {e}")

    # Fallback 3: Search for specific JSON structure with higher threshold
    if result["comments"] == 0 or result["comments"] == 15:
        try:
            print(f"    [DEBUG] Looking for comment count in nested JSON...")
            # Look for specific nested JSON patterns that indicate comment count
            patterns = [
                r'"comment[s]?"\s*:\s*\{"count[s]?"\s*:\s*(\d+)',
                r'"comments"\s*:\s*\[.*?"count"\s*:\s*(\d+)',
            ]
            for pat in patterns:
                m = re.search(pat, page_source, re.IGNORECASE)
                if m:
                    val = parse_number(m.group(1))
                    if val > 0 and val != 15:
                        result["comments"] = val
                        print(f"    [DEBUG] ✓ Comments found in nested JSON: {result['comments']}")
                        break
        except Exception as e:
            print(f"    [DEBUG] Nested JSON search failed: {e}")

    if result["comments"] == 0 or result["comments"] == 15:
        print(f"    [DEBUG] ⚠ No accurate comments found - still getting 0 or 15")
        
        # Last resort for reels: Extract comment numbers from JSON
        if is_reel:
            try:
                print(f"    [DEBUG] Trying reel fallback - extracting comments from engagement areas...")
                patterns = [
                    r'"comments"\s*:\s*\{[^}]*"total_count"\s*:\s*(\d{1,7})',
                    r'"comment_count"\s*:\s*(\d{1,7})',
                    r'commentCount["\']?\s*:\s*(\d{1,7})',
                    r'"comments"\s*:\s*(\d{1,7})(?!\d)',
                ]
                for pat in patterns:
                    m = re.search(pat, page_source, re.IGNORECASE)
                    if m:
                        val = int(m.group(1))
                        if val > 0 and val != 15 and val <= 10000000:  # Reasonable comment count
                            result["comments"] = val
                            print(f"    [DEBUG] ✓ Comments found via reel fallback: {result['comments']}")
                            break
            except Exception as e:
                print(f"    [DEBUG] Reel comment fallback failed: {e}")

    # ── Shares ─────────────────────────────────
    for pattern in [
        r'"share_count"\s*:\s*\{"count"\s*:\s*(\d+)',
        r'"shareCount"\s*:\s*(\d+)',
        r'"share_count"\s*:\s*(\d+)',
        r'"shares_count"\s*:\s*(\d+)',
        # Reel-specific patterns
        r'"reels_tv_video"[^}]*"shareCount"\s*:\s*(\d+)',
        r'"engagement"[^}]*"share_count"\s*:\s*(\d+)',
        r'(\d+)\s*(?:share|shares)',
    ]:
        m = re.search(pattern, page_source, re.IGNORECASE)
        if m:
            result["shares"] = parse_number(m.group(1))
            break

    # Fallback 1: Look for share button with count
    if result["shares"] == 0:
        try:
            share_xpaths = [
                "//*[@aria-label and contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'share')]",
                "//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'share')]",
                "//div[@role='button' and @aria-label and contains(@aria-label, 'share')]",
            ]
            for xpath in share_xpaths:
                els = driver.find_elements(By.XPATH, xpath)
                for el in els:
                    text = el.get_attribute("aria-label") or el.text or ""
                    m = re.search(r"([\d,]+(?:\.\d+)?[KMkm]?)\s*share", text, re.IGNORECASE)
                    if m:
                        result["shares"] = parse_number(m.group(1))
                        break
                if result["shares"] > 0:
                    break
        except:
            pass

    # Fallback 2: Look for shares in page source
    if result["shares"] == 0:
        try:
            m = re.search(r'([\d,]+[KMkm]?)\s*share', page_source, re.IGNORECASE)
            if m:
                result["shares"] = parse_number(m.group(1))
        except:
            pass
    
    # Last resort for reel shares
    if result["shares"] == 0 and is_reel:
        try:
            print(f"    [DEBUG] Trying reel fallback for shares...")
            patterns = [
                r'"share_count"\s*:\s*\{[^}]*"count"\s*:\s*(\d{1,7})',
                r'"share_count"\s*:\s*(\d{1,7})',
                r'shareCount["\']?\s*:\s*(\d{1,7})',
                r'"shares"\s*:\s*(\d{1,7})(?!\d)',
            ]
            for pat in patterns:
                m = re.search(pat, page_source, re.IGNORECASE)
                if m:
                    val = int(m.group(1))
                    if val > 0 and val <= 100000000:  # Reasonable share count
                        result["shares"] = val
                        print(f"    [DEBUG] ✓ Shares found via reel fallback: {result['shares']}")
                        break
        except Exception as e:
            print(f"    [DEBUG] Reel shares fallback failed: {e}")

    # ── Views (Video / Reel only) ───────────────
    for pattern in [
        r'"video_view_count"\s*:\s*(\d+)',
        r'"viewCount"\s*:\s*(\d+)',
        r'"view_count"\s*:\s*(\d+)',
        # Reel-specific patterns
        r'"reels_tv_video"[^}]*"viewCount"\s*:\s*(\d+)',
        r'"engagement"[^}]*"view_count"\s*:\s*(\d+)',
        r'(\d[\d,]*[KMkm]?)\s*[Vv]iew',
    ]:
        m = re.search(pattern, page_source, re.IGNORECASE)
        if m:
            result["views"] = parse_number(m.group(1))
            break
    
    # Fallback for reel views
    if result["views"] == 0 and is_reel:
        try:
            print(f"    [DEBUG] Trying reel fallback for views...")
            patterns = [
                r'"video_view_count"\s*:\s*(\d{1,7})',
                r'"view_count"\s*:\s*(\d{1,7})',
                r'viewCount["\']?\s*:\s*(\d{1,7})',
                r'"views"\s*:\s*(\d{1,7})(?!\d)',
            ]
            for pat in patterns:
                m = re.search(pat, page_source, re.IGNORECASE)
                if m:
                    val = int(m.group(1))
                    if val > 0 and val <= 10000000000:  # Views can be large (up to 10 billion)
                        result["views"] = val
                        print(f"    [DEBUG] ✓ Views found via reel fallback: {result['views']}")
                        break
        except Exception as e:
            print(f"    [DEBUG] Reel views fallback failed: {e}")

    # ── Caption / Hashtags ─────────────────────
    # Try meta description first (most reliable)
    meta_m = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', page_source)
    if not meta_m:
        meta_m = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', page_source)

    caption = ""
    if meta_m:
        caption = meta_m.group(1)
    else:
        # Try JSON "message" or "story" field
        for field in [r'"message"\s*:\s*"([^"]{10,})"', r'"story"\s*:\s*"([^"]{10,})"']:
            fm = re.search(field, page_source)
            if fm:
                caption = fm.group(1)
                break

    result["caption_length"] = len(caption)
    result["hashtag_count"]  = len(re.findall(r"#\w+", caption))

    return result


# ─────────────────────────────────────────────
# MAIN SCRAPER
# ─────────────────────────────────────────────
def scrape_facebook():
    global first_post_saved
    first_post_saved = False
    
    print("Opening Chrome...")
    driver    = setup_driver()
    all_posts = []

    wait_for_manual_login(driver)

    for page_name in BUSINESS_PAGES:
        print(f"\n{'='*50}")
        print(f"Scraping Facebook: {page_name}")
        print(f"{'='*50}")

        try:
            driver.get(f"https://www.facebook.com/{page_name}")
            time.sleep(5)

            followers = get_followers(driver)
            print(f"  Followers/Likes: {followers:,}")

            post_links = collect_post_links(driver, page_name, MAX_POSTS)

            if not post_links:
                print(f"  ❌ No posts found for {page_name} - skipping")
                continue

            posts_saved = 0
            def _session_alive(driver) -> bool:
                try:
                    _ = driver.current_url
                    return True
                except:
                    return False

            for i, link in enumerate(post_links):
                try:
                    if not _session_alive(driver):
                        print(f"  ⚠ Chrome session died at post [{i+1}] - saving {posts_saved} posts collected so far...")
                        break

                    # ── Skip non-post URLs ──
                    SKIP_PATTERNS = ["/stories/", "facebook.com/story", "/story.php"]
                    if any(p in link.lower() for p in SKIP_PATTERNS) and "permalink.php" not in link.lower():
                        print(f"  [{i+1}] Skipping non-post URL: {link[:60]}")
                        continue

                    is_reel_url = ("/reel/" in link.lower() or "/reels/" in link.lower())

                    # ── For reels: flush logs BEFORE navigating so we
                    #    capture ALL GraphQL calls that fire during page load
                    if is_reel_url:
                        try:
                            driver.get_log("performance")  # flush stale logs
                            print(f"  [{i+1}] Reel detected - flushed logs before navigation")
                        except:
                            pass

                    # Navigate to post
                    page_loaded = navigate_and_wait(driver, link, is_reel=is_reel_url)

                    if not page_loaded:
                        print(f"  [{i+1}] ⚠ Load check incomplete, attempting to parse anyway...")
                    else:
                        print(f"  [{i+1}] ✓ Page loaded successfully")

                    # ── For reels: wait for GraphQL calls to complete THEN
                    #    immediately grab logs before anything else runs
                    if is_reel_url:
                        print(f"  [{i+1}] Scraping reel metrics from DOM...")
                        network_data = scrape_reel_from_dom(driver)
                        print(f"    [RESULT] reactions={network_data['reactions']} "
                              f"comments={network_data['comments']} "
                              f"shares={network_data['shares']} "
                              f"views={network_data['views']}")
                    else:
                        time.sleep(1)
                        network_data = None

                    # Get content type
                    page_source  = driver.page_source
                    content_type = get_content_type(link, driver=driver, page_source=page_source)
                    is_reel      = (content_type == "Reel")

                    # ── Parse metrics ──────────────────────────
                    # Always call parse_post_page for timestamp / caption
                    data = parse_post_page(driver, link, is_reel=is_reel)

                    # For reels: override engagement with network data if we got it
                    if is_reel and network_data is not None:
                        if any(v > 0 for v in network_data.values()):
                            print(f"    [DEBUG] ✓ Overriding with network data for reel")
                            data["reactions"] = network_data["reactions"]
                            data["likes"]     = network_data["likes"]
                            data["comments"]  = network_data["comments"]
                            data["shares"]    = network_data["shares"]
                            data["views"]     = network_data["views"]
                        else:
                            print(f"    [DEBUG] ⚠ Network data empty - keeping page-parse values")

                    post_time = data["post_time"]

                    # Save first post's page source for debugging
                    if not first_post_saved:
                        try:
                            import os
                            debug_dir  = "facebook_debug_pages"
                            os.makedirs(debug_dir, exist_ok=True)
                            debug_file = f"{debug_dir}/FIRST_POST_STRUCTURE.html"
                            with open(debug_file, 'w', encoding='utf-8') as f:
                                f.write(driver.page_source)
                            print(f"    [DEBUG] ✓ First post structure saved to: {debug_file}")
                            first_post_saved = True
                        except Exception as e:
                            print(f"    [DEBUG] Failed to save first post: {e}")

                    # Date filtering - only applies after the first 20 posts
                    if post_time is None:
                        print(f"  [{i+1}] ⚠ No timestamp - skipping")
                        continue
                    if post_time < CUTOFF_DATE:
                        print(f"  [{i+1}] {post_time.strftime('%Y-%m-%d')} before "
                              f"cutoff ({CUTOFF_DATE.strftime('%Y-%m-%d')}) - skipping")
                        continue

                    # ── Build row ──────────────────────────────
                    likes      = data["likes"]
                    comments   = data["comments"]
                    shares     = data["shares"]
                    views      = data["views"]
                    reactions  = data["reactions"]
                    engagement = reactions + comments + shares
                    eng_rate   = round((engagement / followers * 100), 4) if followers > 0 else 0

                    post_date_str = post_time.strftime("%Y-%m-%d") if post_time else "Unknown"
                    post_time_str = post_time.strftime("%H:%M")    if post_time else "Unknown"
                    hour          = post_time.hour                 if post_time else None
                    minute        = post_time.minute               if post_time else None
                    day_of_week   = post_time.strftime("%A")       if post_time else None
                    day_number    = post_time.weekday()            if post_time else None
                    month         = post_time.strftime("%B")       if post_time else None

                    all_posts.append({
                        "Platform":          "Facebook",
                        "Business":          page_name,
                        "Followers":         followers,
                        "Post_Date":         post_date_str,
                        "Post_Time":         post_time_str,
                        "Hour":              hour,
                        "Minute":            minute,
                        "Day_of_Week":       day_of_week,
                        "Day_Number":        day_number,
                        "Month":             month,
                        "Views":             views,
                        "Reactions":         reactions,
                        "Likes":             likes,
                        "Comments":          comments,
                        "Shares":            shares,
                        "Total_Engagement":  engagement,
                        "Engagement_Rate_%": eng_rate,
                        "Content_Type":      content_type,
                        "Caption_Length":    data["caption_length"],
                        "Hashtag_Count":     data["hashtag_count"],
                        "Post_URL":          link,
                    })

                    posts_saved += 1
                    print(f"  [{i+1}/{len(post_links)}] "
                          f"{post_date_str} {post_time_str} | "
                          f"Reactions: {reactions:,} | Comments: {comments:,} | "
                          f"Shares: {shares:,} | Views: {views:,} | Type: {content_type}")
                    print(f"       URL: {link[:60]}...")

                    time.sleep(2.5)

                except Exception as e:
                    err_str = str(e)
                    # Detect session-killing errors and break immediately
                    if "invalid session id" in err_str or "no such window" in err_str:
                        print(f"  ⚠ Session died at post [{i+1}] - saving {posts_saved} posts and stopping...")
                        break
                    print(f"  [{i+1}] ERROR: {e}")
                    continue
            print(f"  ✅ Done: {posts_saved} posts saved for {page_name}")

        except Exception as e:
            print(f"  ERROR on {page_name}: {e}")

        time.sleep(5)

    driver.quit()

    # ── Save output ────────────────────────────
    if all_posts:
        df = pd.DataFrame(all_posts)

        try:
            df.to_excel(OUTPUT_FILE, index=False)
            excel_file = OUTPUT_FILE
        except PermissionError:
            from datetime import datetime as dt
            timestamp  = dt.now().strftime("%Y%m%d_%H%M%S")
            excel_file = f"facebook_data_{timestamp}.xlsx"
            df.to_excel(excel_file, index=False)
            print(f"⚠️  Main file locked - saved to: {excel_file}")

        try:
            df.to_csv("facebook_data.csv", index=False)
        except Exception:
            pass

        print(f"\n{'='*50}")
        print(f"✅ SUCCESS! Saved {len(df)} posts → {excel_file}")
        print(f"{'='*50}")
        print(df[[
            "Business", "Post_Date", "Post_Time",
            "Reactions", "Comments", "Shares", "Views", "Content_Type"
        ]].head(15).to_string(index=False))

    else:
        print("\n❌ No data collected.")


if __name__ == "__main__":
    scrape_facebook()