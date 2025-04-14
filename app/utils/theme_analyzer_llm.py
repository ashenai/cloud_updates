import os
from typing import List, Dict
from datetime import datetime
from app.models import Update

class LLMThemeAnalyzer:
    def __init__(self):
        """Initialize the LLM theme analyzer."""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
            
        # Import dependencies
        from anthropic import Anthropic
        import httpx
        
        # Create a clean httpx client without proxies
        http_client = httpx.Client(
            base_url="https://api.anthropic.com",
            headers={"Accept": "application/json"},
            follow_redirects=True,
            timeout=60.0
        )
        
        # Initialize Anthropic client with custom http client
        self.client = Anthropic(
            api_key=api_key,
            http_client=http_client
        )
        
        # Set constants
        self.HUMAN_PROMPT = "Human: "
        self.ASSISTANT_PROMPT = "Assistant: "

    def generate_themes(self, updates: List[Update], min_updates: int = 2) -> List[Dict]:
        """Generate themes from updates using Claude."""
        if not updates:
            return []

        # Group updates by provider
        updates_by_provider = {}
        for update in updates:
            if update.provider not in updates_by_provider:
                updates_by_provider[update.provider] = []
            updates_by_provider[update.provider].append(update)

        all_themes = []
        for provider, provider_updates in updates_by_provider.items():
            # Prepare updates text for the prompt
            updates_text = "\n\n".join([
                f"Title: {update.title}\nDescription: {update.description or ''}"
                for update in provider_updates[:50]  # Limit to 50 updates to stay within context window
            ])

            # Create the prompt with correct format
            formatted_prompt = f"""You are a cloud technology analyst. Analyze these {provider.upper()} cloud updates and identify 3-5 major themes or trends. For each theme:
1. Give it a concise name
2. Write a brief description explaining what the theme represents
3. Note which specific services or features are involved

Updates to analyze:
{updates_text}

Format your response as a JSON array of themes, where each theme has these exact keys:
- name: The theme name (string)
- description: A 1-2 sentence description (string)
- services: List of relevant services (array of strings)
- update_count: Number of updates that fit this theme (integer)

Return ONLY the JSON array, with no other text or explanation. The response should be valid JSON that can be parsed. Example format:
[{{"name": "Example Theme", "description": "Brief description here", "services": ["Service 1", "Service 2"], "update_count": 3}}]"""

            try:
                # Call Claude API
                try:
                    completion = self.client.messages.create(
                        model="claude-3-5-sonnet-20240620",
                        messages=[{
                            "role": "user",
                            "content": formatted_prompt
                        }],
                        max_tokens=4000
                    )
                    
                    if not completion or not completion.content:
                        print("Error: Empty completion response")
                        raise ValueError("Empty completion response")
                        
                    print(f"Completion response: {completion}")  # Debug print
                    print(f"Content: {completion.content}")  # Debug print
                    
                    if not completion.content[0] or not completion.content[0].text:
                        print("Error: No text in completion content")
                        raise ValueError("No text in completion content")
                    
                    response_text = completion.content[0].text
                    print(f"Raw API response text: {response_text}")  # Debug print
                    
                    # Extract the JSON array from the response using regex
                    import json
                    import re
                    
                    # First try direct JSON parsing
                    try:
                        themes_data = json.loads(response_text)
                        if not isinstance(themes_data, list):
                            print(f"Error: Response is not a list: {themes_data}")
                            raise ValueError("Response is not a list")
                    except json.JSONDecodeError:
                        # If direct parsing fails, try to extract JSON array using regex
                        print("Direct JSON parsing failed, trying regex extraction")
                        json_match = re.search(r'\[\s*\{.*?\}\s*\]', response_text, re.DOTALL)
                        if not json_match:
                            print(f"Error: Could not find JSON array in response: {response_text}")
                            raise ValueError("No JSON array found in response")
                        
                        json_str = json_match.group(0)
                        themes_data = json.loads(json_str)
                    
                    if not themes_data:
                        print("Error: Empty themes data after parsing")
                        raise ValueError("No themes found in response")
                    
                    print(f"Parsed themes data: {themes_data}")  # Debug print
                    
                    for theme in themes_data:
                        theme['provider'] = provider
                        theme['score'] = self._calculate_theme_score(theme, provider_updates)
                        all_themes.append(theme)
                        
                except Exception as api_error:
                    print(f"Error in API call or response processing: {str(api_error)}")
                    raise
            except Exception as e:
                print(f"Error processing themes for {provider}: {str(e)}")
                continue

        # Sort themes by score
        return sorted(all_themes, key=lambda x: x['score'], reverse=True)

    def _calculate_theme_score(self, theme: Dict, updates: List[Update]) -> float:
        """Calculate a relevance score for the theme."""
        update_count = theme.get('update_count', 0)
        if not update_count or not updates:
            return 0.0

        # Calculate score based on:
        # 1. Proportion of updates covered (40%)
        # 2. Number of services involved (30%)
        # 3. Recency of updates (30%)
        
        coverage_score = min(update_count / len(updates), 1.0) * 0.4
        
        services_score = min(len(theme.get('services', [])) / 10, 1.0) * 0.3
        
        # Calculate recency score
        now = datetime.utcnow()
        max_age = max((now - update.published_date).days for update in updates)
        recency_score = (1 / (1 + max_age/30)) * 0.3  # 30-day decay
        
        return coverage_score + services_score + recency_score
