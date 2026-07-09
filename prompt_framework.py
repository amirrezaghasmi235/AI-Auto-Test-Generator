import os
import json
import time
from ollama import Client

# 1. Force Python to bypass ANY system/VPN proxies for localhost connection
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["no_proxy"] = "localhost,127.0.0.1,::1"

# 2. Setup paths and directories
DATASET_PATH = "functions_mini.json"
OUTPUT_DIR = "generated_tests"
STRATEGIES = ["baseline", "structured", "cot", "multistep"]

for strategy in STRATEGIES:
    os.makedirs(os.path.join(OUTPUT_DIR, strategy), exist_ok=True)

# اتصال مستقیم به سروری که در CMD اول روشن نگه داشته‌اید
ollama_client = Client(host="http://127.0.0.1:11434", trust_env=False)

# 3. Define the 4 Prompt Engineering Strategies
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

print("[START] Starting test generation. Connecting to manually started Ollama...")

# 5. Process loop
for index, func in enumerate(functions):
    func_name = func["entry_point"]
    func_code = func["code"]
    
    print(f"\n[{index + 1}/{len(functions)}] Processing Function: {func_name}")
    
    for strategy in STRATEGIES:
        file_path = os.path.join(OUTPUT_DIR, strategy, f"test_{func_name}.py")
        
        if os.path.exists(file_path):
            continue
            
        print(f"  -> Generating test using [{strategy}] strategy...")
        prompt = get_prompt(strategy, func_code, func_name)
        
        try:
            response = ollama_client.chat(
                model="qwen2.5-coder:0.5b",
                messages=[{"role": "user", "content": prompt}]
            )
            
            raw_content = response.message.content
            
            # استخراج کد تمیز از مارک‌داون
            if "```python" in raw_content:
                generated_code = raw_content.split("```python")[1].split("```")[0].strip()
            elif "```" in raw_content:
                generated_code = raw_content.split("```")[1].split("```")[0].strip()
            else:
                generated_code = raw_content.strip()
            
            with open(file_path, "w", encoding="utf-8") as test_file:
                test_file.write(generated_code)
                
        except Exception as e:
            print(f"    [ERROR] Failed for {func_name} with {strategy}: {e}")
            
        time.sleep(0.1)

print("\n[SUCCESS] All tests have been generated successfully!")