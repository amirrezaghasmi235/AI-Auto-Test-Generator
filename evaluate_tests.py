import os
import json
import subprocess

# 1. Configuration
DATASET_PATH = "functions_mini.json"
TESTS_DIR = "generated_tests"
STRATEGIES = ["baseline", "structured", "cot", "multistep"]
TEMP_RUN_FILE = "temp_run_target.py"

# 2. Initialize results storage
results = {strategy: {"total": 0, "syntax_correct": 0, "total_coverage": 0.0} for strategy in STRATEGIES}

if not os.path.exists(DATASET_PATH):
    print(f"[ERROR] {DATASET_PATH} not found!")
    exit()

with open(DATASET_PATH, "r", encoding="utf-8") as f:
    functions = json.load(f)

print("[START] Evaluating generated tests... (Printing progress live)")

# 3. Evaluation Loop
for index, func in enumerate(functions):
    func_name = func["entry_point"]
    func_code = func["code"]
    
    print(f"\n[{index + 1}/{len(functions)}] Evaluating Function: {func_name}")
    
    for strategy in STRATEGIES:
        test_file_path = os.path.join(TESTS_DIR, strategy, f"test_{func_name}.py")
        
        if not os.path.exists(test_file_path):
            continue
            
        results[strategy]["total"] += 1
        
        with open(test_file_path, "r", encoding="utf-8") as tf:
            test_code = tf.read()
            
        combined_code = f"""
{func_code}

{test_code}

if __name__ == '__main__':
    import unittest
    import sys
    try:
        suite = unittest.defaultTestLoader.loadTestsFromName('__main__')
        result = unittest.TextTestRunner(verbosity=0).run(suite)
        sys.exit(0 if result.wasSuccessful() else 1)
    except Exception:
        sys.exit(1)
"""
        
        with open(TEMP_RUN_FILE, "w", encoding="utf-8") as temp_file:
            temp_file.write(combined_code)
            
        # پاک کردن فایل دیتابیس قبلی برای جلوگیری از تداخل
        if os.path.exists(".coverage"): os.remove(".coverage")
            
        try:
            # ۱. اجرای تست با ابزار coverage
            run_res = subprocess.run(
                ["coverage", "run", TEMP_RUN_FILE], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL, 
                timeout=3
            )
            
            # ۲. گرفتن درصد به صورت متن مستقیم از خود خط فرمان (کامپایلر مستقل از نسخه جیسون)
            report_res = subprocess.run(
                ["coverage", "report", "--format=total"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                timeout=3,
                text=True
            )
            
            # اگر اجرای تست با موفقیت بوده و خروجی عدد داریم
            if report_res.stdout.strip().isdigit():
                cov_percent = float(report_res.stdout.strip())
                results[strategy]["syntax_correct"] += 1
                results[strategy]["total_coverage"] += cov_percent
                print(f"   -> {strategy.upper()}: Success (Coverage: {cov_percent:.1f}%)")
            else:
                print(f"   -> {strategy.upper()}: Failed (Syntax or Runtime Error)")
                
        except subprocess.TimeoutExpired:
            print(f"   -> {strategy.upper()}: Timeout (Test got stuck)")
        except Exception as e:
            print(f"   -> {strategy.upper()}: Error ({e})")

# 4. Clean up temporary files
for f_path in [TEMP_RUN_FILE, ".coverage"]:
    if os.path.exists(f_path): os.remove(f_path)

# 5. Print and Save the Final Report
print("\n================ FINAL EVALUATION REPORT ================")
report_data = {}

for strategy in STRATEGIES:
    total = results[strategy]["total"]
    syntax_correct = results[strategy]["syntax_correct"]
    total_cov = results[strategy]["total_coverage"]
    
    syntax_rate = (syntax_correct / total * 100) if total > 0 else 0
    avg_coverage = (total_cov / syntax_correct) if syntax_correct > 0 else 0
    
    print(f"Strategy: [{strategy.upper()}]")
    print(f"  - Total Tests Evaluated: {total}")
    print(f"  - Syntax Correctness Rate: {syntax_rate:.2f}% ({syntax_correct}/{total})")
    print(f"  - Average Code Coverage: {avg_coverage:.2f}%")
    print("-" * 50)
    
    report_data[strategy] = {
        "syntax_correctness_rate": f"{syntax_rate:.2f}%",
        "average_coverage": f"{avg_coverage:.2f}%"
    }

with open("evaluation_summary.json", "w", encoding="utf-8") as summary_file:
    json.dump(report_data, summary_file, indent=4)

print("[SUCCESS] Evaluation complete! Check 'evaluation_summary.json'.")