import math
import re
import json
import os

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculates great-circle distance between two coordinates in kilometers.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    try:
        lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371.0  # Earth's radius in km
        return round(c * r, 2)
    except (ValueError, TypeError):
        return None


def parse_prompt_with_llm(prompt):
    """
    Parses unstructured prompt into structured search filters using external LLM
    or robust heuristic fallback architecture.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            system_prompt = (
                "You are an AI assistant for a food delivery platform. "
                "Extract structured search filters from the user query into a clean JSON object with keys: "
                "'cuisine' (string or null), "
                "'price_range' (string like '$', '$$', '$$$' or null), "
                "'min_rating' (float or null), "
                "'dietary_flag' (string like 'halal', 'vegan', 'vegetarian', 'gluten-free' or null), "
                "'location_keyword' (string or null). "
                "Output raw JSON only without markdown formatting."
            )
            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                timeout=5.0
            )
            content = completion.choices[0].message.content.strip()
            # Clean markdown codeblocks if LLM returned any
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\s*", "", content)
                content = re.sub(r"\s*```$", "", content)
            return json.loads(content)
        except Exception:
            pass  # Proceed to resilient fallback

    # Intelligent Heuristic Fallback Parser
    filters = {
        "cuisine": None,
        "price_range": None,
        "min_rating": None,
        "dietary_flag": None,
        "location_keyword": None,
    }
    prompt_lower = prompt.lower()

    # Cuisines
    known_cuisines = [
        "bangladeshi", "bengali", "thai", "italian", "chinese", "mexican", 
        "japanese", "pan-asian", "indian", "biryani", "burger", "pizza", 
        "grill", "cafe", "bakery", "meat", "ramen", "taco"
    ]
    for c in known_cuisines:
        if c in prompt_lower:
            filters["cuisine"] = c
            break

    # Dietary flags
    known_dietary = ["halal", "vegan", "vegetarian", "gluten-free"]
    for d in known_dietary:
        if d in prompt_lower:
            filters["dietary_flag"] = d
            break

    # Rating
    if "high rating" in prompt_lower or "top rated" in prompt_lower or "best" in prompt_lower:
        filters["min_rating"] = 4.0
    rating_match = re.search(r"(\d(?:\.\d)?)\s*(?:\+|star|stars|rating)", prompt_lower)
    if rating_match:
        try:
            filters["min_rating"] = float(rating_match.group(1))
        except ValueError:
            pass

    # Price
    if "$$$" in prompt or "expensive" in prompt_lower or "fine dining" in prompt_lower:
        filters["price_range"] = "$$$"
    elif "$$" in prompt or "moderate" in prompt_lower or "mid range" in prompt_lower:
        filters["price_range"] = "$$"
    elif "$" in prompt or "cheap" in prompt_lower or "budget" in prompt_lower or "affordable" in prompt_lower:
        filters["price_range"] = "$"

    # Location keyword
    locations = ["gulshan", "banani", "dhanmondi", "uttara", "mirpur", "chittagong", "sylhet", "old dhaka", "dohs"]
    for loc in locations:
        if loc in prompt_lower:
            filters["location_keyword"] = loc
            break

    # If no cuisine matched but keywords exist, assign raw prompt for fallback search
    if not filters["cuisine"] and not filters["location_keyword"]:
        filters["cuisine"] = prompt.strip()

    return filters

