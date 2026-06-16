import requests

def test_gofile():
    try:
        url = "https://api.gofile.io/getServer"
        print(f"Requesting {url}...")
        res = requests.get(url, verify=False, timeout=10)
        print("Status Code:", res.status_code)
        print("Response Text:", res.text[:500])
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_gofile()
