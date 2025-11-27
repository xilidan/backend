import requests
from typing import Dict, Any, Optional


class RatingService:
    def __init__(self, base_url: str = "https://git.azed.kz/api/v1"):
        self.base_url = base_url

    def get_user_rating(self, email: str) -> Optional[Dict[str, Any]]:
        try:
            url = f"{self.base_url}/users/{email}/rating"
            response = requests.get(url, headers={"accept": "application/json"}, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching rating for {email}: {e}")
            return None

    def get_ratings_for_users(self, users: list) -> Dict[str, int]:
        ratings = {}
        for user in users:
            email = user.get("email")
            if not email:
                continue
            
            rating_data = self.get_user_rating(email)
            if rating_data:
                ratings[email] = rating_data.get("rating", 0)
                print(f"Fetched rating for {email}: {ratings[email]}")
            else:
                ratings[email] = 0
                print(f"No rating found for {email}, defaulting to 0")
        
        return ratings