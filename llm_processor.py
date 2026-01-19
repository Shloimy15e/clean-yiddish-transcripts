"""
LLM-based document processor for cleaning Yiddish transcripts.
Supports multiple LLM providers: OpenAI, Anthropic, and Google.
"""
import re
from typing import Optional


# Default prompt template for cleaning Yiddish transcripts
DEFAULT_PROMPT = """You are cleaning a Yiddish transcript document. Your task is to extract only the actual spoken words and remove everything else.

Remove all non-speech content such as: titles, headings, section markers, editorial notes, timestamps, page numbers, speaker labels, annotations, and any other meta-information.

Keep only the actual spoken words. Maintain the original language and paragraph structure.

Return ONLY the cleaned text with no explanation or commentary.

---

{document_text}"""


def get_default_prompt():
    """Return the default prompt template."""
    return DEFAULT_PROMPT


def process_with_llm(
    document_text: str,
    prompt_template: str,
    api_key: str,
    provider: str = "openai",
    model: Optional[str] = None
) -> dict:
    """
    Process a document using an LLM.
    
    Args:
        document_text: The text content of the document to process
        prompt_template: The prompt template with {document_text} placeholder
        api_key: The API key for the LLM provider (not required for Ollama)
        provider: One of 'openai', 'anthropic', 'google', 'groq', or 'ollama'
        model: Optional specific model to use
        
    Returns:
        dict with 'success', 'cleaned_text', and optionally 'error'
    """
    # Ollama doesn't require an API key
    if not api_key and provider != "ollama":
        return {"success": False, "error": "API key is required"}
    
    if not document_text:
        return {"success": False, "error": "Document text is empty"}
    
    # Build the full prompt
    full_prompt = prompt_template.replace("{document_text}", document_text)
    
    try:
        if provider == "openai":
            return _process_with_openai(full_prompt, api_key, model)
        elif provider == "anthropic":
            return _process_with_anthropic(full_prompt, api_key, model)
        elif provider == "google":
            return _process_with_google(full_prompt, api_key, model)
        elif provider == "groq":
            return _process_with_groq(full_prompt, api_key, model)
        elif provider == "openrouter":
            return _process_with_openrouter(full_prompt, api_key, model)
        elif provider == "ollama":
            return _process_with_ollama(full_prompt, model)
        else:
            return {"success": False, "error": f"Unknown provider: {provider}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _process_with_openai(prompt: str, api_key: str, model: Optional[str] = None) -> dict:
    """Process using OpenAI API."""
    try:
        import openai
    except ImportError:
        return {"success": False, "error": "OpenAI package not installed. Run: pip install openai"}
    
    model = model or "gpt-4o"
    
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature for consistent output
            max_tokens=16000
        )
        
        cleaned_text = response.choices[0].message.content.strip()
        return {
            "success": True,
            "cleaned_text": cleaned_text,
            "model_used": model,
            "provider": "openai"
        }
    except openai.AuthenticationError:
        return {"success": False, "error": "Invalid OpenAI API key"}
    except openai.RateLimitError:
        return {"success": False, "error": "OpenAI rate limit exceeded. Please try again later."}
    except Exception as e:
        return {"success": False, "error": f"OpenAI error: {str(e)}"}


def _process_with_anthropic(prompt: str, api_key: str, model: Optional[str] = None) -> dict:
    """Process using Anthropic API."""
    try:
        import anthropic
    except ImportError:
        return {"success": False, "error": "Anthropic package not installed. Run: pip install anthropic"}
    
    model = model or "claude-sonnet-4-20250514"
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=16000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        cleaned_text = response.content[0].text.strip()
        return {
            "success": True,
            "cleaned_text": cleaned_text,
            "model_used": model,
            "provider": "anthropic"
        }
    except anthropic.AuthenticationError:
        return {"success": False, "error": "Invalid Anthropic API key"}
    except anthropic.RateLimitError:
        return {"success": False, "error": "Anthropic rate limit exceeded. Please try again later."}
    except Exception as e:
        return {"success": False, "error": f"Anthropic error: {str(e)}"}


