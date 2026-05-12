import requests
from bs4 import BeautifulSoup

url = "https://xn--vf4b15j1pa468argc.com/"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
response = requests.get(url, headers=headers)
response.encoding = 'utf-8'

soup = BeautifulSoup(response.text, 'html.parser')
# Find elements that look like product containers
# Just print the first 2000 chars of body if we don't know the structure
print(soup.body.text[:2000] if soup.body else "No body")

# Let's also print some common tags to understand structure
for a in soup.find_all('a')[:10]:
    print(f"Link: {a.get('href')}, Text: {a.text.strip()}")
    
for img in soup.find_all('img')[:10]:
    print(f"Img: {img.get('src')}")
