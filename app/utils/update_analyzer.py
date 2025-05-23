"""
Utility functions for analyzing and processing updates.
"""
from anthropic import Anthropic
import os

def generate_explanation(title: str) -> str:
    """
    Generate an explanation for a cloud service update using Claude.
    
    Args:
        title (str): The title of the update to explain
        
    Returns:
        str: The generated explanation
        
    Raises:
        Exception: If there's an error generating the explanation
    """    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("Warning: ANTHROPIC_API_KEY not found in environment variables")
        raise Exception('ANTHROPIC_API_KEY environment variable not set')
        
    client = Anthropic(api_key=api_key)
    prompt = f"provide brief explanation for '{title}'"
    
    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    explanation = ""
    for content in message.content:
        if hasattr(content, 'text'):
            explanation += content.text
        elif isinstance(content, str):
            explanation += content
            
    return explanation.strip()