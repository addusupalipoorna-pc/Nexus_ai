import json
import os

log_path = r"C:\Users\addus\.gemini\antigravity\brain\391fb49b-75c0-433f-801d-0a40a3bbdfd1\.system_generated\logs\transcript_full.jsonl"

def get_match(target_idx):
    with open(log_path, 'r', encoding='utf-8') as f:
        for idx, line in enumerate(f):
            if idx == target_idx:
                obj = json.loads(line)
                print(f"=== STEP {idx} ===")
                tool_calls = obj.get('tool_calls', [])
                for tc in tool_calls:
                    if 'boot_screen.py' in str(tc.get('arguments', '')):
                        args = tc.get('arguments')
                        # Print relevant fields of replace_file_content or write_to_file
                        print("File:", args.get('TargetFile'))
                        print("Instruction:", args.get('Instruction'))
                        print("TargetContent:", args.get('TargetContent'))
                        print("ReplacementContent:", args.get('ReplacementContent'))
                        print("Description:", args.get('Description'))
                break

if __name__ == "__main__":
    get_match(818)
