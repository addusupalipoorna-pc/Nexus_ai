import json
import os

log_path = r"C:\Users\addus\.gemini\antigravity\brain\391fb49b-75c0-433f-801d-0a40a3bbdfd1\.system_generated\logs\transcript_full.jsonl"

def search():
    with open(log_path, 'r', encoding='utf-8') as f:
        for idx, line in enumerate(f):
            try:
                obj = json.loads(line)
                tool_calls = obj.get('tool_calls', [])
                for tc in tool_calls:
                    args = tc.get('arguments', {})
                    if 'boot_screen.py' in str(args.get('TargetFile', '')):
                        rep = args.get('ReplacementContent', '')
                        if 'scene_idx' in rep:
                            print(f"Match found at line {idx} in tool call:")
                            print("TargetContent:")
                            print(args.get('TargetContent'))
                            print("ReplacementContent:")
                            print(rep)
                            print("=" * 60)
            except Exception as e:
                pass

if __name__ == "__main__":
    search()
