from playwright.sync_api import sync_playwright
import spacy
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load NLP model for semantic analysis
nlp = spacy.load("en_core_web_lg")
nlp.max_length = 1500000

# Function to analyze website content for keywords
def analyze_content(url, keywords):
    print(f"Processing {url}...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)  # Increased timeout to 60 seconds

            # Wait for the page to finish loading
            page.wait_for_load_state("networkidle")
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            page.wait_for_timeout(5000)  # Adjusted wait time for dynamic loading

            content_locator = page.locator("div")
            content = content_locator.all_inner_texts()
            page.close()
            browser.close()

            if not content:
                print(f"No significant content found at {url}.")
                return None

            content = " ".join(content)
            print(f"Analyzing content for {url}...")

            # Perform keyword matching and semantic analysis
            keyword_matches = {}
            doc = nlp(content)

            for keyword in keywords:
                exact_count = content.lower().count(keyword.lower())
                semantic_count = sum(1 for token in doc if token.has_vector and token.similarity(nlp(keyword)) > 0.8)
                keyword_matches[keyword] = {"exact": exact_count, "semantic": semantic_count}

            total_relevance = sum(count["exact"] + count["semantic"] for count in keyword_matches.values())
            is_relevant = "Yes" if total_relevance > 0 else "No"
            return keyword_matches, is_relevant
    except Exception as e:
        print(f"Error processing {url}: {e}")
        return None

# List of URLs to analyze
urls = [
    "https://www.mars.com/",
    "https://www.nestle.com/",
    "https://www.tysonfoods.com/"  # Add more URLs as needed
]

# List of keywords
keywords = ["gut health", "cognitive health", "women health", "probiotic", "food and beverage", 
            "manufacturer", "distributer", "brand", "certification", "contact information", "global", "local"]

# Function to process each URL concurrently
def process_url(url):
    result = analyze_content(url, keywords)
    if result:
        keyword_matches, is_relevant = result
        row = {"URL": url, "Relevant": is_relevant}
        for keyword in keywords:
            row[f"{keyword}_exact"] = keyword_matches.get(keyword, {}).get("exact", 0)
            row[f"{keyword}_semantic"] = keyword_matches.get(keyword, {}).get("semantic", 0)
        return row
    return None

# Use ThreadPoolExecutor for concurrent execution
results = []
with ThreadPoolExecutor(max_workers=3) as executor:  # Limit workers to avoid overload
    future_to_url = {executor.submit(process_url, url): url for url in urls}
    for future in as_completed(future_to_url):
        url = future_to_url[future]
        try:
            result = future.result()
            if result:
                results.append(result)
        except Exception as e:
            print(f"Exception occurred while processing {url}: {e}")

# Convert results to DataFrame
if results:
    df = pd.DataFrame(results)
    file_name = "website_keyword_analysis.xlsx"
    df.to_excel(file_name, index=False)
    print(f"Analysis results saved to {file_name}.")
else:
    print("No valid results to save.")