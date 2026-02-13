
import os
import sys

print(f"Python: {sys.version}")

try:
    import httpx
    print(f"httpx version: {httpx.__version__}")
except ImportError:
    print("httpx not installed")

try:
    import groq
    print(f"groq version: {groq.__version__}")
except ImportError:
    print("groq not installed")

from dotenv import load_dotenv
load_dotenv()

key = os.getenv("GROQ_API_KEY")
print(f"API Key present: {bool(key)}")

try:
    from groq import Groq
    print("Attempting to initialize Groq client...")
    client = Groq(api_key=key)
    print("Success!")
except Exception as e:
    print(f"Failed: {type(e).__name__}: {e}")
