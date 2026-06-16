import os

run_log_path = r"d:\code alpha object\run.log"

def check_other_errors():
    if not os.path.exists(run_log_path):
        print("run.log not found.")
        return
        
    print("Checking for exceptions in other files...")
    tbs = []
    current_tb = []
    in_tb = False
    
    with open(run_log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if "traceback (most recent call last)" in line.lower():
                if current_tb:
                    if not any("boot_screen.py" in l for l in current_tb) and len(current_tb) > 1:
                        tbs.append(current_tb)
                current_tb = [line.strip()]
                in_tb = True
            elif in_tb:
                if line.startswith("  ") or ":" in line:
                    current_tb.append(line.strip())
                else:
                    in_tb = False
                    if current_tb and not any("boot_screen.py" in l for l in current_tb) and len(current_tb) > 1:
                        tbs.append(current_tb)
                    current_tb = []
        if current_tb and not any("boot_screen.py" in l for l in current_tb) and len(current_tb) > 1:
            tbs.append(current_tb)
            
    print(f"Found {len(tbs)} tracebacks from other files.")
    seen = set()
    for tb in reversed(tbs):
        tb_str = "\n".join(tb)
        if tb_str not in seen:
            seen.add(tb_str)
            print("\n" + "="*50)
            print(tb_str)
            print("="*50)

if __name__ == "__main__":
    check_other_errors()
