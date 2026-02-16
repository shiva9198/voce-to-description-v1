from flask import Flask, render_template, request, jsonify, redirect
from flask_cors import CORS
from dotenv import load_dotenv
import requests
import json
import time
from datetime import datetime
from pathlib import Path
from groq import Groq
import os

# Load environment variables first
load_dotenv()

# Get API key from environment - DO NOT hardcode API keys in source code
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("⚠️ GROQ_API_KEY not found in environment variables")
    print("⚠️ Please set GROQ_API_KEY in your .env file or environment")
    # Exit gracefully or handle appropriately
    raise ValueError("GROQ_API_KEY environment variable is required")
else:
    print(f"GROQ_API_KEY configured: {'Yes' if GROQ_API_KEY else 'No'}")

# Clear proxy environment variables that might interfere with Groq client
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

# Initialize Groq client once at startup
try:
    print("🔧 Attempting to initialize Groq client...")
    print(f"🔑 API Key length: {len(GROQ_API_KEY) if GROQ_API_KEY else 0}")
    groq_client = Groq(api_key=GROQ_API_KEY)
    print("✅ Groq client initialized successfully at startup")
    
    # Test the client with a simple API call
    try:
        models = groq_client.models.list()
        print(f"✅ Groq API connection verified - {len(models.data)} models available")
    except Exception as test_error:
        print(f"⚠️ Groq API test failed: {test_error}")
        
except Exception as e:
    print(f"❌ Failed to initialize Groq client: {e}")
    print(f"❌ Error type: {type(e).__name__}")
    groq_client = None

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
DATA_FOLDER = "data"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)

# ================== SESSION TRACKING ==================
CURRENT_SESSION_FILE = None
CURRENT_SESSION_FILENAME = None

# ================== BUSINESS EXTRACTION ==================
def extract_business_info(text):
    print("🔄 Using fallback business extraction")
    return extract_business_info_fallback(text)

