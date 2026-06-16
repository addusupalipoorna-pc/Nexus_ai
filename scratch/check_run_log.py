import os

run_log_path = r"d:\code alpha object\run.log"

def analyze_log():
    if not os.path.exists(run_log_path):
        print("run.log not found.")
        return
        
    print(f"Reading run.log ({os.path.getsize(run_log_path)} bytes)...")
    errors = []
    with open(run_log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            if "traceback" in line.lower() or "error" in line.lower() or "exception" in line.lower():
                errors.append((line_num, line.strip()))
                
    print(f"Found {len(errors)} potential error/exception lines.")
    # Show the last 20 matching lines to see recent issues
    for num, err in errors[-20:]:
        print(f"Line {num}: {err}")

if __name__ == "__main__":
    analyze_log()
