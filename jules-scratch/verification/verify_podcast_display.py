from playwright.sync_api import sync_playwright, expect

def run_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the running Flask application.
        page.goto("http://127.0.0.1:5000/")

        # Print the full HTML content to debug.
        print(page.content())

        # Expect the page to contain the podcast title and show name.
        expect(page.locator("body")).to_contain_text("My Favorite Murder with Karen Kilgariff and Georgia Hardstark")

        # Take a screenshot for visual verification.
        page.screenshot(path="jules-scratch/verification/verification.png")

        browser.close()

if __name__ == "__main__":
    run_verification()