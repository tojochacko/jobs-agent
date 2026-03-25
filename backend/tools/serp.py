import requests
from backend.config import settings


def search_jobs(query: str, location: str = "", num_results: int = 10) -> list[dict]:
    """Call SerpAPI Google Jobs endpoint and return normalized job list."""
    is_remote = location.strip().lower() == "remote"
    params = {
        "engine": "google_jobs",
        "q": query,
        "num": num_results,
        "api_key": settings.SERP_API_KEY,
    }
    if is_remote:
        params["ltype"] = "1"  # Google Jobs remote filter
    elif location:
        params["location"] = location
    response = requests.get("https://serpapi.com/search", params=params)
    response.raise_for_status()
    data = response.json()

    jobs = []
    for raw in data.get("jobs_results", []):
        links = raw.get("related_links", [])
        url = links[0].get("link", "") if links else ""
        jobs.append({
            "title": raw.get("title", ""),
            "company": raw.get("company_name", ""),
            "location": raw.get("location", ""),
            "description": raw.get("description", ""),
            "url": url,
        })
    return jobs


def search_people(query: str, num_results: int = 5) -> list[dict]:
    """Call SerpAPI Google Search for HR contact discovery."""
    params = {
        "engine": "google",
        "q": query,
        "num": num_results,
        "api_key": settings.SERP_API_KEY,
    }
    response = requests.get("https://serpapi.com/search", params=params)
    response.raise_for_status()
    data = response.json()
    return data.get("organic_results", [])
