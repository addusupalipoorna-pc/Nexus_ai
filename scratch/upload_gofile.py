import os
import sys
import requests
# Disable insecure request warnings from urllib3 since we are using verify=False
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def upload_to_gofile():
    file_path = r"d:\code alpha object\dist\AlphaObject-v1.0.zip"
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        sys.exit(1)
        
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print(f"Uploading {file_path} ({size_mb:.2f} MB) to Gofile...")
    
    url = "https://upload.gofile.io/uploadfile"
    
    try:
        # Use a streaming upload or just read the bytes. Since it's ~350MB, reading it into memory is fine.
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            # verify=False is critical to bypass the SSL certificate revocation check failing in this environment.
            response = requests.post(url, files=files, verify=False, timeout=1200)
            
        if response.status_code in (200, 201):
            data = response.json()
            if data.get('status') == 'ok':
                download_page = data['data']['downloadPage']
                guest_token = data['data'].get('guestToken', 'N/A')
                file_id = data['data'].get('id', 'N/A')
                print("\n=== UPLOAD SUCCESSFUL ===")
                print(f"Download Page: {download_page}")
                print(f"File ID: {file_id}")
                print(f"Guest Token: {guest_token}")
                print("==========================\n")
            else:
                print("Server returned failure response:", response.text)
        else:
            print(f"Upload failed with status code {response.status_code}: {response.text}")
    except Exception as e:
        print("An error occurred during upload:", str(e))

if __name__ == "__main__":
    upload_to_gofile()
