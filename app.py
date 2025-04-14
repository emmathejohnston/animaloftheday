from flask import Flask, jsonify, render_template
import pandas as pd
import random
import requests
import re 
import os

app = Flask(__name__)

# Load the preprocessed dataset once (fast!)
df = pd.read_csv("animal_names.tsv", sep="\t")

def clean_scientific_name(scientific_name):
    """Remove author/year info from scientific name while keeping genus + species."""
    
    # Remove everything after the first two words (genus + species)
    cleaned_name = " ".join(scientific_name.split()[:2])

    print(f"🛠 Original: {scientific_name} → Cleaned: {cleaned_name}")  # Debug output

    return cleaned_name



def get_inaturalist_image(scientific_name):
    """Fetch an image from iNaturalist based on the scientific name."""
    url = f"https://api.inaturalist.org/v1/taxa?q={scientific_name}"
    response = requests.get(url)
    
    try:
        data = response.json()
        print(f"📄 iNaturalist API Response: {data}")  # Debugging output
        
        # Check if 'results' exists and is not empty
        if "results" in data and len(data["results"]) > 0:
            return data["results"][0].get("default_photo", {}).get("medium_url", None)
        else:
            print(f"❌ No results found on iNaturalist for {scientific_name}")
            return None
    except Exception as e:
        print(f"⚠️ Error fetching iNaturalist image: {e}")
        return None


def get_wikimedia_image(scientific_name):
    """Fetch an image from Wikimedia Commons using only genus + species (no author info)."""
    clean_name = clean_scientific_name(scientific_name)  # Ensure we remove author names
    clean_name = clean_name.replace(" ", "_")  # Replace spaces with underscores for Wikimedia

    wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/media-list/{clean_name}"

    print(f"🌐 Wikimedia API URL: {wiki_url}")  # Debugging output

    response = requests.get(wiki_url)

    try:
        data = response.json()
        print(f"📄 Wikimedia Response: {data}")  # Debugging output
        return data["items"][0]["original"]["source"]  # First image
    except (KeyError, IndexError):
        print("❌ No image found on Wikimedia Commons.")
        return None  # No image found

def get_image(scientific_name):
    """Try iNaturalist first, then fallback to Wikimedia Commons."""
    clean_name = clean_scientific_name(scientific_name)

    print(f"🔍 Searching for images of: {clean_name}")

    image = get_inaturalist_image(clean_name)
    if not image:
        print(f"🔄 No image found on iNaturalist. Trying Wikimedia Commons for {clean_name}...")
        image = get_wikimedia_image(clean_name)
    
    return image

def get_inaturalist_wikipedia_url(scientific_name):
    """Fetch Wikipedia URL from iNaturalist if available, using the cleaned scientific name."""
    
    clean_name = clean_scientific_name(scientific_name)  # Remove author names
    url = f"https://api.inaturalist.org/v1/taxa?q={clean_name}"
    
    print(f"🔍 DEBUG: Querying iNaturalist with cleaned name: {clean_name}")  # Debugging line

    response = requests.get(url)

    try:
        data = response.json()
        if "results" in data and len(data["results"]) > 0:
            wiki_url = data["results"][0].get("wikipedia_url", None)
            if wiki_url:
                print(f"✅ DEBUG: Found Wikipedia URL on iNaturalist: {wiki_url}")
                return wiki_url  # Use this link directly
            else:
                print(f"⚠️ DEBUG: iNaturalist response contained no Wikipedia URL for {clean_name}")
        else:
            print(f"⚠️ DEBUG: iNaturalist response had no results for {clean_name}")
    except Exception as e:
        print(f"⚠️ Error fetching Wikipedia URL from iNaturalist: {e}")

    return None  # No Wikipedia link found

def get_wikipedia_url(scientific_name):
    """Check if a Wikipedia page exists, prioritizing iNaturalist links and handling redirects."""

    # 🔹 First, check if iNaturalist provides a Wikipedia link
    inaturalist_url = get_inaturalist_wikipedia_url(scientific_name)
    
    if inaturalist_url:
        print(f"✅ DEBUG: Wikipedia URL being used from iNaturalist: {inaturalist_url}")  # NEW Debugging line
        return inaturalist_url  # Use this link directly

    print(f"⚠️ DEBUG: Falling back to Wikipedia API lookup for {scientific_name}")  # NEW Debugging line

    # 🔹 Otherwise, construct a Wikipedia link using scientific name
    base_url = "https://en.wikipedia.org/wiki/"
    clean_name = scientific_name.replace(" ", "_")  # Wikipedia uses underscores

    # 🔹 Check if Wikipedia page exists
    wiki_check_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{clean_name}"
    response = requests.get(wiki_check_url)

    if response.status_code == 200:
        data = response.json()
        if "content_urls" in data and "desktop" in data["content_urls"]:
            redirect_url = data["content_urls"]["desktop"]["page"]
            print(f"✅ DEBUG: Wikipedia page found via API: {redirect_url}")
        
def get_wikipedia_summary(scientific_name):
    """Fetch the Wikipedia summary for the given scientific name, using the cleaned name."""
    
    clean_name = clean_scientific_name(scientific_name)  # Remove author names
    wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{clean_name.replace(' ', '_')}"
    
    print(f"🔍 DEBUG: Fetching Wikipedia summary from {wiki_url}")  # Debugging line

    response = requests.get(wiki_url)

    if response.status_code == 200:
        data = response.json()
        summary_text = data.get("extract", "No summary available.")  # Get the intro text
        wikipedia_url = data.get("content_urls", {}).get("desktop", {}).get("page", None)
        wiki_image = data.get("thumbnail", {}).get("source", None)  # Optional image

        return {
            "summary": summary_text,
            "wikipedia_url": wikipedia_url,
            "wiki_image": wiki_image
        }
    
    print(f"❌ DEBUG: No Wikipedia summary found for {clean_name}")
    return None  # No Wikipedia summary found


### 🚀 **Fix: Add Missing Routes**
@app.route("/")
def index():
    """Serve the HTML webpage."""
    return render_template("index.html")

@app.route("/random_animal")

@app.route("/")
def index():
    return render_template("index.html")


def random_animal():
    """API endpoint: Returns a random animal with image & Wikipedia summary."""
    random_entry = df.sample(n=1).iloc[0]
    scientific_name = random_entry["scientificName"]
    
    # Fetch image from iNaturalist or Wikimedia
    image_url = get_image(scientific_name)
    
    # Fetch Wikipedia summary (ensure it's a dictionary)
    wikipedia_data = get_wikipedia_summary(scientific_name) or {}

    return jsonify({
        "vernacularName": random_entry["vernacularName"],
        "scientificName": scientific_name,
        "image": image_url,
        "wikipedia_summary": wikipedia_data.get("summary", "No Wikipedia summary found."),
        "wikipedia_url": wikipedia_data.get("wikipedia_url"),
        "wiki_image": wikipedia_data.get("wiki_image")
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
if __name__ == "__main__":
    app.run(debug=True)
