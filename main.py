import asyncio
import random
import time
from playwright.async_api import async_playwright
from colorama import Fore, Back, Style, init
import threading
from datetime import datetime

# Initialize colorama for colored output
init(autoreset=True)

AUTH = 'brd-customer-hl_c19cf957-zone-scraping_browser1-country-in:9y5yhiqi5mdg'
SBR_WS_CDP = f'wss://{AUTH}@brd.superproxy.io:9222'

class ParallelProgressTracker:
    def __init__(self, max_instances=5):
        self.max_instances = max_instances
        self.instances = {}
        self.lock = threading.Lock()
        self.total_steps = 11
        
        # Initialize instances
        for i in range(1, max_instances + 1):
            self.instances[f"Instance_{i}"] = {
                "current_step": 0,
                "status": "Waiting",
                "url": "N/A",
                "last_update": "N/A",
                "iteration": 0,
                "errors": 0
            }
    
    def update_instance(self, instance_id, step=None, status=None, url=None):
        with self.lock:
            if instance_id in self.instances:
                if step is not None:
                    self.instances[instance_id]["current_step"] = step
                if status is not None:
                    self.instances[instance_id]["status"] = status
                if url is not None:
                    self.instances[instance_id]["url"] = url[:50] + "..." if len(url) > 50 else url
                self.instances[instance_id]["last_update"] = datetime.now().strftime("%H:%M:%S")
                
                # Print updated table
                self.print_table()
    
    def increment_iteration(self, instance_id):
        with self.lock:
            if instance_id in self.instances:
                self.instances[instance_id]["iteration"] += 1
                self.instances[instance_id]["current_step"] = 0
                self.instances[instance_id]["status"] = "Starting New Iteration"
    
    def increment_errors(self, instance_id):
        with self.lock:
            if instance_id in self.instances:
                self.instances[instance_id]["errors"] += 1
    
    def print_table(self):
        # Clear screen and move cursor to top
        print("\033[H\033[J", end="")
        
        print(f"\n{Fore.CYAN}╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL}                                            {Fore.YELLOW}🤖 PARALLEL BROWSER AUTOMATION STATUS 🤖{Style.RESET_ALL}                                            {Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}╠═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣{Style.RESET_ALL}")
        
        # Header
        header = f"{Fore.CYAN}║{Style.RESET_ALL} {'Instance':<12} {'Progress':<15} {'Step':<4} {'Status':<25} {'URL':<35} {'Iteration':<9} {'Errors':<6} {'Updated':<8} {Fore.CYAN}║{Style.RESET_ALL}"
        print(header)
        print(f"{Fore.CYAN}╠═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣{Style.RESET_ALL}")
        
        # Data rows
        for instance_id, data in self.instances.items():
            progress_bar = "█" * data["current_step"] + "░" * (self.total_steps - data["current_step"])
            
            # Color coding for status
            if "completed" in data["status"].lower():
                status_color = Fore.GREEN
            elif "error" in data["status"].lower() or "failed" in data["status"].lower():
                status_color = Fore.RED
            elif "waiting" in data["status"].lower():
                status_color = Fore.YELLOW
            else:
                status_color = Fore.CYAN
            
            row = f"{Fore.CYAN}║{Style.RESET_ALL} {instance_id:<12} {progress_bar:<15} {data['current_step']:<4} {status_color}{data['status']:<25}{Style.RESET_ALL} {data['url']:<35} {data['iteration']:<9} {data['errors']:<6} {data['last_update']:<8} {Fore.CYAN}║{Style.RESET_ALL}"
            print(row)
        
        print(f"{Fore.CYAN}╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")

# Global tracker instance
tracker = ParallelProgressTracker()