def _process_with_google(prompt: str, api_key: str, model: Optional[str] = None) -> dict:
    """Process using Google Generative AI API."""
    try:
        import google.generativeai as genai
    except ImportError:
        return {"success": False, "error": "Google Generative AI package not installed. Run: pip install google-generativeai"}
    
    model = model or "gemini-1.5-pro"
    
    try:
        genai.configure(api_key=api_key)
        gen_model = genai.GenerativeModel(model)
        response = gen_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=16000
            )
        )
        
        cleaned_text = response.text.strip()
        return {
            "success": True,
            "cleaned_text": cleaned_text,
            "model_used": model,
            "provider": "google"
        }
    except Exception as e:
        error_str = str(e).lower()
        if "api key" in error_str or "invalid" in error_str or "401" in error_str:
            return {"success": False, "error": "Invalid Google API key"}
        return {"success": False, "error": f"Google AI error: {str(e)}"}


def _process_with_groq(prompt: str, api_key: str, model: Optional[str] = None) -> dict:
    """Process using Groq API (free tier available)."""
    try:
        import requests
    except ImportError:
        return {"success": False, "error": "Requests package not installed. Run: pip install requests"}
    
    model = model or "llama-3.3-70b-versatile"
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 16000
            },
            timeout=120
        )
        
        if response.status_code == 401:
            return {"success": False, "error": "Invalid Groq API key"}
        elif response.status_code == 429:
            return {"success": False, "error": "Groq rate limit exceeded. Please try again later."}
        elif response.status_code != 200:
            return {"success": False, "error": f"Groq API error: {response.text}"}
        
        result = response.json()
        cleaned_text = result["choices"][0]["message"]["content"].strip()
        return {
            "success": True,
            "cleaned_text": cleaned_text,
            "model_used": model,
            "provider": "groq"
        }
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Groq API request timed out"}
    except Exception as e:
        return {"success": False, "error": f"Groq error: {str(e)}"}


def _process_with_openrouter(prompt: str, api_key: str, model: Optional[str] = None) -> dict:
    """Process using OpenRouter API (access to all major models via single API)."""
    try:
        import requests
    except ImportError:
        return {"success": False, "error": "Requests package not installed. Run: pip install requests"}
    
    model = model or "openai/gpt-4o"
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/Shloimy15e/clean-yiddish-transcripts",
                "X-Title": "Yiddish Transcript Cleaner"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 16000
            },
            timeout=120
        )
        
        if response.status_code == 401:
            return {"success": False, "error": "Invalid OpenRouter API key"}
        elif response.status_code == 402:
            return {"success": False, "error": "OpenRouter: Insufficient credits. Please add credits at openrouter.ai"}
        elif response.status_code == 429:
            return {"success": False, "error": "OpenRouter rate limit exceeded. Please try again later."}
        elif response.status_code != 200:
            return {"success": False, "error": f"OpenRouter API error: {response.text}"}
        
        result = response.json()
        cleaned_text = result["choices"][0]["message"]["content"].strip()
        return {
            "success": True,
            "cleaned_text": cleaned_text,
            "model_used": model,
            "provider": "openrouter"
        }
    except requests.exceptions.Timeout:
        return {"success": False, "error": "OpenRouter API request timed out"}
    except Exception as e:
        return {"success": False, "error": f"OpenRouter error: {str(e)}"}


