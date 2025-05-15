# backend/ai_core/llm_service.py
from llama_cpp import Llama
from pathlib import Path
import os
import logging

# Configure basic logging for the service
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - LLM_SERVICE: %(message)s')
llm_service_logger = logging.getLogger(__name__)  # Create a logger specific to this module

# --- Configuration ---
MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_BASENAME = "gemma-3-4b-it-q4_0.gguf"
MODEL_PATH_STR = str(MODEL_DIR / MODEL_BASENAME)

N_CTX_VAL = 8192
N_GPU_LAYERS_VAL = 0
SEED_VAL = 42

# --- Global LLM instance ---
llm_instance = None

def get_llm_instance():
    global llm_instance
    if llm_instance is None:
        if not os.path.exists(MODEL_PATH_STR):
            llm_service_logger.error(f"Model file not found: {MODEL_PATH_STR}")
            raise FileNotFoundError(f"Model file not found: {MODEL_PATH_STR}")
        try:
            llm_service_logger.info(f"Initializing GGUF model from {MODEL_PATH_STR} with n_ctx={N_CTX_VAL}, n_gpu_layers={N_GPU_LAYERS_VAL}, seed={SEED_VAL}, verbose=True")
            llm_instance = Llama(
                model_path=MODEL_PATH_STR,
                n_ctx=N_CTX_VAL,
                n_gpu_layers=N_GPU_LAYERS_VAL,
                seed=SEED_VAL,
                verbose=True
            )
            llm_service_logger.info("GGUF model initialized successfully.")
        except Exception as e:
            llm_service_logger.critical(f"Failed to initialize GGUF model: {e}", exc_info=True)
            raise
    return llm_instance

MODEL_PATH = MODEL_PATH_STR
N_CTX = N_CTX_VAL

def query_gemma_gguf(
    prompt: str,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    top_p: float = 0.95,
    top_k: int = 40,
    repeat_penalty: float = 1.1,
    stop: list[str] | None = None
) -> str:
    global llm_instance
    if llm_instance is None:
        llm_service_logger.info("LLM_SERVICE: GGUF model not loaded. Attempting to load...")
        get_llm_instance()
        if llm_instance is None:  # Check again after attempting to load
            llm_service_logger.error("LLM_SERVICE: GGUF model failed to load. Cannot query.")
            return "Error: GGUF Model not loaded."

    if stop is None:
        stop = ["<|eot_id|>", "<|end_of_turn|>"]  # Default stop tokens for Gemma if not provided

    llm_service_logger.info(f"LLM_SERVICE: Preparing to query GGUF model. Max tokens: {max_tokens}, Temp: {temperature}")
    llm_service_logger.debug(f"LLM_SERVICE: Full prompt being sent to GGUF model:\n{prompt}")  # Log the full prompt

    try:
        llm_service_logger.info("LLM_SERVICE: Sending request to LlamaCPP model...")
        output = llm_instance(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            repeat_penalty=repeat_penalty,
            stop=stop,
            echo=False  # Ensure echo is False to avoid prompt in output
        )
        llm_service_logger.info("LLM_SERVICE: Received response from LlamaCPP model.")
        
        # Extract the text from the response structure
        response_text = output['choices'][0]['text'].strip() if output and output['choices'] and output['choices'][0]['text'] else ""
        
        llm_service_logger.debug(f"LLM_SERVICE: GGUF model raw response (full):\n{response_text}")  # Log the full raw response
        llm_service_logger.info(f"LLM_SERVICE: GGUF model raw response (first 150 chars): {response_text[:150]}")

        return response_text
    except Exception as e:
        llm_service_logger.error(f"LLM_SERVICE: Error during GGUF model query: {e}", exc_info=True)
        # Log more details about the exception
        if hasattr(e, 'response') and e.response is not None:
            llm_service_logger.error(f"LLM_SERVICE: Exception response status: {e.response.status_code}")
            llm_service_logger.error(f"LLM_SERVICE: Exception response text: {e.response.text}")
        return f"Error: Exception during model query - {str(e)}"

if __name__ == "__main__":
    llm_service_logger.info("LLM Service Test Block: Initializing and testing query_gemma_gguf...")
    try:
        test_prompt = "What is the capital of France? Explain in one short sentence."
        llm_service_logger.info(f"Test: Sending prompt: '{test_prompt}'")
        
        response_text = query_gemma_gguf(
            test_prompt,
            max_tokens=100,
            temperature=0.6,
            top_p=0.9,
            top_k=35,
            repeat_penalty=1.15,
            stop=None
        )
        
        print("\n--- LLM Service Test: Full Response ---")
        print(response_text)
        print("--- End of LLM Service Test Response ---")

        if "Error:" in response_text:
            llm_service_logger.error("Test: Failed due to an error string in response.")
        elif not response_text.strip():
            llm_service_logger.warning("Test: Resulted in an empty response.")
        elif len(response_text) < 10 and not any(c.isalpha() for c in response_text):
            llm_service_logger.warning(f"Test: Response seems garbled or too short: '{response_text}'")
        else:
            llm_service_logger.info("Test: Completed. Review output above.")

    except Exception as e:
        llm_service_logger.critical(f"Test: An error occurred during the test: {e}", exc_info=True)