async def human_like_scroll_to_element(page, selector, description):
    """Scroll to element in a human-like manner"""
    tracker.info(f"Scrolling to {description}...")
    
    # Get element position
    element = await page.query_selector(selector)
    if not element:
        tracker.error(f"Element not found for scrolling: {selector}")
        return
        
    bbox = await element.bounding_box()
    
    if bbox:
        # Calculate scroll position to center the element
        viewport_size = page.viewport_size
        target_y = bbox['y'] - (viewport_size['height'] // 2) + (bbox['height'] // 2)
        
        # Human-like smooth scrolling
        current_scroll = await page.evaluate("window.pageYOffset")
        scroll_distance = target_y - current_scroll
        steps = abs(scroll_distance) // 50 + 1
        
        for i in range(int(steps)):
            scroll_y = current_scroll + (scroll_distance * (i + 1) / steps)
            await page.evaluate(f"window.scrollTo(0, {scroll_y})")
            await asyncio.sleep(random.uniform(0.02, 0.05))
        
        await asyncio.sleep(random.uniform(0.5, 1.0))

async def human_like_click(page, selector, description):
    """Perform human-like click with movement and timing"""
    tracker.info(f"Clicking on {description}...")
    
    element = await page.query_selector(selector)
    if not element:
        tracker.error(f"Element not found for clicking: {selector}")
        return
        
    bbox = await element.bounding_box()
    
    if bbox:
        # Move to a random point within the element
        x = bbox['x'] + random.uniform(bbox['width'] * 0.2, bbox['width'] * 0.8)
        y = bbox['y'] + random.uniform(bbox['height'] * 0.2, bbox['height'] * 0.8)
        
        # Human-like mouse movement
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Click with human-like timing
        await page.mouse.click(x, y)
        await asyncio.sleep(random.uniform(0.2, 0.5))

async def wait_for_element_with_retry(page, selector, timeout=70000, step5_special=False, instance_id=None):
    """Wait for element with retry logic"""
    if step5_special:
        timeout = 2000
    
    end_time = time.time() + (timeout / 1000)
    
    while time.time() < end_time:
        try:
            element = await page.wait_for_selector(selector, timeout=500)
            if element:
                return element
        except:
            pass
        
        try:
            escaped_selector = selector.replace('"', '\\"').replace("'", "\\'")
            element_exists = await page.evaluate(f'document.querySelector("{escaped_selector}") !== null')
            if element_exists:
                element = await page.query_selector(selector)
                if element:
                    return element
        except:
            pass
        
        await asyncio.sleep(0.1)
    
    return None

async def close_popup_ads(page):
    """Close any popup ads that might appear"""
    popup_selectors = [
        'button[onclick*="close"]',
        'a[onclick*="close"]',
        '.close',
        '#close',
        '[aria-label="Close"]',
        '.popup-close',
        '.ad-close'
    ]
    
    for selector in popup_selectors:
        try:
            element = await page.wait_for_selector(selector, timeout=1000)
            if element:
                await element.click()
                tracker.info("Closed popup ad")
                await asyncio.sleep(0.5)
        except:
            continue

def read_random_url():
    """Read random URL from file"""
    try:
        with open('/workspaces/codespaces-blank/url4.txt', 'r') as file:
            urls = [line.strip() for line in file.readlines() if line.strip()]
            if urls:
                return random.choice(urls)
            else:
                raise Exception("No URLs found in file")
    except FileNotFoundError:
        raise Exception("URL file not found")

async def run_single_instance(instance_id, playwright):
    """Run automation for a single instance"""
    while True:
        try:
            tracker.increment_iteration(instance_id)
            tracker.update_instance(instance_id, status="Reading URL")
            
            # Read random URL
            url = read_random_url()
            tracker.update_instance(instance_id, status="Connecting to browser", url=url)
            
            # Connect to browser
            browser = await playwright.chromium.connect_over_cdp(SBR_WS_CDP)
            page = await browser.new_page()
            await page.set_viewport_size({"width": 1366, "height": 768})
            
            tracker.update_instance(instance_id, step=1, status="Loading page")
            
            # Navigate to URL
            await page.goto(url, timeout=30000, wait_until='domcontentloaded')
            await asyncio.sleep(5)
            
            # Check page state
            try:
                page_title = await page.title()
                if 'redirect' in page_title.lower() or 'redirecting' in page_title.lower():
                    await asyncio.sleep(8)
            except:
                pass
            
            # Step 1: Click "I Am Not Robot" button
            tracker.update_instance(instance_id, step=1, status="Step 1: Robot button")
            robot_selectors = ['#robot', 'button#robot', 'center #robot', '#robot.rtg_btn', 'button[onclick*="startTimer"]', '.rtg_btn', 'center button']
            
            element_found = False
            for robot_selector in robot_selectors:
                element = await wait_for_element_with_retry(page, robot_selector, timeout=5000, instance_id=instance_id)
                if element:
                    click_success = await javascript_click_with_validation(page, robot_selector, "I Am Not Robot button", instance_id)
                    if click_success:
                        element_found = True
                        break
            
            if not element_found:
                tracker.update_instance(instance_id, status="Error: Robot button not found")
                await browser.close()
                await asyncio.sleep(10)
                continue

            # Wait 25 seconds
            tracker.update_instance(instance_id, status="Waiting 25s after step 1")
            await asyncio.sleep(25)

            # Step 2: Click "Dual Tap Go Link"
            tracker.update_instance(instance_id, step=2, status="Step 2: Dual Tap Go Link")
            dual_tap_selector = 'button#rtgli1[onclick="scrol()"]'
            element = await wait_for_element_with_retry(page, dual_tap_selector, instance_id=instance_id)
            if element:
                await javascript_click_with_validation(page, dual_tap_selector, "Dual Tap Go Link button", instance_id)

            await asyncio.sleep(2)

            # Step 3: Click "Dual Tap Continue"
            tracker.update_instance(instance_id, step=3, status="Step 3: Dual Tap Continue")
            continue_selector = 'button#robot2'
            element = await wait_for_element_with_retry(page, continue_selector, instance_id=instance_id)
            if element:
                await javascript_click_with_validation(page, continue_selector, "Dual Tap Continue button", instance_id)

            await asyncio.sleep(10)

            # Step 4: Click "GO TO LINK"
            tracker.update_instance(instance_id, step=4, status="Step 4: GO TO LINK")
            go_link_selector = 'button#rtg-snp2.rtg_btn[type="submit"]'
            element = await wait_for_element_with_retry(page, go_link_selector, instance_id=instance_id)
            if element:
                await javascript_click_with_validation(page, go_link_selector, "GO TO LINK button", instance_id)
                await asyncio.sleep(3)

            # Step 5: Handle popup
            tracker.update_instance(instance_id, step=5, status="Step 5: Checking popup")
            popup_selector = 'div.popup#popup[style*="display: block"]'
            popup_element = await wait_for_element_with_retry(page, popup_selector, timeout=2000, instance_id=instance_id)
            if popup_element:
                # Handle popup ads
                pass

            # Step 6: Click proceed image
            tracker.update_instance(instance_id, step=6, status="Step 6: Proceed image")
            await asyncio.sleep(2)
            proceed_img_selector = 'img[src="https://i.imgur.com/KvyIEsF.png"][alt="Click to proceed"]'
            element = await wait_for_element_with_retry(page, proceed_img_selector, instance_id=instance_id)
            if element:
                await javascript_click_with_validation(page, proceed_img_selector, "proceed image", instance_id)
                await asyncio.sleep(3)

            # Step 7: Close sticky ads
            tracker.update_instance(instance_id, step=7, status="Step 7: Close ads")
            close_ads_selector = 'a.close-stky-ads[onclick*="fixedbannner"]'
            element = await wait_for_element_with_retry(page, close_ads_selector, instance_id=instance_id)
            if element:
                await page.click(close_ads_selector)

            # Step 8: Click Continue button
            tracker.update_instance(instance_id, step=8, status="Step 8: Continue button")
            continue_btn_selector = 'button#btn7.ce-btn.ce-blue[type="submit"]'
            element = await wait_for_element_with_retry(page, continue_btn_selector, instance_id=instance_id)
            if element:
                await javascript_click_with_validation(page, continue_btn_selector, "Continue button", instance_id)
                await asyncio.sleep(3)

            # Wait 15 seconds before step 9
            tracker.update_instance(instance_id, status="Waiting 15s before step 9")
            await asyncio.sleep(15)

            # Step 9: Click continue image
            tracker.update_instance(instance_id, step=9, status="Step 9: Continue image")
            continue_img_selector = 'img[src="https://i.imgur.com/KvyIEsF.png"][alt="Continue"]'
            element = await wait_for_element_with_retry(page, continue_img_selector, instance_id=instance_id)
            if element:
                await javascript_click_with_validation(page, continue_img_selector, "continue image", instance_id)
                await asyncio.sleep(4)

            # Step 10: Click Get Link
            tracker.update_instance(instance_id, step=10, status="Step 10: Get Link")
            await asyncio.sleep(5)
            
            get_link_selectors = [
                'a.btn.btn-success.btn-lg.get-link', 'a[class*="get-link"]', 'a.get-link',
                'a.btn-success[href*="driveseed"]', 'a.btn-lg[href*="file"]', 'a.btn.btn-success',
                'a[href*="driveseed.org"]', '.get-link', 'button.get-link'
            ]
            
            for get_link_selector in get_link_selectors:
                element = await wait_for_element_with_retry(page, get_link_selector, timeout=5000, instance_id=instance_id)
                if element:
                    await javascript_click_with_validation(page, get_link_selector, "Get Link button", instance_id)
                    break

            # Step 11: Close browser
            tracker.update_instance(instance_id, step=11, status="Completed successfully")
            await browser.close()
            
            # Wait before next iteration
            await asyncio.sleep(5)
            
        except Exception as e:
            tracker.increment_errors(instance_id)
            tracker.update_instance(instance_id, status=f"Error: {str(e)[:20]}...")
            if 'browser' in locals():
                await browser.close()
            await asyncio.sleep(10)

async def javascript_click_with_validation(page, selector, description, instance_id):
    """Perform JavaScript click with validation"""
    try:
        element = await page.query_selector(selector)
        if not element:
            return False
        
        # Scroll to element
        await page.evaluate(f"""
            (selector) => {{
                const element = document.querySelector(selector);
                if (element) {{
                    element.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                }}
            }}
        """, selector)
        
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
        # Perform click
        click_result = await page.evaluate(f"""
            (selector) => {{
                const element = document.querySelector(selector);
                if (!element) return {{ success: false, error: 'Element not found' }};
                
                try {{
                    const events = ['mousedown', 'mouseup', 'click'];
                    events.forEach(eventType => {{
                        const event = new MouseEvent(eventType, {{
                            bubbles: true,
                            cancelable: true,
                            view: window
                        }});
                        element.dispatchEvent(event);
                    }});
                    
                    if (element.onclick) {{
                        element.onclick();
                    }}
                    
                    return {{ success: true, message: 'Click events dispatched successfully' }};
                }} catch (error) {{
                    return {{ success: false, error: error.message }};
                }}
            }}
        """, selector)
        
        if not click_result.get('success'):
            return False
        
        await asyncio.sleep(random.uniform(0.2, 0.5))
        return True
        
    except Exception as e:
        if "Execution context was destroyed" in str(e) or "navigation" in str(e).lower():
            return True
        return False

async def main():
    print(f"{Fore.MAGENTA}{Back.BLACK} 🤖 Starting Parallel Browser Automation (5 Instances) 🤖 {Style.RESET_ALL}\n")
    
    # Initial table display
    tracker.print_table()
    
    async with async_playwright() as playwright:
        # Create 5 parallel tasks
        tasks = []
        for i in range(1, 6):
            instance_id = f"Instance_{i}"
            task = asyncio.create_task(run_single_instance(instance_id, playwright))
            tasks.append(task)
        
        # Run all tasks concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == '__main__':
    asyncio.run(main())
