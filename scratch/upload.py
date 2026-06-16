import os
import sys
import requests

def upload_file():
    file_path = r"d:\code alpha object\dist\AlphaObject-v1.0.zip"
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        sys.exit(1)
        
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print(f"Uploading {file_path} ({size_mb:.2f} MB) to pixeldrain.com...")
    
    url = "https://pixeldrain.com/api/file/"
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            response = requests.post(url, files=files, timeout=600)
            
        if response.status_code in (200, 201):
            data = response.json()
            if data.get('success'):
                file_id = data.get('id')
                download_url = f"https://pixeldrain.com/u/{file_id}"
                print("\n=== UPLOAD SUCCESSFUL ===")
                print(f"File ID: {file_id}")
                print(f"Permanent Download URL: {download_url}")
                print("==========================\n")
            else:
                print("Server returned failure response:", response.text)
        else:
            print(f"Upload failed with status code {response.status_code}: {response.text}")
    except Exception as e:
        print("An error occurred during upload:", str(e))

if __name__ == "__main__":
    upload_file()
