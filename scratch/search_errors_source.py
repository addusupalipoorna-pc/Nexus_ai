import os

run_log_path = r"d:\code alpha object\run.log"

def analyze_tracebacks():
    if not os.path.exists(run_log_path):
        print("run.log not found.")
        return
        
    print(f"Searching tracebacks in run.log...")
    tracebacks = []
    current_tb = []
    in_tb = False
    
    with open(run_log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if "traceback (most recent call last)" in line.lower():
                if current_tb:
                    tracebacks.append(current_tb)
                current_tb = [line.strip()]
                in_tb = True
            elif in_tb:
                if line.startswith("  ") or ":" in line:
                    current_tb.append(line.strip())
                else:
                    in_tb = False
                    if current_tb:
                        tracebacks.append(current_tb)
                        current_tb = []
        if current_tb:
            tracebacks.append(current_tb)
            
    print(f"Total tracebacks found: {len(tracebacks)}")
    # Print the unique tracebacks (last 10 unique ones)
    unique_tbs = []
    seen = set()
    for tb in reversed(tracebacks):
        tb_str = "\n".join(tb)
        # check last line of traceback for uniqueness
        if tb:
            err_msg = tb[-1]
            if err_msg not in seen:
                seen.add(err_msg)
                unique_tbs.append(tb)
                if len(unique_tbs) >= 5:
                    break
                    
    for i, tb in enumerate(unique_tbs, 1):
        print(f"\n--- Traceback {i} ---")
        for line in tb:
            print(line)

if __name__ == "__main__":
    analyze_tracebacks()