def extract_business_info_fallback(text):
    """Fallback function to extract business info from transcription using basic text processing"""
    import re
    
    result = {
        "personName": "",
        "name": "",
        "address": "",
        "city": "",
        "state": "",
        "pincode": "",
        "gstNumber": "",
        "category": "",
        "subcategory": "",
        "email": "",
        "phone": "",
        "website": "",
        "establishedYear": "",
        "products": []
    }
    
    text_lower = text.lower()
    
    # Extract state
    states = ["andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh", "goa", "gujarat", "haryana", "himachal pradesh", "jammu & kashmir", "jharkhand", "karnataka", "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram", "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu", "telangana", "tripura", "uttar pradesh", "uttarakhand", "west bengal", "chandigarh", "delhi", "hyderabad", "bangalore", "mumbai", "chennai", "kolkata", "pune", "jaipur", "lucknow"]
    for state in states:
        if state in text_lower:
            result["state"] = state.title()
            break
    
    # Extract GST number (should be 15 characters, not 6)
    gst_patterns = [
        r'\b(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z0-9]{1}Z\d{1})\b',
        r'(?:gst|gstin|gst no)\s*[:\-]?\s*([A-Z0-9]{15})',
        r'(?:tax|tin)\s*[:\-]?\s*([A-Z0-9]{15})'
    ]
    for pattern in gst_patterns:
        gst_matches = re.findall(pattern, text.upper())
        if gst_matches:
            result["gstNumber"] = gst_matches[0]
            break
    
    # Extract pincode (6 digits, 优先级高于GST)
    pincode_pattern = r'\b(\d{6})\b'
    pincodes = re.findall(pincode_pattern, text_lower)
    if pincodes:
        # Only treat as pincode if it's not a valid GST format
        pincode = pincodes[0]
        if len(pincode) == 6 and not re.match(r'^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z0-9]{1}Z\d{1}$', pincode.upper()):
            result["pincode"] = pincode
    
    # Extract email
    email_patterns = [
        r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
        r'(?:email|mail|e-mail)\s*[:\-]?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        r'(?:contact|reach)\s+(?:me|us)\s+at\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        r'(?:my email address is|email is)\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    ]
    for pattern in email_patterns:
        emails = re.findall(pattern, text_lower)
        if emails:
            result["email"] = emails[0]
            break
    
    # Extract website
    website_patterns = [
        r'\b((?:https?://|www\.)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
        r'(?:website|site|web|url)\s*[:\-]?\s*((?:https?://|www\.)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        r'(?:visit|check)\s+(?:our|the)\s+website\s*((?:https?://|www\.)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        r'([a-zA-Z0-9.-]+\.(?:com|in|org|net|co|io))',
        r'(?:my website is|my site is|website is)\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        r'(?:email address is|my email is)\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    ]
    for pattern in website_patterns:
        websites = re.findall(pattern, text_lower)
        if websites:
            result["website"] = websites[0]
            break
    
    # Extract established year
    year_patterns = [
        r'(?:established|founded|started|since|year|operating|running)\s+(?:in|from|since)?\s*(\d{4})',
        r'(?:since|from)\s+(\d{4})',
        r'(\d{4})\s+(?:established|founded|started|since)',
        r'(?:business|company|shop)\s+(?:is|was)\s+(?:established|founded|started)\s+(?:in)?\s*(\d{4})'
    ]
    for pattern in year_patterns:
        years = re.findall(pattern, text_lower)
        for year in years:
            if 1900 <= int(year) <= 2024:
                result["establishedYear"] = year
                break
        if result["establishedYear"]:
            break
    
    # Extract city
    cities = ["chandigarh", "hyderabad", "bangalore", "delhi", "mumbai", "chennai", "kolkata", "pune", "jaipur", "lucknow", "ahmedabad", "surat", "nagpur", "indore", "thane", "bhopal", "visakhapatnam", "pimpri", "patna", "vadodara", "ghaziabad", "ludhiana", "agra", "nashik", "faridabad", "meerut", "rajkot", "kalyan", "vasai", "varanasi", "srinagar", "aurangabad", "dhanbad", "amritsar", "navi mumbai", "allahabad", "ranchi", "howrah", "coimbatore", "jabalpur", "gwalior", "vijayawada", "jodhpur", "madurai", "raipur", "kota", "guwahati", "chandigarh", "hubli", "dharwad", "mysore"]
    for city in cities:
        if city in text_lower:
            result["city"] = city.title()
            break
    
    # Extract phone
    phone_patterns = [
        r'\b(\d{10})\b',
        r'(?:phone|mobile|contact|call)\s*[:\-]?\s*(\d{10})',
        r'(?:\+91|0)?\s*(\d{10})',
        r'(?:phone|mobile|contact)\s+(?:number|no)?\s*[:\-]?\s*(\d{10})'
    ]
    for pattern in phone_patterns:
        phones = re.findall(pattern, text_lower)
        if phones:
            result["phone"] = phones[0]
            break
    
    # Extract person name
    person_patterns = [
        r'myself is ([a-zA-Z\s]+)',
        r'(?:my name is|i am|this is|myself)\s+is\s+([a-zA-Z\s]+?)(?:\s+(?:and|so|feed|my|i|from|at|in|owner|live|reside))',
        r'(?:my name is|i am|this is|myself)\s+([a-zA-Z\s]+?)(?:\s+(?:and|so|feed|my|i|from|at|in|owner|live|reside))',
        r'(?:i\'m|i am)\s+([a-zA-Z\s]+?)(?:\s+(?:and|so|feed|my|from|at|in|live|reside))',
        r'(?:myself)\s+([a-zA-Z\s]+?)(?:\s+(?:and|i|owner|from|business|live|reside))',
        r'([a-zA-Z\s]+?)(?:\s+is my name)',
        r'calling\s+([a-zA-Z\s]+?)(?:\s+(?:and|so|feed|my|i))',
        r'([a-zA-Z\s]+?)(?:\s+and\s+i\s+live)'
    ]
    
    for pattern in person_patterns:
        match = re.search(pattern, text_lower)
        if match:
            name = match.group(1).strip().title()
            if len(name) > 2 and len(name) < 50:
                result["personName"] = name
                break
    
    # Extract business name
    name_patterns = [
        r'(?:my name is|my business is|i own|we are|this is)\s+([a-zA-Z\s]+?)(?:\s+(?:in|at|and|located|so|feed|business|shop|store))',
        r'business\s+name\s+is\s+([a-zA-Z\s]+?)(?:\s+(?:and|we|located|in|at))',
        r'we\s+are\s+([a-zA-Z\s]+?)(?:\s+(?:and|we|located|in|at|business))',
        r'name\s+is\s+([a-zA-Z\s]+?)(?:\s+(?:and|so|feed|business|shop|store))',
        r'(?:running|operating)\s+([a-zA-Z\s]+?)(?:\s+(?:business|shop|store|firm|company))',
        r'([a-zA-Z\s]+?)(?:\s+(?:business|shop|store|firm|company)\s+name)'
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, text_lower)
        if match:
            name = match.group(1).strip().title()
            if len(name) > 2 and len(name) < 50:
                result["name"] = name
                break
    
    # Extract address
    address_patterns = [
        r'(?:located|address|at|in|shop at|store at)\s+([a-zA-Z0-9\s,\-#]+?)(?:\s+(?:city|and|we|phone|state|near|beside|opposite))',
        r'address\s+is\s+([a-zA-Z0-9\s,\-#]+?)(?:\s+(?:city|and|we|phone|state|near|beside|opposite))',
        r'(?:shop|store|business)\s+(?:is\s+)?(?:located|situated)\s+at\s+([a-zA-Z0-9\s,\-#]+?)(?:\s+(?:city|and|we|phone|state|near|beside|opposite))',
        r'([a-zA-Z0-9\s,\-#]+?)(?:\s+(?:road|street|lane|nagar|colony|area|sector))'
    ]
    
    for pattern in address_patterns:
        match = re.search(pattern, text_lower)
        if match:
            address = match.group(1).strip().title()
            if len(address) > 3 and len(address) < 100:
                result["address"] = address
                break
    
    # Extract category
    categories = {
        "retail": ["retail", "shop", "store", "grocery", "market", "supermarket", "mart", "bazaar", "outlet"],
        "food & restaurant": ["food", "restaurant", "cafe", "hotel", "eatery", "sweet", "treat", "bakery", "dining", "catering", "food court"],
        "services": ["service", "consulting", "repair", "maintenance", "cleaning", "salon", "spa", "fitness"],
        "manufacturing": ["manufacturing", "factory", "production", "industry", "plant", "workshop"],
        "healthcare": ["health", "medical", "hospital", "clinic", "pharmacy", "diagnostic", "wellness"],
        "education": ["education", "school", "college", "tuition", "institute", "academy", "training", "coaching"],
        "technology": ["tech", "software", "computer", "it", "digital", "app", "website", "automation"],
        "agriculture": ["agriculture", "farming", "crops", "seeds", "horticulture", "dairy", "poultry"],
        "textile": ["textile", "clothing", "garments", "fashion", "apparel", "boutique", "fabrics"],
        "automotive": ["automotive", "car", "vehicle", "motor", "auto", "garage", "showroom"],
        "real estate": ["property", "real estate", "construction", "builder", "developer", "housing"],
        "finance": ["finance", "banking", "loan", "insurance", "investment", "accounting"],
        "transportation": ["transport", "logistics", "shipping", "delivery", "cargo", "courier"],
        "entertainment": ["entertainment", "media", "gaming", "cinema", "music", "events"]
    }
    
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in text_lower:
                result["category"] = category.title()
                break
        if result["category"]:
            break
    
    # Extract subcategory
    subcategories = {
        "electronics": ["mobile", "phone", "laptop", "computer", "tablet", "tv", "electronics", "gadgets"],
        "jewelry": ["jewelry", "gold", "silver", "diamond", "ornaments", "accessories"],
        "books & stationery": ["books", "stationery", "notebooks", "pens", "paper", "office supplies"],
        "home appliances": ["appliances", "refrigerator", "washing machine", "microwave", "kitchen", "home"],
        "furniture": ["furniture", "sofa", "bed", "table", "chair", "wood", "interior"],
        "sports & fitness": ["sports", "fitness", "gym", "equipment", "exercise", "yoga"],
        "toys & games": ["toys", "games", "children", "kids", "play", "fun"],
        "beauty & cosmetics": ["beauty", "cosmetics", "makeup", "skincare", "hair", "salon"],
        "bakery & confectionery": ["bakery", "confectionery", "cakes", "pastries", "sweets", "desserts"],
        "beverages": ["beverages", "drinks", "juice", "tea", "coffee", "cold drinks"],
        "hardware": ["hardware", "tools", "plumbing", "electrical", "building materials"],
        "pet supplies": ["pet", "animals", "dog", "cat", "food", "supplies"]
    }
    
    for subcategory, keywords in subcategories.items():
        for keyword in keywords:
            if keyword in text_lower:
                result["subcategory"] = subcategory.title()
                break
        if result["subcategory"]:
            break
    # Extract business type/size
    business_types = {
        "proprietorship": ["proprietor", "sole proprietor", "individual", "owner"],
        "partnership": ["partnership", "partner", "joint venture"],
        "private limited": ["private limited", "pvt ltd", "private ltd"],
        "limited company": ["limited company", "ltd", "public limited"],
        "llp": ["llp", "limited liability partnership"],
        "startup": ["startup", "start up", "new business", "emerging"],
        "small business": ["small business", "sme", "small medium", "micro"],
        "large enterprise": ["large enterprise", "corporate", "multinational", "mnc"]
    }
    
    for business_type, keywords in business_types.items():
        for keyword in keywords:
            if keyword in text_lower:
                result["businessType"] = business_type.title()
                break
        if result.get("businessType"):
            break
    
    # Extract products
    product_keywords = ["vegetable", "fruit", "rice", "milk", "bread", "sweet", "snack", "food", "grocery", "tomato", "potato", "onion", "egg", "chicken", "meat", "fish"]
    found_products = []
    
    # First try pattern-based extraction for structured product info
    product_patterns = [
        r'(\d+)\s+(kg|grams|pcs|pieces|liter|litre|dozen|packet|bottle|box)\s+(\w+)\s+(?:at|@|for|rupees?|rs\.?|₹)\s*(\d+)',
        r'(\w+)\s+(kg|grams|pcs|pieces|liter|litre|dozen|packet|bottle|box)\s+(?:at|@|for|rupees?|rs\.?|₹)\s*(\d+)',
        r'(\w+)\s+(?:at|@|for|rupees?|rs\.?|₹)\s*(\d+)\s+(?:per\s+)?(kg|grams|pcs|pieces|liter|litre|dozen|packet|bottle|box)',
        r'(\w+)\s+(?:at|@|for|rupees?|rs\.?|₹)\s*(\d+)',
        r'(\d+)\s+(kg|grams|pcs|pieces|liter|litre|dozen|packet|bottle|box)\s+(\w+)'
    ]
    
    # Extract structured products first
    for pattern in product_patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            if isinstance(match, tuple):
                if len(match) == 4:  # quantity, unit, name, price
                    quantity, unit, name, price = match
                    if name not in [p[0] for p in found_products]:  # avoid duplicates
                        found_products.append({
                            "name": name.title(),
                            "price": int(price),
                            "category": "General",
                            "subcategory": "",
                            "description": f"Fresh {name.title()}",
                            "unit": unit,
                            "unitQuantity": int(quantity),
                            "minimumOrderQuantity": 1,
                            "quantity": int(quantity)
                        })
                elif len(match) == 3:  # name, price, unit OR quantity, unit, name
                    if match[1].isdigit():  # quantity, unit, name
                        quantity, unit, name = match
                        if name not in [p[0] for p in found_products]:
                            found_products.append({
                                "name": name.title(),
                                "price": int(match[2]),
                                "category": "General", 
                                "subcategory": "",
                                "description": f"Fresh {name.title()}",
                                "unit": unit,
                                "unitQuantity": int(quantity),
                                "minimumOrderQuantity": 1,
                                "quantity": int(quantity)
                            })
                    else:  # name, price, unit
                        name, price, unit = match
                        if name not in [p[0] for p in found_products]:
                            found_products.append({
                                "name": name.title(),
                                "price": int(price),
                                "category": "General",
                                "subcategory": "",
                                "description": f"Fresh {name.title()}",
                                "unit": unit,
                                "unitQuantity": 1,
                                "minimumOrderQuantity": 1,
                                "quantity": 1
                            })
                elif len(match) == 2:  # name, price OR quantity, unit
                    if match[0].isdigit():  # quantity, unit
                        quantity, unit = match
                        # This is likely just quantity+unit without name, skip
                    else:  # name, price
                        name, price = match
                        if name not in [p[0] for p in found_products]:
                            found_products.append({
                                "name": name.title(),
                                "price": int(price),
                                "category": "General",
                                "subcategory": "",
                                "description": f"Fresh {name.title()}",
                                "unit": "pcs",
                                "unitQuantity": 1,
                                "minimumOrderQuantity": 1,
                                "quantity": 1
                            })
    
    # If no structured products found, look for individual product keywords
    if not found_products:
        for keyword in product_keywords:
            if keyword in text_lower:
                if keyword.endswith('y'):
                    plural = keyword[:-1] + 'ies'
                else:
                    plural = keyword + 's'
                
                if keyword in text_lower and keyword not in [p["name"] for p in found_products]:
                    found_products.append({
                        "name": keyword.title(),
                        "price": 0,
                        "category": "General",
                        "subcategory": "",
                        "description": f"Fresh {keyword.title()}",
                        "unit": "pcs",
                        "unitQuantity": 1,
                        "minimumOrderQuantity": 1,
                        "quantity": 1
                    })
                elif plural in text_lower and plural not in [p["name"] for p in found_products]:
                    found_products.append({
                        "name": plural.title(),
                        "price": 0,
                        "category": "General",
                        "subcategory": "", 
                        "description": f"Fresh {plural.title()}",
                        "unit": "pcs",
                        "unitQuantity": 1,
                        "minimumOrderQuantity": 1,
                        "quantity": 1
                    })
    
    result["products"] = found_products[:5]
    
    return result

# ================== PRODUCT EXTRACTION ==================
def extract_products_llm(text):
    """Extract products using Groq LLM with structured output"""
    try:
        if not groq_client:
            print("❌ Groq client not available for LLM extraction")
            return None
            
        prompt = f"""Extract product information from the following text.
Return a JSON array of products with these exact fields:
- name: product name (can be multiple words, e.g., "Premium Basmati Rice")
- price: price per unit in rupees (number only, use 0 if not mentioned)
- unit: unit of measurement (kg, gram, liter, piece, pcs, etc. - use lowercase)
- unitQuantity: total quantity available (number only, use 1 if not mentioned)
- minimumOrderQuantity: minimum order quantity (number only, use 1 if not mentioned)
- category: product category (Groceries, Electronics, Clothing, Food, etc.)
- subcategory: product subcategory (Rice, Wheat, Vegetables, etc.)
- description: brief description

Important extraction rules:
- Extract the FULL product name including adjectives (e.g., "Premium Basmati Rice" not just "Rice")
- Look for price keywords: "price is", "costs", "rupees", "rs", "per kg", "per unit"
- Look for category keywords: "category", "category is"
- Look for subcategory keywords: "subcategory", "subcategory is", "type"
- Look for total quantity keywords: "total quantity available", "available", "stock", "quantity available"
- Look for minimum order keywords: "minimum order quantity", "min order", "minimum quantity"
- Look for unit keywords: "units is", "unit", "per kg", "per liter"
- Convert "kilogram" to "kg", "piece" to "pcs", "pieces" to "pcs"

Text: {text}

Return ONLY a valid JSON array, no other text. Example format:
[{{"name": "Premium Basmati Rice", "price": 12, "unit": "kg", "unitQuantity": 50, "minimumOrderQuantity": 5, "category": "Groceries", "subcategory": "Rice", "description": "High quality aged Basmati rice perfect for biryani and daily cooking"}}]"""

        print("🤖 Calling Groq LLM for product extraction...")
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1500
        )
        
        result = response.choices[0].message.content.strip()
        print(f"📝 LLM Response: {result[:200]}...")
        
        # Try to extract JSON from response
        # Sometimes LLM wraps JSON in markdown code blocks
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            result = result.split("```")[1].split("```")[0].strip()
        
        products = json.loads(result)
        
        if not isinstance(products, list):
            print("❌ LLM response is not a list")
            return None
            
        print(f"✅ LLM extracted {len(products)} products")
        return products
        
    except json.JSONDecodeError as e:
        print(f"❌ LLM extraction JSON parse error: {e}")
        print(f"   Raw response: {result[:200]}")
        return None
    except Exception as e:
        print(f"❌ LLM extraction failed: {e}")
        return None

def extract_products(text):
    """Extract products using LLM first, fallback to regex"""
    # Try LLM extraction first
    print("🤖 Attempting LLM product extraction...")
    llm_products = extract_products_llm(text)
    
    if llm_products and len(llm_products) > 0:
        print(f"✅ Using LLM-extracted products: {len(llm_products)} products")
        return llm_products
    
    # Fallback to regex
    print("🔄 LLM extraction failed or returned no products, using regex fallback")
    return extract_products_fallback(text)

def extract_products_fallback(text):
    """Fallback function to extract products from transcription"""
    import re
    
    text_lower = text.lower()
    products = []
    
    # Pattern priority order (most specific to least specific):
    # 1. name quantity unit price: "rice 2 kg 400"
    # 2. quantity unit name price: "2 kg rice 400" 
    # 3. name unit price: "rice kg 400"
    # 4. name price unit: "rice 400 kg"
    # 5. name price: "rice 400"
    product_patterns = [
        # Pattern: name(noun) quantity(number) unit price(number) - e.g., "rice 2 kg 400"
        r'([a-zA-Z]+)\s+(\d+)\s+(kg|grams|pcs|pieces|liter|litre|dozen|packet|bottle|box)\s+(?:at|@|for|rupees?|rs\.?|₹)?\s*(\d+)',
        # Pattern: quantity(number) unit name(noun) price(number) - e.g., "2 kg rice 400"
        r'(\d+)\s+(kg|grams|pcs|pieces|liter|litre|dozen|packet|bottle|box)\s+([a-zA-Z]+)\s+(?:at|@|for|rupees?|rs\.?|₹)?\s*(\d+)',
        # Pattern: name(noun) unit price(number) - e.g., "rice kg 400"
        r'([a-zA-Z]+)\s+(kg|grams|pcs|pieces|liter|litre|dozen|packet|bottle|box)\s+(?:at|@|for|rupees?|rs\.?|₹)?\s*(\d+)',
        # Pattern: name(noun) price(number) unit - e.g., "rice 400 kg"
        r'([a-zA-Z]+)\s+(?:at|@|for|rupees?|rs\.?|₹)?\s*(\d+)\s+(?:per\s+)?(kg|grams|pcs|pieces|liter|litre|dozen|packet|bottle|box)',
        # Pattern: name(noun) price(number) - e.g., "rice 400"
        r'([a-zA-Z]+)\s+(?:at|@|for|rupees?|rs\.?|₹)?\s*(\d+)',
    ]
    
    product_keywords = [
        "tomato", "potato", "onion", "vegetable", "fruit", "rice", "wheat", "flour",
        "milk", "bread", "egg", "chicken", "meat", "fish", "sugar", "salt", "oil",
        "tea", "coffee", "butter", "cheese", "curd", "sweet", "snack", "chocolate",
        "biscuit", "soap", "shampoo", "toothpaste", "detergent", "paper", "pen"
    ]
    
    category_keywords = {
        "Groceries": ["tomato", "potato", "onion", "vegetable", "fruit", "rice", "wheat", "flour", "milk", "bread", "egg", "chicken", "meat", "fish", "sugar", "salt", "oil", "tea", "coffee", "butter", "cheese", "curd"],
        "Food": ["sweet", "snack", "chocolate", "biscuit"],
        "Electronics": ["phone", "laptop", "computer", "tablet", "camera", "tv", "headphone", "speaker"],
        "Clothing": ["shirt", "pants", "dress", "jeans", "t-shirt", "jacket", "shoes", "socks"],
        "Home & Kitchen": ["soap", "shampoo", "toothpaste", "detergent", "paper", "pen", "plate", "cup", "bowl"],
        "Books": ["book", "notebook", "pen", "paper"],
        "Toys": ["toy", "game", "puzzle", "doll"],
        "Sports": ["ball", "bat", "racket", "shoes", "equipment"],
        "Beauty": ["lipstick", "cream", "makeup", "perfume", "shampoo", "soap"],
        "Health": ["medicine", "tablet", "vitamin", "cream", "oil"]
    }
    
    subcategory_keywords = {
        "Rice": ["rice", "basmati"],
        "Wheat": ["wheat", "atta", "flour"],
        "Vegetables": ["tomato", "potato", "onion", "vegetable"],
        "Fruits": ["fruit", "apple", "banana", "mango"],
        "Dairy": ["milk", "butter", "cheese", "curd"],
        "Bakery": ["bread", "biscuit", "cake"],
        "Meat": ["chicken", "meat", "fish", "egg"],
        "Spices": ["sugar", "salt", "oil", "tea", "coffee"]
    }
    
    extracted_names = set()
    
    # Unit keywords and stopwords that should never be product names
    unit_keywords = {
        'kg', 'grams', 'pcs', 'pieces', 'liter', 'litre', 'dozen', 'packet', 'bottle', 'box', 'gram', 'kilogram',
        'is', 'are', 'was', 'were', 'total', 'quantity', 'available', 'min', 'minimum', 'max', 'maximum', 'order',
        'rs', 'rupees', 'price', 'cost', 'unit', 'units'
    }
    
    # Extract category from text
    extracted_category = "General"
    category_match = re.search(r'category\s+(?:is\s+)?([a-zA-Z\s]+?)(?:\s+(?:subcategory|units|price|quantity|minimum|description|this|perfect|high|quality))', text_lower)
    if category_match:
        extracted_category = category_match.group(1).strip().title()
    
    # Extract subcategory from text
    extracted_subcategory = ""
    subcategory_match = re.search(r'subcategory\s+(?:is\s+)?([a-zA-Z\s]+?)(?:\s+(?:units|price|quantity|minimum|description|this|perfect|high|quality))', text_lower)
    if subcategory_match:
        extracted_subcategory = subcategory_match.group(1).strip().title()
    
    # Extract total quantity available
    total_quantity = 1
    quantity_match = re.search(r'(?:total\s+)?quantity\s+(?:available\s+)?(?:is\s+)?(\d+)', text_lower)
    if quantity_match:
        total_quantity = int(quantity_match.group(1))
    
    # Extract minimum order quantity
    min_order_quantity = 1
    min_order_match = re.search(r'minimum\s+order\s+quantity\s+(?:is\s+)?(\d+)', text_lower)
    if min_order_match:
        min_order_quantity = int(min_order_match.group(1))
    
    # Process each pattern in priority order
    for pattern_idx, pattern in enumerate(product_patterns):
        matches = re.findall(pattern, text_lower)
        for match in matches:
            if not isinstance(match, tuple):
                continue
                
            name = None
            quantity = 1
            unit = "pcs"
            price = 0
            
            # Pattern 0: name quantity unit price - e.g., "rice 2 kg 400"
            if pattern_idx == 0 and len(match) == 4:
                name, quantity, unit, price = match
                quantity = int(quantity)
                price = int(price)
            
            # Pattern 1: quantity unit name price - e.g., "2 kg rice 400"
            elif pattern_idx == 1 and len(match) == 4:
                quantity, unit, name, price = match
                quantity = int(quantity)
                price = int(price)
            
            # Pattern 2: name unit price - e.g., "rice kg 400"
            elif pattern_idx == 2 and len(match) == 3:
                name, unit, price = match
                price = int(price)
                quantity = 1
            
            # Pattern 3: name price unit - e.g., "rice 400 kg"
            elif pattern_idx == 3 and len(match) == 3:
                name, price, unit = match
                price = int(price)
                quantity = 1
            
            # Pattern 4: name price - e.g., "rice 400"
            elif pattern_idx == 4 and len(match) == 2:
                name, price = match
                price = int(price)
                quantity = 1
                unit = "pcs"
            
            # Add product if name was extracted, is not a unit keyword, and not already seen
            if name and name not in unit_keywords and name not in extracted_names:
                extracted_names.add(name)
                category = extracted_category if extracted_category != "General" else get_product_category(name, category_keywords)
                subcategory = extracted_subcategory if extracted_subcategory else get_product_subcategory(name, subcategory_keywords)
                products.append({
                    "name": name.title(),
                    "price": price,
                    "unit": unit,
                    "unitQuantity": total_quantity,
                    "minimumOrderQuantity": min_order_quantity,
                    "category": category,
                    "subcategory": subcategory,
                    "description": f"Fresh {name.title()}"
                })
    
    for keyword in product_keywords:
        if keyword in text_lower and keyword not in extracted_names:
            extracted_names.add(keyword)
            category = extracted_category if extracted_category != "General" else get_product_category(keyword, category_keywords)
            subcategory = extracted_subcategory if extracted_subcategory else get_product_subcategory(keyword, subcategory_keywords)
            products.append({
                "name": keyword.title(),
                "price": 0,
                "unit": "pcs",
                "unitQuantity": total_quantity,
                "minimumOrderQuantity": min_order_quantity,
                "category": category,
                "subcategory": subcategory,
                "description": f"Fresh {keyword.title()}"
            })
    
    unique_products = []
    seen = set()
    for product in products:
        key = (product["name"], product["unit"])
        if key not in seen:
            seen.add(key)
            unique_products.append(product)
    
    return unique_products[:5]

def get_product_category(product_name, category_keywords):
    """Helper function to determine product category"""
    product_lower = product_name.lower()
    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in product_lower:
                return category
    return "General"

def get_product_subcategory(product_name, subcategory_keywords):
    """Helper function to determine product subcategory"""
    product_lower = product_name.lower()
    for subcategory, keywords in subcategory_keywords.items():
        for keyword in keywords:
            if keyword in product_lower:
                return subcategory
    return ""

# ================== TRANSCRIPTION ==================
def transcribe_audio(path):
    """Transcribe audio using Groq Whisper API"""
    try:
        # Check if Groq client is initialized
        if groq_client is None:
            print("❌ Groq client not initialized")
            return "Groq API client initialization failed. Please check API key."
        
        # Check file exists and size
        if not os.path.exists(path):
            print(f"❌ Audio file not found: {path}")
            return "Audio file not found"
        
        file_size = os.path.getsize(path)
        print(f"📁 Audio file size: {file_size / 1024:.2f} KB")

        # Check file size limit (25MB for Groq)
        if file_size > 25 * 1024 * 1024:
            print("❌ Audio file too large")
            return "Audio file too large (max 25MB). Please record shorter audio."
        
        if file_size < 100:
            print("❌ Audio file too small")
            return "Audio file too small. Please record again."

        # Convert WebM to WAV for better compatibility
        if path.endswith('.webm'):
            try:
                from pydub import AudioSegment
                wav_path = path.replace(".webm", ".wav")
                AudioSegment.from_file(path).export(wav_path, format="wav")
                path = wav_path
                print(f"🔄 Converted WebM to WAV: {path}")
            except ImportError:
                print("⚠️ pydub not installed, using original file")
            except Exception as e:
                print(f"⚠️ Audio conversion failed: {e}, using original file")

        # Transcribe using Groq Whisper
        print("📤 Sending audio to Groq Whisper API...")
        
        with open(path, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                file=audio_file,  # send file object, NOT read()
                model="whisper-large-v3",
                response_format="text",  # simpler + more stable
                temperature=0,
                language="en"  # Force English-only transcription
            )
        
        text = transcription.strip()
        print(f"✅ Transcription successful ({len(text)} chars)")
        print(f"📝 Transcribed text: {text[:200]}...")

        if not text or len(text.strip()) < 3:
            print("⚠️ Transcription too short or empty")
            return "No speech detected. Please speak clearly and try again."

        return text

    except Exception as e:
        print("FULL ERROR:", repr(e))
        print(f"❌ Transcription error: {type(e).__name__}: {str(e)}")
        
        # Check for specific network/API errors
        error_str = str(e).lower()
        if "network" in error_str or "connection" in error_str or "timeout" in error_str:
            return "Network error: Unable to connect to transcription service. Please check your internet connection and try again."
        elif "unauthorized" in error_str or "authentication" in error_str or "401" in error_str:
            return "Authentication error: Invalid API key. Please check your Groq API key."
        elif "rate limit" in error_str or "429" in error_str:
            return "Rate limit error: Too many requests. Please wait a moment and try again."
        elif "400" in error_str or "bad request" in error_str:
            return "Audio format error: The audio file may be corrupted or in an unsupported format."
        else:
            return f"Transcription failed: {str(e)}"

# ================== ROUTES ==================
@app.route("/")
def index():
    return jsonify({
        "message": "Ekthaa AI STT Backend API is running",
        "endpoints": [
            "/upload_business_audio (POST)",
            "/upload_product_audio (POST)", 
            "/save (POST)",
            "/get_sessions (GET)",
            "/get_session/<filename> (GET)",
            "/delete_session/<filename> (DELETE)"
        ]
    })

@app.route("/api")
def api_info():
    return jsonify({
        "message": "Flask API is running",
        "react_app": "http://localhost:3000",
        "groq_status": "initialized" if groq_client else "not initialized",
        "endpoints": [
            "/upload_business_audio",
            "/upload_product_audio", 
            "/save",
            "/get_sessions",
            "/get_session/<filename>",
            "/delete_session/<filename>"
        ]
    })

@app.route("/upload_business_audio", methods=["POST"])
def upload_business_audio():
    global CURRENT_SESSION_FILE, CURRENT_SESSION_FILENAME
    try:
        print("🎤 Received business audio upload request")
        
        if 'audio' not in request.files:
            print("❌ No audio file in request")
            return jsonify({"error": "No audio file provided"}), 400
            
        audio = request.files["audio"]
        if audio.filename == '':
            print("❌ Empty audio filename")
            return jsonify({"error": "No audio file selected"}), 400
            
        print(f"📁 Audio file received: {audio.filename}")
        
        path = os.path.join(UPLOAD_FOLDER, "business_audio.webm")
        audio.save(path)
        print(f"💾 Audio saved to: {path}")

        print("🔍 Starting transcription...")
        transcript = transcribe_audio(path)
        
        # Check if transcription failed
        if transcript.startswith("Transcription failed") or transcript.startswith("Groq") or transcript.startswith("Audio"):
            print(f"❌ Transcription error: {transcript}")
            return jsonify({"error": transcript}), 400
        
        print(f"📝 Transcription completed: {transcript[:100]}...")
        
        print("🤖 Starting business info extraction...")
        data = extract_business_info(transcript)
        print(f"✅ Extraction completed")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        CURRENT_SESSION_FILENAME = f"session_{timestamp}.json"
        CURRENT_SESSION_FILE = os.path.join(DATA_FOLDER, CURRENT_SESSION_FILENAME)

        # Format products properly
        products = data.get("products", [])
        formatted_products = []
        for item in products:
            if isinstance(item, str):
                formatted_products.append({
                    "name": item,
                    "price": 0,
                    "category": "",
                    "subcategory": "",
                    "description": f"Fresh {item}",
                    "unit": "",
                    "unitQuantity": 1,
                    "minimumOrderQuantity": 1,
                    "quantity": 1
                })
            elif isinstance(item, dict):
                formatted_products.append({
                    "name": item.get("name", ""),
                    "price": item.get("price", 0),
                    "category": item.get("category", ""),
                    "subcategory": item.get("subcategory", ""),
                    "description": item.get("description", ""),
                    "unit": item.get("unit", ""),
                    "unitQuantity": item.get("unitQuantity", 1),
                    "minimumOrderQuantity": item.get("minimumOrderQuantity", 1),
                    "quantity": item.get("quantity", 1)
                })
            else:
                formatted_products.append({
                    "name": str(item),
                    "price": 0,
                    "category": "",
                    "subcategory": "",
                    "description": f"Fresh {item}",
                    "unit": "",
                    "unitQuantity": 1,
                    "minimumOrderQuantity": 1,
                    "quantity": 1
                })

        final_json = {
            "personName": data.get("personName", ""),
            "name": data.get("name", ""),
            "address": data.get("address", ""),
            "city": data.get("city", ""),
            "state": data.get("state", ""),
            "pincode": data.get("pincode", ""),
            "gstNumber": data.get("gstNumber", ""),
            "category": data.get("category", ""),
            "subcategory": data.get("subcategory", ""),
            "businessType": data.get("businessType", ""),
            "email": data.get("email", ""),
            "phone": data.get("phone", ""),
            "website": data.get("website", ""),
            "establishedYear": data.get("establishedYear", ""),
            "products": formatted_products,
            "transcription": transcript
        }

        with open(CURRENT_SESSION_FILE, "w") as f:
            json.dump(final_json, f, indent=4)
        
        print(f"💾 Session saved to: {CURRENT_SESSION_FILE}")

        return jsonify({
            "data": final_json, 
            "filename": CURRENT_SESSION_FILENAME,
            "transcription": transcript
        })
        
    except Exception as e:
        print(f"❌ Error in upload_business_audio: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/upload_product_audio", methods=["POST"])
def upload_product_audio():
    global CURRENT_SESSION_FILE, CURRENT_SESSION_FILENAME
    try:
        print("🛒 Received product audio upload request")
        
        if not CURRENT_SESSION_FILE:
            print("📝 No business session found, creating new session for products")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            CURRENT_SESSION_FILENAME = f"session_{timestamp}.json"
            CURRENT_SESSION_FILE = os.path.join(DATA_FOLDER, CURRENT_SESSION_FILENAME)
            
            basic_session = {
                "personName": "",
                "name": "",
                "address": "",
                "city": "",
                "state": "",
                "pincode": "",
                "gstNumber": "",
                "category": "",
                "subcategory": "",
                "businessType": "",
                "email": "",
                "phone": "",
                "website": "",
                "establishedYear": "",
                "products": [],
                "transcription": ""
            }
            
            with open(CURRENT_SESSION_FILE, "w") as f:
                json.dump(basic_session, f, indent=4)
            
            print(f"📁 Created new session: {CURRENT_SESSION_FILE}")

        if 'audio' not in request.files:
            print("❌ No audio file in request")
            return jsonify({"error": "No audio file provided"}), 400
            
        audio = request.files["audio"]
        if audio.filename == '':
            print("❌ Empty audio filename")
            return jsonify({"error": "No audio file selected"}), 400
            
        print(f"📁 Audio file received: {audio.filename}")

        path = os.path.join(UPLOAD_FOLDER, "product_audio.webm")
        audio.save(path)
        print(f"💾 Audio saved to: {path}")

        print("🔍 Starting transcription...")
        transcript = transcribe_audio(path)
        
        # Check if transcription failed
        if transcript.startswith("Transcription failed") or transcript.startswith("Groq") or transcript.startswith("Audio"):
            print(f"❌ Transcription error: {transcript}")
            return jsonify({"error": transcript}), 400
        
        print(f"📝 Transcription completed: {transcript[:100]}...")
        
        print("🤖 Starting product extraction...")
        products = extract_products(transcript)
        print(f"✅ Product extraction completed: {len(products)} products found")

        with open(CURRENT_SESSION_FILE, "r") as f:
            session_data = json.load(f)

        existing_products = session_data.get("products", [])
        combined_products = existing_products + products

        session_data["products"] = combined_products
        session_data["transcription"] = transcript

        with open(CURRENT_SESSION_FILE, "w") as f:
            json.dump(session_data, f, indent=4)
        
        print(f"💾 Session updated with products: {CURRENT_SESSION_FILE}")

        return jsonify({
            "data": session_data, 
            "filename": CURRENT_SESSION_FILENAME,
            "transcription": transcript
        })
        
    except Exception as e:
        print(f"❌ Error in upload_product_audio: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/save", methods=["POST"])
def save_edited_data():
    data = request.json
    filename = data.get("filename")
    session_data = data.get("data")
    
    if not filename or not session_data:
        return jsonify({"error": "Missing filename or data"}), 400
    
    file_path = os.path.join(DATA_FOLDER, filename)
    
    if "transcription" not in session_data:
        session_data["transcription"] = ""
    
    with open(file_path, "w") as f:
        json.dump(session_data, f, indent=4)
    
    return jsonify({"success": True, "message": "Data saved successfully"})

@app.route("/editor")
def editor():
    files = sorted(os.listdir(DATA_FOLDER))
    if not files:
        return "No sessions found"

    with open(os.path.join(DATA_FOLDER, files[-1])) as f:
        data = json.load(f)
    
    if "transcription" not in data:
        data["transcription"] = ""
    
    return jsonify(data)

@app.route("/get_session/<filename>")
def get_session(filename):
    file_path = os.path.join(DATA_FOLDER, filename)
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            data = json.load(f)
        
        if "transcription" not in data:
            data["transcription"] = ""
            
        return jsonify(data)
    else:
        return jsonify({"error": "Session file not found"}), 404

@app.route("/get_sessions")
def get_sessions():
    try:
        files = sorted(os.listdir(DATA_FOLDER))
        sessions = []
        
        for filename in files:
            if filename.endswith('.json'):
                file_path = os.path.join(DATA_FOLDER, filename)
                try:
                    with open(file_path, "r") as f:
                        data = json.load(f)
                    
                    if "transcription" not in data:
                        data["transcription"] = ""
                        
                    sessions.append({
                        "filename": filename,
                        "data": data
                    })
                except Exception as e:
                    print(f"Error reading file {filename}: {e}")
                    continue
        
        return jsonify(sessions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/delete_session/<filename>", methods=["DELETE"])
def delete_session(filename):
    try:
        file_path = os.path.join(DATA_FOLDER, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({"success": True, "message": "Session deleted successfully"})
        else:
            return jsonify({"error": "Session file not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 Starting Flask Backend Server")
    print("="*50)
    print(f"✅ Groq API Status: {'Connected' if groq_client else 'Not Connected'}")
    print(f"📂 Upload Folder: {UPLOAD_FOLDER}")
    print(f"📂 Data Folder: {DATA_FOLDER}")
    print("="*50 + "\n")
    app.run(debug=True, port=5001)
