import requests

url = "http://127.0.0.1:8000/complaints/"
payload = {"user_details": "Test User", "description": "I just received a text that $500 was deducted from my account, but I didn't authorize it. I think I was scammed."}

print("Sending POST request to test advice generation...")
try:
    response = requests.post(url, json=payload, timeout=20)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
