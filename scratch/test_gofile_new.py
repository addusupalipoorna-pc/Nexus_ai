import requests

def test_gofile_new():
    try:
        url = "https://upload.gofile.io/uploadfile"
        print(f"Uploading dummy file to {url}...")
        
        with open("test_gofile_dummy.txt", "w") as f:
            f.write("test gofile new upload api")
            
        with open("test_gofile_dummy.txt", "rb") as f:
            files = {"file": f}
            res = requests.post(url, files=files, verify=False, timeout=30)
            print("Status Code:", res.status_code)
            print("Response:", res.text)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_gofile_new()
