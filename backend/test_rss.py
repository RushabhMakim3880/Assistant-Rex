import requests
import xml.etree.ElementTree as ET

def test_rss():
    # Google News RSS for Cricket
    url = "https://news.google.com/rss/search?q=cricket+match+result&hl=en-IN&gl=IN&ceid=IN:en"
    
    try:
        response = requests.get(url, timeout=5)
        root = ET.fromstring(response.content)
        
        print("--- Cricket Headlines ---")
        count = 0
        for item in root.findall('./channel/item'):
            title = item.find('title').text
            pubDate = item.find('pubDate').text
            print(f"[{pubDate}] {title}")
            count += 1
            if count >= 3: break
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_rss()
