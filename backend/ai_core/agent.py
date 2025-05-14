# backend/ai_core/agent.py
import sys  # Ensure sys is imported first for the __package__ fix
from pathlib import Path  # Ensure Path is imported for the __package__ fix

if __name__ == "__main__" and __package__ is None:
    # This script is being run directly.
    # Set __package__ to allow relative imports.
    # The parent directory (ai_core) is part of the package 'backend.ai_core'.
    # The directory containing 'backend' (i.e., project root) must be in sys.path.
    _file = Path(__file__).resolve()
    _project_root = _file.parent.parent.parent
    sys.path.insert(0, str(_project_root))
    __package__ = "backend.ai_core"

# --- Local LLM Service Import ---
from .llm_service import query_gemma_gguf, N_CTX

import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer  # For encoding the user's query
import re
import os
import logging

# --- Define paths to your RAG knowledge base files ---
KB_DIR = Path(__file__).resolve().parent.parent / "data"
KB_JSON_PATH = KB_DIR / "grammar_chunks.json"
KB_EMBEDDINGS_NPY_PATH = KB_DIR / "grammar_embeddings.npy"

KEYWORD_TO_TOPIC_MAP = {
    "past simple": "past simple tense",
    "present simple": "present simple tense",
    "future simple": "future simple tense",
    "present continuous": "present continuous tense",
    "past continuous": "past continuous tense",
    "future continuous": "future continuous tense",
    "present perfect": "present perfect tense",
    "past perfect": "past perfect tense",
    "future perfect": "future perfect tense",
    "present perfect continuous": "present perfect continuous tense",
    "past perfect continuous": "past perfect continuous tense",
    "future perfect continuous": "future perfect continuous tense",
    "reported speech": "reported speech and indirect speech",
    "passive voice": "passive voice construction and usage",
    "conditionals": "conditional sentences (zero, first, second, third, mixed)",
    "first conditional": "first conditional sentences",
    "second conditional": "second conditional sentences",
    "third conditional": "third conditional sentences",
    "modals": "modal verbs (can, could, may, might, must, shall, should, will, would)",
    "modal verbs": "modal verbs (can, could, may, might, must, shall, should, will, would)",
    "phrasal verbs": "common English phrasal verbs and their meanings",
    "idioms": "common English idioms and their meanings",
    "general english idioms": "common English idioms and their meanings",
    "business work": "business communication (emails, meetings, presentations, reports)",
    "business letter": "writing formal business letters",
    "business email": "writing professional business emails",
    "job interview": "common questions and answers for job interviews",
    "office vocabulary": "vocabulary related to the office environment and daily work tasks",
    "presentations": "language for giving presentations in English",
    "meetings": "language for participating in meetings in English",
    "negotiations": "language for negotiations in English",
    "articles": "articles (a, an, the) and their usage",
    "quantifiers": "quantifiers (some, any, much, many, few, little, etc.)",
    "prepositions": "prepositions of time, place, and movement",
}


