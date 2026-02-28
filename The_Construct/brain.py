import os
from llama_cpp import Llama
from huggingface_hub import hf_hub_download

# CONFIGURATION
REPO_ID = "Qwen/Qwen2.5-0.5B-Instruct-GGUF"
FILENAME = "qwen2.5-0.5b-instruct-q4_k_m.gguf" # The specific "quantized" file
MODEL_DIR = "./models"
MODEL_PATH = os.path.join(MODEL_DIR, FILENAME)

def load_model():
    """
    Downloads the model if missing, then loads it into RAM.
    """
    if not os.path.exists(MODEL_PATH):
        print(f"Downloading {FILENAME}... this happens only once.")
        os.makedirs(MODEL_DIR, exist_ok=True)
        hf_hub_download(repo_id=REPO_ID, filename=FILENAME, local_dir=MODEL_DIR)
        print("Download complete.")

    # Initialize the model
    # n_ctx=512 is small to keep it fast. 
    # verbose=False stops it from spamming your terminal.
    return Llama(model_path=MODEL_PATH, n_ctx=512, verbose=False)

# Global instance (so we don't reload it every time)
llm = load_model()

def get_coaching_tip(joint_name, issue):
    """
    Generates a fast, aggressive coaching tip.
    """
    prompt = f"System: You are a tough gym coach. Keep it under 10 words.\nUser: My {joint_name} is {issue}. Fix it.\nCoach:"
    
    output = llm(
        prompt, 
        max_tokens=20, # Keep it short = Faster
        stop=["User:", "\n"], 
        echo=False
    )
    
    return output['choices'][0]['text'].strip()

# --- TEST BLOCK ---
if __name__ == "__main__":
    start = os.times()[4]
    print(get_coaching_tip("knees", "caving in"))
    print(f"Response time: {os.times()[4] - start:.4f}s")