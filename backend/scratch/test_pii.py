import requests

url = "http://127.0.0.1:8000/api/pii/detect"
payload = {"text": "My name is Samuel Mwangi and I live in Nairobi, Kenya."}
headers = {"Content-Type": "application/json"}

try:
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status: {response.status_code}")
    print(response.json())
except Exception as e:
    print(f"Error: {e}")