class MainCoreAgent:
    def __init__(self):
        self.embedding_model_name = 'all-MiniLM-L6-v2'
        self.query_embedding_model = None
        self.kb_texts = []
        self.kb_index = None

        logging.info(f"AI Agent: Initializing MainCoreAgent...")
        try:
            logging.info(f"AI Agent: Loading SentenceTransformer model '{self.embedding_model_name}' for encoding user queries...")
            self.query_embedding_model = SentenceTransformer(self.embedding_model_name)
            logging.info("AI Agent: SentenceTransformer model for queries loaded successfully.")
        except Exception as e:
            logging.critical(f"AI Agent: CRITICAL - Failed to load SentenceTransformer model for queries: {e}. RAG will not be available.")

        self._load_kb_from_precomputed()
        logging.info("MainCoreAgent initialization complete.")

    def _load_kb_from_precomputed(self):
        if not self.query_embedding_model:
            logging.warning("AI Agent: Query embedding model not loaded. Skipping Knowledge Base (KB) loading.")
            return

        if not KB_JSON_PATH.exists():
            logging.critical(f"AI Agent: CRITICAL - Knowledge Base JSON file not found at {KB_JSON_PATH}. RAG will not be available.")
            return

        if not KB_EMBEDDINGS_NPY_PATH.exists():
            logging.critical(f"AI Agent: CRITICAL - Knowledge Base Embeddings NPY file not found at {KB_EMBEDDINGS_NPY_PATH}. RAG will not be available.")
            return

        try:
            logging.info(f"AI Agent: Loading knowledge base text chunks from {KB_JSON_PATH}...")
            with open(KB_JSON_PATH, "r", encoding="utf-8") as f:
                chunks_data = json.load(f)

            self.kb_texts = [chunk.get("content", "").strip() for chunk in chunks_data if chunk.get("content", "").strip()]

            if not self.kb_texts:
                logging.warning("AI Agent: WARNING - No text chunks extracted from Knowledge Base JSON. RAG might be ineffective.")
                return
            logging.info(f"AI Agent: Loaded {len(self.kb_texts)} text chunks from JSON.")

            logging.info(f"AI Agent: Loading precomputed embeddings from {KB_EMBEDDINGS_NPY_PATH}...")
            kb_embeddings = np.load(KB_EMBEDDINGS_NPY_PATH)

            if len(self.kb_texts) != kb_embeddings.shape[0]:
                error_msg = (
                    f"AI Agent: CRITICAL ERROR - Mismatch between number of text chunks ({len(self.kb_texts)}) "
                    f"and embeddings ({kb_embeddings.shape[0]}) loaded from NPY file. "
                    "Ensure the NPY embeddings correspond exactly to the JSON chunks. KB will not be loaded."
                )
                logging.critical(error_msg)
                self.kb_texts = []
                self.kb_index = None
                return

            dimension = kb_embeddings.shape[1]
            self.kb_index = faiss.IndexFlatL2(dimension)
            self.kb_index.add(np.array(kb_embeddings, dtype=np.float32))
            logging.info(f"AI Agent: Knowledge Base successfully indexed with FAISS using {self.kb_index.ntotal} precomputed embeddings of dimension {dimension}.")

        except json.JSONDecodeError as e:
            logging.critical(f"AI Agent: CRITICAL ERROR - Failed to decode JSON from {KB_JSON_PATH}: {e}. KB will not be loaded.")
            self.kb_texts = []
            self.kb_index = None
        except Exception as e:
            logging.critical(f"AI Agent: CRITICAL ERROR - An unexpected error occurred while loading/indexing precomputed KB: {e}. KB will not be loaded.")
            self.kb_texts = []
            self.kb_index = None

    def _retrieve_from_kb(self, query_text: str, top_k_retrieval: int = 3) -> str:
        if not self.kb_index or not self.query_embedding_model or not self.kb_texts:
            logging.warning("AI Agent: Knowledge Base (KB) or query embedding model not available for retrieval. Returning empty context.")
            return ""

        if not query_text.strip():
            logging.warning("AI Agent: Empty query text for RAG retrieval. Returning empty context.")
            return ""

        try:
            logging.info(f"AI Agent (RAG): Encoding query for KB retrieval: '{query_text[:70]}...'")
            query_embedding = self.query_embedding_model.encode([query_text])

            distances, indices = self.kb_index.search(np.array(query_embedding, dtype=np.float32), top_k_retrieval)

            retrieved_docs_content = []
            if indices.size > 0:
                for i in indices[0]:
                    if 0 <= i < len(self.kb_texts):
                        retrieved_docs_content.append(self.kb_texts[i])

            if not retrieved_docs_content:
                logging.info("AI Agent (RAG): No relevant documents retrieved from KB for the query.")
                return ""

            logging.info(f"AI Agent (RAG): Retrieved {len(retrieved_docs_content)} documents from KB.")
            return "\n\n--- Retrieved Context Snippet ---\n\n".join(retrieved_docs_content)
        except Exception as e:
            logging.error(f"AI Agent (RAG): Error during KB retrieval: {e}")
            return ""

    def _prompt_llm_for_mcq(self, topic: str, num_questions: int, context_text: str | None = None) -> str:
        if context_text:
            json_output_format_structure = """\
[
  {
    "question": "The question text itself. Can be multi-line.",
    "option_a": "Text for option A",
    "option_b": "Text for option B",
    "option_c": "Text for option C",
    "option_d": "Text for option D",
    "correct_answer_letter": "A" 
  }
]"""

            prompt = (
                "<start_of_turn>user\n"
                f"You are an AI assistant that generates Multiple Choice Questions (MCQs). Your ONLY task is to create MCQs.\n"
                f"Generate EXACTLY {num_questions} MCQs for the topic: '{topic}'.\n"
                "Use the provided CONTEXT as your primary source of information. If the context is insufficient, use general knowledge about the topic.\n"
                f"Your response MUST be a valid JSON array containing EXACTLY {num_questions} MCQ objects. Each object must conform to the structure shown in the example. The 'correct_answer_letter' field must be one of 'A', 'B', 'C', or 'D'.\n\n"
                
                "VERY IMPORTANT JSON FORMATTING RULES - FOLLOW EXACTLY:\n"
                "1. The entire response MUST be a single, valid JSON array, starting with '[' and ending with ']'.\n"
                "2. Do NOT use any code block delimiters (like ```json or ```) around or inside the JSON array.\n"
                "3. All keys (e.g., \"question\", \"option_a\") and all string values (e.g., the question text, option texts) MUST be enclosed in double quotes (\").\n"
                "4. Do NOT use single quotes (') for JSON keys or string values.\n"
                "5. Use standard JSON escaping (e.g., \\\" for a double quote within a string, \\\\n for a newline) ONLY when necessary. Do not add unnecessary or incorrect escape characters.\n"
                "6. Ensure there are no trailing commas after the last element in an array or the last property in an object.\n"
                "7. Output ONLY the JSON array. No introductory text, no explanations, no apologies, no summaries. Just the JSON.\n\n"

                f"JSON Structure for each MCQ object (the response will be an array of these objects):\n{json_output_format_structure}\n\n"
                
                f"Topic: '{topic}'\n"
                "CONTEXT TO USE FOR MCQ GENERATION:\n"
                "-------------------------------------\n"
                f"{context_text}\n"
                "-------------------------------------\n\n"
                "<end_of_turn>\n"
                "<start_of_turn>model\n"
            )
            
            prompt_tokens_rag = len(prompt.split())  # Approximate token count
            buffer_tokens_rag = 512 
            available_for_generation_rag = N_CTX - prompt_tokens_rag - buffer_tokens_rag
            
            # RAG specific parameters (adjust as needed based on previous findings)
            estimated_tokens_per_mcq_rag = 350 
            rag_temperature = 0.5  # Increased from 0.4
            rag_top_p = 0.7
            rag_top_k = 30
            rag_repeat_penalty = 1.5  # Increased from 1.2
            rag_stop_sequences = ["]", "<end_of_turn>", "User:"]

            calculated_max_tokens_rag = min(num_questions * estimated_tokens_per_mcq_rag, available_for_generation_rag)
            max_new_tokens_rag = max(100, calculated_max_tokens_rag)  # Ensure at least 100 tokens
            max_new_tokens_rag = min(max_new_tokens_rag, N_CTX - buffer_tokens_rag)  # Cap by N_CTX
            max_new_tokens_rag = min(max_new_tokens_rag, 4096)  # Absolute cap if needed

            logging.info(f"AI Agent (RAG): Prompt tokens (estimated): {prompt_tokens_rag}, Max new tokens for LLM: {max_new_tokens_rag}, Temperature: {rag_temperature}, N_CTX: {N_CTX}, Available for generation (estimated): {available_for_generation_rag}")

            if max_new_tokens_rag <= 0:
                logging.error(f"AI Agent (RAG): Calculated max_new_tokens_rag is zero or negative ({max_new_tokens_rag}). Prompt length ({prompt_tokens_rag}) might be too large for N_CTX ({N_CTX}).")
                return "Error: Prompt too long or N_CTX too small for RAG generation."

            logging.debug(f"LLM_AGENT (RAG): Full prompt being sent to LLM Service:\n{prompt}")
            logging.info(f"AI Agent: Querying LLM in RAG mode. Max new tokens: {max_new_tokens_rag}, Temp: {rag_temperature}, Top_p: {rag_top_p}, Top_k: {rag_top_k}, Repeat Penalty: {rag_repeat_penalty}")
            raw_response = query_gemma_gguf(
                prompt=prompt,
                max_tokens=max_new_tokens_rag,
                temperature=rag_temperature,
                top_p=rag_top_p,
                top_k=rag_top_k,
                repeat_penalty=rag_repeat_penalty,
                stop=rag_stop_sequences
            )

        else:
            prompt = (
                "<start_of_turn>user\n"
                f"You are an AI assistant that generates Multiple Choice Questions (MCQs). Your ONLY task is to create MCQs.\n"
                f"Generate EXACTLY {num_questions} MCQs for the topic: '{topic}' using your general knowledge of English grammar.\n"
                "Your response MUST ONLY contain the MCQs in the specified format. No other text, preamble, or explanation.\n\n"

                f"Topic: '{topic}'\n"
                f"Number of MCQs to generate: {num_questions}\n\n"

                "OUTPUT REQUIREMENTS (VERY IMPORTANT - FOLLOW EXACTLY):\n"
                f"1. You MUST generate EXACTLY {num_questions} MCQs.\n"
                "2. Start your response IMMEDIATELY with 'Question 1:'. DO NOT add any text before 'Question 1:'.\n"
                "3. Each MCQ must strictly follow this format (X is the question number):\n"
                "   Question X: [The question text itself, can be multi-line]\n"
                "   A) [Option A text]\n"
                "   B) [Option B text]\n"
                "   C) [Option C text]\n"
                "   D) [Option D text]\n"
                "   Correct Answer: [A, B, C, or D]\n"
                "   (A single blank line MUST follow the 'Correct Answer:' line, before the next 'Question X+1:' or the end of your response if it's the last question).\n\n"

                f"Example of ONE correctly formatted MCQ block (your response should contain {num_questions} such blocks):\n"
                "Question 1: What is the past simple form of 'go'?\n"
                "A) Going\n"
                "B) Went\n"
                "C) Gone\n"
                "D) Goes\n"
                "Correct Answer: B\n"
                "\n"

                f"Begin generating the {num_questions} MCQs now. Your entire response must start with 'Question 1:' and contain only the MCQs formatted as described.\n"
                "<end_of_turn>\n"
                "<start_of_turn>model\n"
            )

            prompt_tokens = len(prompt.split())
            buffer_tokens = 512
            available_for_generation = N_CTX - prompt_tokens - buffer_tokens
            estimated_tokens_per_mcq = 200

            calculated_max_tokens = min(num_questions * estimated_tokens_per_mcq, available_for_generation)
            max_new_tokens = max(100, calculated_max_tokens)
            max_new_tokens = min(max_new_tokens, N_CTX - buffer_tokens)
            max_new_tokens = min(max_new_tokens, 4096)

            logging.info(f"AI Agent (Non-RAG): Prompt tokens (estimated): {prompt_tokens}, Max new tokens for LLM: {max_new_tokens}, Temperature: 0.7, N_CTX: {N_CTX}, Available for generation (estimated): {available_for_generation}")

            if max_new_tokens <= 0:
                logging.error(f"AI Agent (Non-RAG): Calculated max_new_tokens is zero or negative ({max_new_tokens}). Prompt length ({prompt_tokens}) might be too large for N_CTX ({N_CTX}).")
                return "Error: Prompt too long or N_CTX too small for generation."

            stop_sequences = [
                "User:",
                "Assistant:",
                "Note:",
                "Explanation:",
                "<end_of_turn>",
                f"Question {num_questions + 1}:"
            ]
            
            logging.debug(f"LLM_AGENT (Non-RAG): Full prompt being sent to LLM Service:\n{prompt}")

            logging.info(f"AI Agent: Querying LLM in basic mode. Max new tokens: {max_new_tokens}, Temp: 0.7")
            raw_response = query_gemma_gguf(
                prompt=prompt,
                max_tokens=max_new_tokens,
                temperature=0.7,
                stop=stop_sequences
            )

        logging.debug(f"Raw response from LLM:\n{raw_response}")
        return raw_response

    def _parse_mcq_via_regex(self, raw_response: str, num_questions_expected: int) -> list:
        mcqs = []
        pattern = re.compile(
            r"Question\s*\d+:\s*(.*?)\s*"
            r"A\)\s*(.*?)\s*"
            r"B\)\s*(.*?)\s*"
            r"C\)\s*(.*?)\s*"
            r"D\)\s*(.*?)\s*"
            r"Correct Answer:\s*([A-D])",
            re.DOTALL | re.IGNORECASE 
        )
        
        matches = pattern.findall(raw_response)
        
        for match in matches:
            if len(mcqs) >= num_questions_expected:
                logging.info(f"AI Agent (Regex Parse): Reached expected number of MCQs ({num_questions_expected}). Stopping regex parsing.")
                break
            
            question_text, opt_a_text, opt_b_text, opt_c_text, opt_d_text, correct_letter = match
            
            mcq = {
                "question": question_text.strip(),
                "option_a": opt_a_text.strip(),
                "option_b": opt_b_text.strip(),
                "option_c": opt_c_text.strip(),
                "option_d": opt_d_text.strip(),
                "correct_answer_letter": correct_letter.strip().upper(),
            }
            mcqs.append(mcq)
            
        if not mcqs:
            logging.warning(f"AI Agent (Regex Parse): Could not parse any MCQs using regex from response (first 200 chars): {raw_response[:200]}...")
        elif len(mcqs) < num_questions_expected:
            logging.warning(f"AI Agent (Regex Parse): Parsed {len(mcqs)} MCQs via regex, but expected {num_questions_expected}.")
        else:
            logging.info(f"AI Agent (Regex Parse): Successfully parsed {len(mcqs)} MCQs via regex.")
            
        return mcqs

    def _parse_llm_mcq_response(self, raw_response: str, num_questions_expected: int) -> list:
        logging.debug(f"AI Agent: Attempting to parse LLM response (first 300 chars): {raw_response[:300]}")
        parsed_mcqs = []

        try:
            json_start_index = -1
            json_end_index = -1
            
            code_block_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", raw_response, re.DOTALL)
            if code_block_match:
                json_str_candidate = code_block_match.group(1)
                logging.debug(f"AI Agent: Found JSON array within code block: {json_str_candidate[:200]}...")
            else:
                json_start_index = raw_response.find('[')
                json_end_index = raw_response.rfind(']')

                if json_start_index != -1 and json_end_index != -1 and json_start_index < json_end_index:
                    json_str_candidate = raw_response[json_start_index : json_end_index + 1]
                    logging.debug(f"AI Agent: Found potential JSON string (plain): {json_str_candidate[:200]}...")
                else:
                    json_str_candidate = None 

            if json_str_candidate:
                parsed_data = json.loads(json_str_candidate)
                
                if isinstance(parsed_data, list):
                    valid_mcqs = []
                    for item in parsed_data:
                        if isinstance(item, dict) and "question" in item and \
                           "option_a" in item and "option_b" in item and \
                           "option_c" in item and "option_d" in item and \
                           "correct_answer_letter" in item:
                            valid_mcqs.append(item)
                        else:
                            logging.warning(f"AI Agent: JSON item does not look like an MCQ: {str(item)[:100]}")
                    
                    parsed_mcqs = valid_mcqs
                    logging.info(f"AI Agent: Successfully parsed {len(parsed_mcqs)} MCQs as JSON.")
                    
                    if len(parsed_mcqs) > num_questions_expected:
                        logging.warning(f"AI Agent: JSON parsing yielded {len(parsed_mcqs)} MCQs, more than expected {num_questions_expected}. Truncating.")
                        return parsed_mcqs[:num_questions_expected]
                    return parsed_mcqs
                else:
                    logging.warning(f"AI Agent: Parsed JSON is not a list, but type {type(parsed_data)}. Content: {str(parsed_data)[:200]}")
            else:
                logging.info("AI Agent: Could not find a clear JSON array structure in the response for primary JSON parsing.")

        except json.JSONDecodeError as e:
            error_snippet_start = json_start_index if json_start_index != -1 else 0
            error_snippet_end = (json_end_index + 1) if json_end_index != -1 else len(raw_response)
            error_snippet_end = min(error_snippet_end, error_snippet_start + 100) 
            logging.warning(f"AI Agent: JSON parsing failed. Error: {e}. Response snippet for error: {raw_response[error_snippet_start:error_snippet_end]}...")
        except Exception as e:
            logging.error(f"AI Agent: Unexpected error during JSON parsing attempt: {e}")
        
        if not parsed_mcqs:
            logging.info("AI Agent: JSON parsing did not yield MCQs or failed. Falling back to regex-based parsing.")
            parsed_mcqs = self._parse_mcq_via_regex(raw_response, num_questions_expected)
            if parsed_mcqs:
                 logging.info(f"AI Agent: Successfully parsed {len(parsed_mcqs)} MCQs using fallback regex method.")
            else:
                 logging.warning("AI Agent: Fallback regex parsing also failed to extract MCQs.")
        
        return parsed_mcqs

    def generate_mcqs_basic(self, topic: str, num_questions: int = 5) -> list:
        logging.info(f"AI Agent: Generating {num_questions} basic MCQs for topic: '{topic}'")
        raw_response = self._prompt_llm_for_mcq(topic, num_questions, context_text=None)
        
        if not isinstance(raw_response, str) or "Error:" in raw_response:
            logging.error(f"AI Agent: Error from LLM during basic generation: {raw_response}")
            return []
            
        parsed_mcqs = self._parse_llm_mcq_response(raw_response, num_questions_expected=num_questions)
        logging.info(f"AI Agent: Parsed {len(parsed_mcqs)} basic MCQs out of {num_questions} requested for topic '{topic}'.")
        return parsed_mcqs

    def generate_mcqs_with_rag(self, user_topic: str, num_questions: int = 5) -> list:
        """Generates MCQs using RAG for the given user topic."""
        logging.info(f"AI Agent: Generating {num_questions} RAG MCQs for user topic: '{user_topic}'")
        
        mapped_topic = KEYWORD_TO_TOPIC_MAP.get(user_topic.lower().strip(), user_topic)
        if mapped_topic != user_topic:
            logging.info(f"AI Agent (RAG): Mapped user topic '{user_topic}' to canonical topic '{mapped_topic}'.")
        else:
            logging.info(f"AI Agent (RAG): Using user topic directly as canonical topic: '{mapped_topic}'.")

        context = ""
        if self.kb_index and self.query_embedding_model and self.kb_texts:
            context = self._retrieve_from_kb(mapped_topic, top_k_retrieval=1)
            if context:
                logging.info(f"AI Agent (RAG): Retrieved context for '{mapped_topic}'. Preview (first 100 chars): {context[:100]}...")
            else:
                logging.info(f"AI Agent (RAG): No context retrieved for '{mapped_topic}'. Proceeding without specific RAG context, will rely on general knowledge for this topic.")
        else:
            logging.warning("AI Agent (RAG): Knowledge Base (KB) or query model not fully available. Proceeding without RAG context.")

        raw_response = self._prompt_llm_for_mcq(mapped_topic, num_questions, context_text=context)

        if not isinstance(raw_response, str) or "Error:" in raw_response:
            logging.error(f"AI Agent: Error from LLM during RAG generation: {raw_response}")
            return []

        parsed_mcqs = self._parse_llm_mcq_response(raw_response, num_questions_expected=num_questions)
        logging.info(f"AI Agent: Parsed {len(parsed_mcqs)} RAG MCQs out of {num_questions} requested for user topic '{user_topic}'.")
        return parsed_mcqs

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s: %(message)s')
    
    llm_service_specific_logger = logging.getLogger('backend.ai_core.llm_service')
    llm_service_specific_logger.setLevel(logging.DEBUG)

    agent_logger = logging.getLogger(__name__)
    agent_logger.setLevel(logging.DEBUG)

    test_logger = logging.getLogger("TEST_AGENT_SCRIPT") 
    test_logger.setLevel(logging.INFO)

    test_logger.info("AI Agent Test Block: Initializing agent...")
    agent = MainCoreAgent()
    test_logger.info("Agent initialized.")

    test_logger.info("--- Test Case 1: Basic MCQ Generation (5 questions) ---")
    topic_1 = "Present Simple Tense"
    num_q_1 = 5
    test_logger.info(f"Requesting {num_q_1} basic MCQ(s) for topic: '{topic_1}'")
    parsed_mcqs_1 = agent.generate_mcqs_basic(topic=topic_1, num_questions=num_q_1)
    
    print(f"\n--- Parsed MCQs for Test Case 1 ({topic_1}, {num_q_1} requested) ---")
    print(json.dumps(parsed_mcqs_1, indent=2))
    if len(parsed_mcqs_1) == num_q_1:
        test_logger.info(f"SUCCESS: Correct number of MCQs ({len(parsed_mcqs_1)}) parsed for Test Case 1.")
    else:
        test_logger.warning(f"WARNING: Expected {num_q_1} MCQ(s), but parsed {len(parsed_mcqs_1)} for Test Case 1.")

    test_logger.info("\n--- Test Case 2: Basic MCQ Generation (5 questions) ---")
    topic_2 = "Past Continuous Tense"
    num_q_2 = 5
    test_logger.info(f"Requesting {num_q_2} basic MCQ(s) for topic: '{topic_2}'")
    parsed_mcqs_2 = agent.generate_mcqs_basic(topic=topic_2, num_questions=num_q_2)

    print(f"\n--- Parsed MCQs for Test Case 2 ({topic_2}, {num_q_2} requested) ---")
    print(json.dumps(parsed_mcqs_2, indent=2))
    if len(parsed_mcqs_2) == num_q_2:
        test_logger.info(f"SUCCESS: Correct number of MCQs ({len(parsed_mcqs_2)}) parsed for Test Case 2.")
    else:
        test_logger.warning(f"WARNING: Expected {num_q_2} MCQ(s), but parsed {len(parsed_mcqs_2)} for Test Case 2.")

    test_logger.info("\n--- Test Case 3: RAG MCQ Generation (5 questions) ---")
    topic_3_user = "past simple"
    num_q_3 = 5
    test_logger.info(f"Requesting {num_q_3} RAG MCQ(s) for user topic: '{topic_3_user}'")
    parsed_mcqs_3 = agent.generate_mcqs_with_rag(user_topic=topic_3_user, num_questions=num_q_3)

    print(f"\n--- Parsed MCQs for Test Case 3 (User Topic: '{topic_3_user}', {num_q_3} requested) ---")
    print(json.dumps(parsed_mcqs_3, indent=2))
    if len(parsed_mcqs_3) == num_q_3:
        test_logger.info(f"SUCCESS: Correct number of MCQs ({len(parsed_mcqs_3)}) parsed for Test Case 3.")
    else:
        test_logger.warning(f"WARNING: Expected {num_q_3} MCQ(s), but parsed {len(parsed_mcqs_3)} for Test Case 3.")

    test_logger.info("\n--- Test Case 4: RAG MCQ Generation (5 questions, general topic) ---")
    topic_4_user = "General English Idioms" 
    num_q_4 = 5
    test_logger.info(f"Requesting {num_q_4} RAG MCQ(s) for user topic: '{topic_4_user}'")
    parsed_mcqs_4 = agent.generate_mcqs_with_rag(user_topic=topic_4_user, num_questions=num_q_4)

    print(f"\n--- Parsed MCQs for Test Case 4 (User Topic: '{topic_4_user}', {num_q_4} requested) ---")
    print(json.dumps(parsed_mcqs_4, indent=2))
    if len(parsed_mcqs_4) == num_q_4:
        test_logger.info(f"SUCCESS: Correct number of MCQs ({len(parsed_mcqs_4)}) parsed for Test Case 4.")
    else:
        test_logger.warning(f"WARNING: Expected {num_q_4} MCQ(s), but parsed {len(parsed_mcqs_4)} for Test Case 4.")

    test_logger.info("\nAI Agent Test Block finished.")
