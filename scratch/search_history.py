import json
import os

log_path = r"C:\Users\addus\.gemini\antigravity\brain\391fb49b-75c0-433f-801d-0a40a3bbdfd1\.system_generated\logs\transcript_full.jsonl"

def search():
    if not os.path.exists(log_path):
        # try the other one if not exists
        print("Not found path:", log_path)
        return
        
    print("Searching log for boot_screen.py...")
    with open(log_path, 'r', encoding='utf-8') as f:
        for idx, line in enumerate(f):
            try:
                obj = json.loads(line)
                content = str(obj)
                if "boot_screen.py" in content and ("replace_file_content" in content or "write_to_file" in content):
                    print(f"Match found at line {idx} (type: {obj.get('type')})")
                    # Check tool calls
                    tool_calls = obj.get('tool_calls', [])
                    for tc in tool_calls:
                        if 'boot_screen.py' in str(tc.get('arguments', '')):
                            print("Arguments:")
                            print(json.dumps(tc.get('arguments'), indent=2))
                            print("-" * 50)
            except Exception as e:
                pass

if __name__ == "__main__":
    search()