def _process_with_ollama(prompt: str, model: Optional[str] = None) -> dict:
    """Process using local Ollama instance (no API key required)."""
    try:
        import requests
    except ImportError:
        return {"success": False, "error": "Requests package not installed. Run: pip install requests"}
    
    model = model or "llama3.2:latest"
    ollama_url = "http://localhost:11434/api/generate"
    
    try:
        # First check if Ollama is running
        try:
            health_check = requests.get("http://localhost:11434/api/tags", timeout=5)
            if health_check.status_code != 200:
                return {"success": False, "error": "Ollama is not responding. Make sure Ollama is running (run 'ollama serve')."}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Cannot connect to Ollama. Make sure Ollama is installed and running (run 'ollama serve')."}
        
        response = requests.post(
            ollama_url,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 16000
                }
            },
            timeout=300  # Local models may be slower
        )
        
        if response.status_code == 404:
            return {"success": False, "error": f"Model '{model}' not found. Run 'ollama pull {model}' to download it."}
        elif response.status_code != 200:
            return {"success": False, "error": f"Ollama error: {response.text}"}
        
        result = response.json()
        cleaned_text = result.get("response", "").strip()
        return {
            "success": True,
            "cleaned_text": cleaned_text,
            "model_used": model,
            "provider": "ollama"
        }
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Ollama request timed out. The model might be too slow or the document too large."}
    except Exception as e:
        return {"success": False, "error": f"Ollama error: {str(e)}"}


def get_available_providers():
    """Return information about available LLM providers."""
    return {
        "openai": {
            "name": "OpenAI",
            "models": [
                "gpt-5.2", "gpt-5.2-mini",
                "gpt-5.1", "gpt-5.1-mini",
                "gpt-5", "gpt-5-mini",
                "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano",
                "o3", "o3-mini",
                "o1", "o1-mini", "o1-pro",
                "gpt-4o", "gpt-4o-mini"
            ],
            "default_model": "gpt-5.2-mini",
            "description": "OpenAI's GPT and o-series models",
            "requires_key": True
        },
        "anthropic": {
            "name": "Anthropic",
            "models": [
                "claude-4.5-sonnet",
                "claude-4.5-haiku",
                "claude-opus-4-20250514",
                "claude-sonnet-4-20250514",
                "claude-3-7-sonnet-20250219",
                "claude-3-5-sonnet-20241022",
                "claude-3-5-haiku-20241022"
            ],
            "default_model": "claude-4.5-sonnet",
            "description": "Anthropic's Claude models",
            "requires_key": True
        },
        "google": {
            "name": "Google",
            "models": [
                "gemini-3-pro",
                "gemini-3-flash",
                "gemini-2.5-pro",
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-2.0-flash-lite",
                "gemini-1.5-pro",
                "gemini-1.5-flash"
            ],
            "default_model": "gemini-3-flash",
            "description": "Google's Gemini models",
            "requires_key": True
        },
        "groq": {
            "name": "Groq (Free)",
            "models": [
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "llama-3.2-90b-vision",
                "mixtral-8x7b-32768",
                "gemma2-9b-it"
            ],
            "default_model": "llama-3.3-70b-versatile",
            "description": "Groq - Fast inference, free tier available",
            "requires_key": True,
            "free_tier": True
        },
        "openrouter": {
            "name": "OpenRouter",
            "models": [
                "openai/gpt-5.2",
                "openai/gpt-4o",
                "openai/o3-mini",
                "anthropic/claude-4.5-sonnet",
                "anthropic/claude-sonnet-4",
                "google/gemini-2.5-pro",
                "google/gemini-2.0-flash",
                "meta-llama/llama-3.3-70b-instruct",
                "mistralai/mistral-large",
                "deepseek/deepseek-r1",
                "qwen/qwen-2.5-72b-instruct",
                "perplexity/sonar-pro"
            ],
            "default_model": "openai/gpt-4o",
            "description": "OpenRouter - Access all models via single API",
            "requires_key": True
        },
        "ollama": {
            "name": "Ollama (Local)",
            "models": [
                "llama3.3:70b",
                "llama3.2:latest",
                "mistral:latest",
                "mixtral:latest",
                "qwen2.5:72b",
                "deepseek-r1:70b",
                "phi4:latest"
            ],
            "default_model": "llama3.2:latest",
            "description": "Local models via Ollama - No API key needed",
            "requires_key": False
        }
    }
