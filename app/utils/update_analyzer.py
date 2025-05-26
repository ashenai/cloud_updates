"""
Utility functions for analyzing and processing updates.
"""
from anthropic import Anthropic
import os
import re
import spacy

# Load spaCy model - will be loaded on first use
nlp = None

def load_nlp_model():
    """
    Load the spaCy NLP model lazily.
    
    Returns:
        The loaded spaCy model
    """
    global nlp
    if nlp is None:
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            # If model is not available, download it
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], check=True)
            nlp = spacy.load("en_core_web_sm")
    return nlp

def format_explanation_text(text):
    """
    Format explanation text into paragraphs using spaCy NLP for better paragraph detection.
    
    Args:
        text (str): The raw explanation text
    
    Returns:
        str: HTML-formatted text with proper paragraph tags
    """
    if not text:
        return ""
    
    # First handle basic formatting with standard line breaks
    # This helps with simple cases and preserves existing formatting
    basic_formatted = text.replace('\r\n\r\n', '\n\n')
    basic_formatted = basic_formatted.replace('\r\n', '\n')
    
    # Initialize spaCy if not already loaded
    model = load_nlp_model()
    
    # Process the text with spaCy
    doc = model(basic_formatted)
    
    # Break into paragraphs - a sentence that starts after a newline 
    # or a sentence that follows another sentence with high likelihood of being
    # in a new paragraph (based on content and structure)
    paragraphs = []
    current_para = []
    prev_sent_end = 0
    
    for sent in doc.sents:
        sent_text = sent.text.strip()
        if not sent_text:
            continue
            
        # Check if this sentence starts a new paragraph based on various heuristics
        starts_new_para = False
        
        # 1. Explicit newline before sentence
        if '\n\n' in doc.text[prev_sent_end:sent.start_char]:
            starts_new_para = True
        
        # 2. First sentence or follows a sentence ending with a common paragraph terminator
        elif not current_para or re.search(r'(\.|:|;|\?)$', current_para[-1].strip()):
            # Check if the sentence starts with a common paragraph starter like "First", "Additionally", etc.
            starters = ["first", "second", "third", "finally", "additionally", "moreover", "furthermore", 
                       "in addition", "in conclusion", "to summarize", "overall", "this", "these",
                       "however", "nevertheless", "therefore", "thus", "consequently", "as a result"]
            
            lower_text = sent_text.lower()
            if any(lower_text.startswith(starter) for starter in starters):
                starts_new_para = True
        
        if starts_new_para and current_para:
            # Save current paragraph and start a new one
            paragraphs.append(" ".join(current_para))
            current_para = [sent_text]
        else:
            # Add to current paragraph
            current_para.append(sent_text)
            
        prev_sent_end = sent.end_char
    
    # Add the last paragraph
    if current_para:
        paragraphs.append(" ".join(current_para))
    
    # Convert to HTML with paragraphs
    html = ""
    for para in paragraphs:
        html += f"<p>{para}</p>"
    
    # Handle special case of empty result
    if not html:
        html = f"<p>{text}</p>"
        
    return html

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
    prompt = f"provide brief explanation for '{title}' ignore keywords like \"in preview\" or \"launched\" or \"retired\" or \"in development\" from title for generating description. For \"Public Preview\" and \"Generally Available\" status don't elaborate and just mention the status as a separate line. Create paragraphs"
    
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