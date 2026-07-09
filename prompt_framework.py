import os
import json
import time
from openai import OpenAI

# 1. Setup paths and directories
DATASET_PATH = "functions.json"  # استفاده از دیتاست ۱۰۰ تایی اصلی
OUTPUT_DIR = "generated_tests"
STRATEGIES = ["baseline", "structured", "cot", "multistep"]

for strategy in STRATEGIES:
    os.makedirs(os.path.join(OUTPUT_DIR, strategy), exist_ok=True)

# 2. Authenticate with OpenAI API via GitHub Secrets
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("[ERROR] OPENAI_API_KEY not found in environment variables!")
    exit()

# اتصال به سرور واسط ایرانی (GapGPT) برای دور زدن تحریم‌ها
client = OpenAI(
    api_key=api_key,
    base_url="https://api.gapgpt.app/v1"
) 

# 3. Define Prompts
def get_prompt(strategy, code, entry_point):
    system_instruction = "Respond ONLY with the executable Python code inside a ```python ``` block. Do not include any introductory or concluding text."
    
    if strategy == "baseline":
        return f'{system_instruction}\n\nGenerate Python unit tests using the unittest framework for this function:\n\n{code}'
    elif strategy == "structured":
        return f'{system_instruction}\n\nGenerate Python unit tests using the unittest framework.\nFunction Name: {entry_point}\nCode:\n{code}'
    elif strategy == "cot":
        return f'{system_instruction}\n\nAnalyze the following Python function step-by-step, identify edge cases, and then generate comprehensive unit tests using the unittest framework:\n\n{code}'
    elif strategy == "multistep":
        return f'{system_instruction}\n\nStep 1: List all important test scenarios and edge cases for this function.\nStep 2: Generate the executable Python unit test code based on those scenarios using the unittest framework.\n\nFunction:\n{code}'

# 4. Load dataset
if not os.path.exists(DATASET_PATH):
    print(f"[ERROR] {DATASET_PATH} not found!")
    exit()

with open(DATASET_PATH, "r", encoding="utf-8") as f:
    functions = json.load(f)

print(f"[START] Starting fast generation for {len(functions)} functions via ChatGPT (GapGPT Proxy)...")

# 5. Process loop
for index, func in enumerate(functions):
    func_name = func["entry_point"]
    func_code = func["code"]
    
    print(f"\n[{index + 1}/{len(functions)}] Processing Function: {func_name}")
    
    for strategy in STRATEGIES:
        file_path = os.path.join(OUTPUT_DIR, strategy, f"test_{func_name}.py")
        if os.path.exists(file_path): continue
            
        prompt = get_prompt(strategy, func_code, func_name)
        
        try:
            # استفاده از مدل فوق‌سریع و ارزان gpt-4o-mini
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            
            raw_content = response.choices[0].message.content
            
            # استخراج کد تمیز
            if "```python" in raw_content:
                generated_code = raw_content.split("```python")[1].split("```")[0].strip()
            elif "```" in raw_content:
                generated_code = raw_content.split("```")[1].split("```")[0].strip()
            else:
                generated_code = raw_content.strip()
            
            with open(file_path, "w", encoding="utf-8") as test_file:
                test_file.write(generated_code)
                
        except Exception as e:
            print(f"    [ERROR] Failed for {func_name}: {e}")
            
        time.sleep(0.1)

print("\n[SUCCESS] All 400 tests have been generated lightning fast!")
