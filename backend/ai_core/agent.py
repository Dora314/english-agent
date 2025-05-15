# %% [markdown]
# # AI Core Agent - Jupyter Notebook

# %% [markdown]
# ## 1. Imports và Cài đặt ban đầu
# Đảm bảo rằng tệp `llm_service.py` và thư mục `data` (chứa `grammar_chunks.json` và `grammar_embeddings.npy`)
# nằm trong cùng thư mục với notebook này.

# %%
import sys
from pathlib import Path
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import re
import os
import logging

# %% [markdown]
# ## 2. LLM Service (Cần tạo tệp llm_service.py)
# Skript `agent.py` import `query_gemma_gguf` và `N_CTX` từ `llm_service`.
# Để notebook này chạy được, bạn cần tạo một tệp `llm_service.py` trong cùng thư mục.
#
# **Ví dụ nội dung tệp `llm_service.py` (thay thế bằng hàm thực tế của bạn):**
# ```python
# # llm_service.py
# N_CTX = 2048 # Giá trị ví dụ, thay bằng giá trị thực của mô hình bạn dùng
#
# def query_gemma_gguf(prompt: str, max_tokens: int, temperature: float, top_p=None, top_k=None, repeat_penalty=None, stop=None):
#     """
#     Đây là hàm giả lập cho việc gọi mô hình Gemma GGUF của bạn.
#     Hãy thay thế bằng logic gọi LLM thực tế.
#     """
#     print(f"--- LLM SERVICE ĐƯỢC GỌI (Giả lập) ---")
#     print(f"Prompt (100 ký tự đầu): {prompt[:100]}...")
#     print(f"Max tokens: {max_tokens}, Nhiệt độ: {temperature}")
#     print(f"Stop sequences: {stop}")
#
#     # Giả lập một cấu trúc phản hồi
#     if "JSON array" in prompt: # Giả lập cho RAG
#         return """
# [
#   {
#     "question": "Đây là câu hỏi mẫu từ LLM giả lập?",
#     "option_a": "Lựa chọn A",
#     "option_b": "Lựa chọn B",
#     "option_c": "Lựa chọn C",
#     "option_d": "Lựa chọn D",
#     "correct_answer_letter": "A"
#   }
# ]
# """
#     else: # Giả lập cho chế độ cơ bản
#         return """
# Question 1: Placeholder là gì?
# A) Một vật thật
# B) Một vật thay thế
# C) Một loại cà phê
# D) Một ngôn ngữ lập trình
# Correct Answer: B
#
# Question 2: Đây có phải phản hồi LLM thật không?
# A) Có
# B) Không
# C) Có thể
# D) Hỏi lại sau
# Correct Answer: B
# """
# ```
# **Hãy tạo tệp `llm_service.py` này.**

# %%
# --- Import LLM Service cục bộ ---
# Giả định llm_service.py nằm cùng thư mục với notebook
try:
    from llm_service import query_gemma_gguf, N_CTX
    print("Đã import thành công query_gemma_gguf và N_CTX từ llm_service.py")
    print(f"Giá trị N_CTX: {N_CTX}")
except ImportError as e:
    print(f"LỖI: Không thể import từ llm_service.py: {e}")
    print("Vui lòng đảm bảo tệp llm_service.py nằm trong cùng thư mục với notebook này và chứa hàm query_gemma_gguf và biến N_CTX.")
    # Cung cấp giá trị giả nếu import thất bại, để phần còn lại của notebook có thể được cấu trúc
    # Tuy nhiên, agent sẽ không hoạt động chính xác nếu không có llm_service thực tế.
    N_CTX = 2048 # Giá trị giả mặc định
    def query_gemma_gguf(prompt: str, max_tokens: int, temperature: float, top_p=None, top_k=None, repeat_penalty=None, stop=None):
        print("CẢNH BÁO: Đang sử dụng query_gemma_gguf GIẢ LẬP. Các lệnh gọi LLM sẽ không hoạt động như mong đợi.")
        return "Lỗi: LLM service chưa được import đúng cách."

# %% [markdown]
# ## 3. Cấu hình và Đường dẫn
# Các đường dẫn được định nghĩa tương đối với thư mục làm việc hiện tại của notebook.
# Thư mục `data` phải nằm trong cùng thư mục với notebook này.

# %%
# --- Định nghĩa đường dẫn đến các tệp cơ sở tri thức RAG ---
# Giả định thư mục 'data' nằm trong cùng thư mục với notebook.
# Path.cwd() trả về thư mục làm việc hiện tại của notebook.
NOTEBOOK_DIR = Path.cwd()
KB_DIR = NOTEBOOK_DIR / "data"
KB_JSON_PATH = KB_DIR / "grammar_chunks.json"
KB_EMBEDDINGS_NPY_PATH = KB_DIR / "grammar_embeddings.npy"

print(f"Thư mục notebook: {NOTEBOOK_DIR}")
print(f"Thư mục Cơ sở tri thức (KB): {KB_DIR}")
print(f"Đường dẫn KB JSON: {KB_JSON_PATH} (Tồn tại: {KB_JSON_PATH.exists()})")
print(f"Đường dẫn KB Embeddings: {KB_EMBEDDINGS_NPY_PATH} (Tồn tại: {KB_EMBEDDINGS_NPY_PATH.exists()})")

# Tạo tệp dữ liệu giả nếu chúng không tồn tại, để notebook có thể chạy
# Hãy thay thế chúng bằng các tệp dữ liệu thực tế của bạn.
if not KB_DIR.exists():
    KB_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Đã tạo thư mục: {KB_DIR}")

if not KB_JSON_PATH.exists():
    print(f"CẢNH BÁO: {KB_JSON_PATH} không tìm thấy. Đang tạo tệp giả để minh họa.")
    dummy_json_content = [
        {"id": "chunk1", "content": "Thì quá khứ đơn được dùng để nói về các hành động đã hoàn thành trong quá khứ."},
        {"id": "chunk2", "content": "Ví dụ về quá khứ đơn: Tôi đã đi bộ về nhà. Anh ấy đã xem một bộ phim."}
    ]
    with open(KB_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(dummy_json_content, f, indent=2)
    print(f"Đã tạo tệp giả {KB_JSON_PATH}")

if not KB_EMBEDDINGS_NPY_PATH.exists():
    print(f"CẢNH BÁO: {KB_EMBEDDINGS_NPY_PATH} không tìm thấy. Đang tạo tệp giả để minh họa.")
    # Đối với 'all-MiniLM-L6-v2', chiều embedding là 384.
    # Tạo embedding giả khớp với số lượng chunk trong dummy_json_content và chiều 384.
    dummy_embeddings = np.random.rand(2, 384).astype(np.float32) # 2 chunks, 384 chiều
    np.save(KB_EMBEDDINGS_NPY_PATH, dummy_embeddings)
    print(f"Đã tạo tệp giả {KB_EMBEDDINGS_NPY_PATH} với shape {dummy_embeddings.shape}")


# %%
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

# %% [markdown]
# ## 4. Định nghĩa lớp MainCoreAgent

# %%
class MainCoreAgent:
    def __init__(self): # Sửa 'init' thành '__init__'
        self.embedding_model_name = 'all-mpnet-base-v2'
        self.query_embedding_model = None
        self.kb_texts = []
        self.kb_index = None

        # Lấy một logger cụ thể cho lớp này
        self.logger = logging.getLogger(__name__ + ".MainCoreAgent")

        self.logger.info(f"AI Agent: Đang khởi tạo MainCoreAgent...")
        try:
            self.logger.info(f"AI Agent: Đang tải mô hình SentenceTransformer '{self.embedding_model_name}' để mã hóa truy vấn người dùng...")
            self.query_embedding_model = SentenceTransformer(self.embedding_model_name)
            self.logger.info("AI Agent: Đã tải thành công mô hình SentenceTransformer cho truy vấn.")
        except Exception as e:
            self.logger.critical(f"AI Agent: LỖI NGHIÊM TRỌNG - Không thể tải mô hình SentenceTransformer cho truy vấn: {e}. RAG sẽ không khả dụng.")

        self._load_kb_from_precomputed()
        self.logger.info("Hoàn tất khởi tạo MainCoreAgent.")

    def _load_kb_from_precomputed(self):
        if not self.query_embedding_model:
            self.logger.warning("AI Agent: Mô hình embedding truy vấn chưa được tải. Bỏ qua việc tải Cơ sở tri thức (KB).")
            return

        if not KB_JSON_PATH.exists():
            self.logger.critical(f"AI Agent: LỖI NGHIÊM TRỌNG - Không tìm thấy tệp JSON Cơ sở tri thức tại {KB_JSON_PATH}. RAG sẽ không khả dụng.")
            return

        if not KB_EMBEDDINGS_NPY_PATH.exists():
            self.logger.critical(f"AI Agent: LỖI NGHIÊM TRỌNG - Không tìm thấy tệp NPY Embeddings Cơ sở tri thức tại {KB_EMBEDDINGS_NPY_PATH}. RAG sẽ không khả dụng.")
            return

        try:
            self.logger.info(f"AI Agent: Đang tải các đoạn văn bản cơ sở tri thức từ {KB_JSON_PATH}...")
            with open(KB_JSON_PATH, "r", encoding="utf-8") as f:
                chunks_data = json.load(f)

            self.kb_texts = [chunk.get("content", "").strip() for chunk in chunks_data if chunk.get("content", "").strip()]

            if not self.kb_texts:
                self.logger.warning("AI Agent: CẢNH BÁO - Không có đoạn văn bản nào được trích xuất từ JSON Cơ sở tri thức. RAG có thể không hiệu quả.")
                return # Quan trọng: trả về nếu không có văn bản, để tránh lỗi với kb_embeddings rỗng
            self.logger.info(f"AI Agent: Đã tải {len(self.kb_texts)} đoạn văn bản từ JSON.")

            self.logger.info(f"AI Agent: Đang tải các embedding đã tính toán trước từ {KB_EMBEDDINGS_NPY_PATH}...")
            kb_embeddings = np.load(KB_EMBEDDINGS_NPY_PATH)

            if len(self.kb_texts) != kb_embeddings.shape[0]:
                error_msg = (
                    f"AI Agent: LỖI NGHIÊM TRỌNG - Không khớp giữa số lượng đoạn văn bản ({len(self.kb_texts)}) "
                    f"và embeddings ({kb_embeddings.shape[0]}) được tải từ tệp NPY. "
                    "Đảm bảo các embedding NPY tương ứng chính xác với các đoạn JSON. KB sẽ không được tải."
                )
                self.logger.critical(error_msg)
                self.kb_texts = []
                self.kb_index = None
                return

            if kb_embeddings.size == 0 : # Xử lý trường hợp tệp embeddings rỗng hoặc lỗi dẫn đến mảng rỗng
                self.logger.critical(f"AI Agent: LỖI NGHIÊM TRỌNG - Mảng embeddings được tải từ {KB_EMBEDDINGS_NPY_PATH} bị rỗng. KB sẽ không được tải.")
                self.kb_texts = []
                self.kb_index = None
                return

            dimension = kb_embeddings.shape[1]
            self.kb_index = faiss.IndexFlatL2(dimension)
            self.kb_index.add(np.array(kb_embeddings, dtype=np.float32))
            self.logger.info(f"AI Agent: Cơ sở tri thức đã được lập chỉ mục thành công với FAISS sử dụng {self.kb_index.ntotal} embedding đã tính toán trước có chiều {dimension}.")

        except json.JSONDecodeError as e:
            self.logger.critical(f"AI Agent: LỖI NGHIÊM TRỌNG - Không thể giải mã JSON từ {KB_JSON_PATH}: {e}. KB sẽ không được tải.")
            self.kb_texts = []
            self.kb_index = None
        except Exception as e:
            self.logger.critical(f"AI Agent: LỖI NGHIÊM TRỌNG - Đã xảy ra lỗi không mong muốn khi tải/lập chỉ mục KB đã tính toán trước: {e}. KB sẽ không được tải.")
            self.kb_texts = []
            self.kb_index = None

    def _retrieve_from_kb(self, query_text: str, top_k_retrieval: int = 3) -> str:
        if not self.kb_index or not self.query_embedding_model or not self.kb_texts:
            self.logger.warning("AI Agent: Cơ sở tri thức (KB) hoặc mô hình embedding truy vấn không khả dụng để truy xuất. Trả về ngữ cảnh rỗng.")
            return ""

        if not query_text.strip():
            self.logger.warning("AI Agent: Văn bản truy vấn rỗng cho truy xuất RAG. Trả về ngữ cảnh rỗng.")
            return ""

        try:
            self.logger.info(f"AI Agent (RAG): Đang mã hóa truy vấn để truy xuất KB: '{query_text[:70]}...'")
            query_embedding = self.query_embedding_model.encode([query_text])

            distances, indices = self.kb_index.search(np.array(query_embedding, dtype=np.float32), top_k_retrieval)

            retrieved_docs_content = []
            if indices.size > 0:
                for i in indices[0]: # D, I là (1, top_k_retrieval) cho một truy vấn
                    if 0 <= i < len(self.kb_texts): # Kiểm tra giới hạn chỉ mục
                        retrieved_docs_content.append(self.kb_texts[i])

            if not retrieved_docs_content:
                self.logger.info("AI Agent (RAG): Không có tài liệu liên quan nào được truy xuất từ KB cho truy vấn.")
                return ""

            self.logger.info(f"AI Agent (RAG): Đã truy xuất {len(retrieved_docs_content)} tài liệu từ KB.")
            return "\n\n--- Retrieved Context Snippet ---\n\n".join(retrieved_docs_content)
        except Exception as e:
            self.logger.error(f"AI Agent (RAG): Lỗi trong quá trình truy xuất KB: {e}")
            return ""

    def _prompt_llm_for_mcq(self, topic: str, num_questions: int, context_text: str | None = None) -> str:
        global N_CTX # Sử dụng biến N_CTX toàn cục đã được import
        if 'N_CTX' not in globals():
            self.logger.error("N_CTX không được định nghĩa. Vui lòng đảm bảo nó được import từ llm_service.py hoặc được định nghĩa toàn cục.")
            N_CTX = 2048 # Giá trị dự phòng, nhưng không lý tưởng

        if context_text: # Chế độ RAG
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
            
            prompt_tokens_rag = len(prompt.split())
            buffer_tokens_rag = 512 
            available_for_generation_rag = N_CTX - prompt_tokens_rag - buffer_tokens_rag
            
            estimated_tokens_per_mcq_rag = 350 
            rag_temperature = 0.5
            rag_top_p = 0.7
            rag_top_k = 30
            rag_repeat_penalty = 1.5
            rag_stop_sequences = ["]", "<end_of_turn>", "User:"]

            calculated_max_tokens_rag = min(num_questions * estimated_tokens_per_mcq_rag, available_for_generation_rag)
            max_new_tokens_rag = max(100, calculated_max_tokens_rag)
            max_new_tokens_rag = min(max_new_tokens_rag, N_CTX - buffer_tokens_rag)
            max_new_tokens_rag = min(max_new_tokens_rag, 4096)

            self.logger.info(f"AI Agent (RAG): Số token prompt (ước tính): {prompt_tokens_rag}, Số token mới tối đa cho LLM: {max_new_tokens_rag}, Nhiệt độ: {rag_temperature}, N_CTX: {N_CTX}, Khả dụng để tạo (ước tính): {available_for_generation_rag}")

            if max_new_tokens_rag <= 0:
                self.logger.error(f"AI Agent (RAG): max_new_tokens_rag được tính toán bằng không hoặc âm ({max_new_tokens_rag}). Độ dài prompt ({prompt_tokens_rag}) có thể quá lớn so với N_CTX ({N_CTX}).")
                return "Lỗi: Prompt quá dài hoặc N_CTX quá nhỏ cho việc tạo RAG."

            self.logger.debug(f"LLM_AGENT (RAG): Toàn bộ prompt được gửi đến LLM Service:\n{prompt[:500]}...")
            self.logger.info(f"AI Agent: Đang truy vấn LLM ở chế độ RAG. Số token mới tối đa: {max_new_tokens_rag}, Temp: {rag_temperature}, Top_p: {rag_top_p}, Top_k: {rag_top_k}, Repeat Penalty: {rag_repeat_penalty}")
            raw_response = query_gemma_gguf(
                prompt=prompt,
                max_tokens=max_new_tokens_rag,
                temperature=rag_temperature,
                top_p=rag_top_p,
                top_k=rag_top_k,
                repeat_penalty=rag_repeat_penalty,
                stop=rag_stop_sequences
            )

        else: # Chế độ cơ bản (Không RAG)
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

            self.logger.info(f"AI Agent (Không RAG): Số token prompt (ước tính): {prompt_tokens}, Số token mới tối đa cho LLM: {max_new_tokens}, Nhiệt độ: 0.7, N_CTX: {N_CTX}, Khả dụng để tạo (ước tính): {available_for_generation}")

            if max_new_tokens <= 0:
                self.logger.error(f"AI Agent (Không RAG): max_new_tokens được tính toán bằng không hoặc âm ({max_new_tokens}). Độ dài prompt ({prompt_tokens}) có thể quá lớn so với N_CTX ({N_CTX}).")
                return "Lỗi: Prompt quá dài hoặc N_CTX quá nhỏ để tạo."

            stop_sequences = [
                "User:",
                "Assistant:",
                "Note:",
                "Explanation:",
                "<end_of_turn>",
                f"Question {num_questions + 1}:"
            ]
            
            self.logger.debug(f"LLM_AGENT (Không RAG): Toàn bộ prompt được gửi đến LLM Service:\n{prompt[:500]}...")

            self.logger.info(f"AI Agent: Đang truy vấn LLM ở chế độ cơ bản. Số token mới tối đa: {max_new_tokens}, Temp: 0.7")
            raw_response = query_gemma_gguf(
                prompt=prompt,
                max_tokens=max_new_tokens,
                temperature=0.7,
                stop=stop_sequences
            )
        
        self.logger.debug(f"Phản hồi thô từ LLM (300 ký tự đầu):\n{str(raw_response)[:300]}")
        return raw_response

    def _parse_mcq_via_regex(self, raw_response: str, num_questions_expected: int) -> list:
        mcqs = []
        pattern = re.compile(
            r"Question\s*\d+:\s*(.*?)\s*"       # Văn bản câu hỏi
            r"A\)\s*(.*?)\s*"                   # Lựa chọn A
            r"B\)\s*(.*?)\s*"                   # Lựa chọn B
            r"C\)\s*(.*?)\s*"                   # Lựa chọn C
            r"D\)\s*(.*?)\s*"                   # Lựa chọn D
            r"Correct Answer:\s*([A-D])",       # Đáp án đúng
            re.DOTALL | re.IGNORECASE 
        )
        
        current_pos = 0
        while len(mcqs) < num_questions_expected:
            match = pattern.search(raw_response, pos=current_pos)
            if not match:
                break

            question_text, opt_a_text, opt_b_text, opt_c_text, opt_d_text, correct_letter = \
                (m.strip() for m in match.groups())
            
            mcq = {
                "question": question_text,
                "option_a": opt_a_text,
                "option_b": opt_b_text,
                "option_c": opt_c_text,
                "option_d": opt_d_text,
                "correct_answer_letter": correct_letter.upper(),
            }
            mcqs.append(mcq)
            current_pos = match.end()
            
        if not mcqs:
            self.logger.warning(f"AI Agent (Regex Parse): Không thể phân tích bất kỳ MCQ nào bằng regex từ phản hồi (200 ký tự đầu): {str(raw_response)[:200]}...")
        elif len(mcqs) < num_questions_expected:
            self.logger.warning(f"AI Agent (Regex Parse): Đã phân tích {len(mcqs)} MCQ qua regex, nhưng mong đợi {num_questions_expected}.")
        else:
            self.logger.info(f"AI Agent (Regex Parse): Đã phân tích thành công {len(mcqs)} MCQ qua regex.")
            
        return mcqs[:num_questions_expected]

    def _parse_llm_mcq_response(self, raw_response: str, num_questions_expected: int) -> list:
        self.logger.debug(f"AI Agent: Đang cố gắng phân tích phản hồi LLM (300 ký tự đầu): {str(raw_response)[:300]}")
        parsed_mcqs = []

        try:
            json_str_candidate = None
            code_block_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", raw_response, re.DOTALL)
            if code_block_match:
                json_str_candidate = code_block_match.group(1)
                self.logger.debug(f"AI Agent: Tìm thấy mảng JSON trong khối mã: {json_str_candidate[:200]}...")
            else:
                json_start_index = raw_response.find('[')
                json_end_index = raw_response.rfind(']')
                if json_start_index != -1 and json_end_index != -1 and json_start_index < json_end_index:
                    json_str_candidate = raw_response[json_start_index : json_end_index + 1]
                    self.logger.debug(f"AI Agent: Tìm thấy chuỗi JSON tiềm năng (thường): {json_str_candidate[:200]}...")
            
            if json_str_candidate:
                parsed_data = json.loads(json_str_candidate)
                if isinstance(parsed_data, list):
                    valid_mcqs = []
                    for item in parsed_data:
                        if isinstance(item, dict) and \
                           all(k in item for k in ["question", "option_a", "option_b", "option_c", "option_d", "correct_answer_letter"]):
                            valid_mcqs.append(item)
                        else:
                            self.logger.warning(f"AI Agent: Mục JSON không tuân theo cấu trúc MCQ: {str(item)[:100]}")
                    
                    parsed_mcqs = valid_mcqs
                    self.logger.info(f"AI Agent: Đã phân tích thành công {len(parsed_mcqs)} MCQ dưới dạng JSON.")
                    
                    if len(parsed_mcqs) > num_questions_expected:
                        self.logger.warning(f"AI Agent: Phân tích JSON thu được {len(parsed_mcqs)} MCQ, nhiều hơn {num_questions_expected} mong đợi. Đang cắt bớt.")
                        return parsed_mcqs[:num_questions_expected]
                    return parsed_mcqs
                else:
                    self.logger.warning(f"AI Agent: JSON đã phân tích không phải là một danh sách, mà là loại {type(parsed_data)}. Nội dung: {str(parsed_data)[:200]}")
            else:
                self.logger.info("AI Agent: Không thể tìm thấy cấu trúc mảng JSON rõ ràng trong phản hồi để phân tích JSON chính.")

        except json.JSONDecodeError as e:
            error_context_snippet = str(raw_response)
            if json_str_candidate:
                error_context_snippet = json_str_candidate
            
            err_pos = getattr(e, 'pos', None)
            if err_pos is not None:
                 start_snip = max(0, err_pos - 30)
                 end_snip = min(len(error_context_snippet), err_pos + 30)
                 snippet = error_context_snippet[start_snip:end_snip]
                 self.logger.warning(f"AI Agent: Phân tích JSON thất bại. Lỗi: {e}. Gần vị trí {err_pos}. Đoạn mã: ...{snippet}...")
            else:
                 self.logger.warning(f"AI Agent: Phân tích JSON thất bại. Lỗi: {e}. Đoạn phản hồi: {error_context_snippet[:100]}...")

        except Exception as e:
            self.logger.error(f"AI Agent: Lỗi không mong muốn trong quá trình phân tích JSON: {e}. Phản hồi: {str(raw_response)[:200]}")
        
        if not parsed_mcqs:
            self.logger.info("AI Agent: Phân tích JSON chính không mang lại MCQ hoặc thất bại. Chuyển sang phân tích dựa trên regex.")
            parsed_mcqs_regex = self._parse_mcq_via_regex(raw_response, num_questions_expected)
            if parsed_mcqs_regex:
                 self.logger.info(f"AI Agent: Đã phân tích thành công {len(parsed_mcqs_regex)} MCQ bằng phương pháp regex dự phòng.")
                 return parsed_mcqs_regex
            else:
                 self.logger.warning("AI Agent: Phân tích regex dự phòng cũng thất bại trong việc trích xuất MCQ.")
        
        return parsed_mcqs

    def generate_mcqs_basic(self, topic: str, num_questions: int = 5) -> list:
        self.logger.info(f"AI Agent: Đang tạo {num_questions} MCQ cơ bản cho chủ đề: '{topic}'")
        raw_response = self._prompt_llm_for_mcq(topic, num_questions, context_text=None)
        
        if not isinstance(raw_response, str) or "Error:" in raw_response or "Lỗi:" in raw_response:
            self.logger.error(f"AI Agent: Lỗi từ LLM trong quá trình tạo cơ bản: {raw_response}")
            return []
            
        parsed_mcqs = self._parse_llm_mcq_response(raw_response, num_questions_expected=num_questions)
        self.logger.info(f"AI Agent: Đã phân tích {len(parsed_mcqs)} MCQ cơ bản trong số {num_questions} được yêu cầu cho chủ đề '{topic}'.")
        return parsed_mcqs

    def generate_mcqs_with_rag(self, user_topic: str, num_questions: int = 5) -> list:
        self.logger.info(f"AI Agent: Đang tạo {num_questions} MCQ RAG cho chủ đề người dùng: '{user_topic}'")
        
        mapped_topic = KEYWORD_TO_TOPIC_MAP.get(user_topic.lower().strip(), user_topic)
        if mapped_topic != user_topic:
            self.logger.info(f"AI Agent (RAG): Đã ánh xạ chủ đề người dùng '{user_topic}' sang chủ đề chính tắc '{mapped_topic}'.")
        else:
            self.logger.info(f"AI Agent (RAG): Sử dụng trực tiếp chủ đề người dùng làm chủ đề chính tắc: '{mapped_topic}'.")

        context = ""
        if self.kb_index and self.query_embedding_model and self.kb_texts:
            context = self._retrieve_from_kb(mapped_topic, top_k_retrieval=1)
            if context:
                self.logger.info(f"AI Agent (RAG): Đã truy xuất ngữ cảnh cho '{mapped_topic}'. Xem trước (100 ký tự đầu): {context[:100]}...")
            else:
                self.logger.info(f"AI Agent (RAG): Không có ngữ cảnh nào được truy xuất cho '{mapped_topic}'. LLM sẽ sử dụng kiến thức chung của mình cho chủ đề này.")
        else:
            self.logger.warning("AI Agent (RAG): Cơ sở tri thức (KB) hoặc mô hình truy vấn không hoàn toàn khả dụng. Tiếp tục mà không có ngữ cảnh RAG cụ thể.")

        # Prompt RAG mong đợi ngữ cảnh, ngay cả khi nó rỗng, nó sẽ sử dụng kiến thức chung.
        raw_response = self._prompt_llm_for_mcq(mapped_topic, num_questions, context_text=context if context else "Không có ngữ cảnh cụ thể. Sử dụng kiến thức chung.")

        if not isinstance(raw_response, str) or "Error:" in raw_response or "Lỗi:" in raw_response:
            self.logger.error(f"AI Agent: Lỗi từ LLM trong quá trình tạo RAG: {raw_response}")
            return []

        parsed_mcqs = self._parse_llm_mcq_response(raw_response, num_questions_expected=num_questions)
        self.logger.info(f"AI Agent: Đã phân tích {len(parsed_mcqs)} MCQ RAG trong số {num_questions} được yêu cầu cho chủ đề người dùng '{user_topic}'.")
        return parsed_mcqs

# %% [markdown]
# ## 5. Cấu hình Logging (Chạy một lần)
# Cấu hình logging cho notebook.

# %%
# --- Cài đặt Logging ---
logging.basicConfig(
    level=logging.DEBUG, # Đặt thành INFO để ít chi tiết hơn, DEBUG để chi tiết hơn
    format='%(asctime)s - %(levelname)s - %(name)s - %(module)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout) # Đảm bảo log xuất ra output của notebook
    ]
)

# Bạn có thể đặt các cấp độ cụ thể cho các logger khác nhau nếu cần
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

# Lấy một logger cho phần notebook/script hiện tại
notebook_logger = logging.getLogger(__name__) # __name__ sẽ là '__main__' trong script notebook cấp cao nhất
notebook_logger.setLevel(logging.INFO)

# %% [markdown]
# ## 6. Khởi tạo Agent và Kiểm thử
# Phần này tương ứng với khối `if __name__ == '__main__':` trong skript gốc của bạn.

# %%
notebook_logger.info("Khối kiểm thử AI Agent: Đang khởi tạo agent...")
try:
    agent = MainCoreAgent()
    notebook_logger.info("Agent đã được khởi tạo.")

    # --- Trường hợp kiểm thử 1: Tạo MCQ cơ bản (5 câu hỏi) ---
    notebook_logger.info("\n--- Trường hợp kiểm thử 1: Tạo MCQ cơ bản (5 câu hỏi) ---")
    topic_1 = "Present Simple Tense"
    num_q_1 = 5 # Default is now 5
    notebook_logger.info(f"Yêu cầu {num_q_1} MCQ cơ bản cho chủ đề: '{topic_1}'")
    parsed_mcqs_1 = agent.generate_mcqs_basic(topic=topic_1, num_questions=num_q_1)

    print(f"\n--- Các MCQ đã phân tích cho Trường hợp kiểm thử 1 ({topic_1}, {num_q_1} yêu cầu) ---")
    print(json.dumps(parsed_mcqs_1, indent=2, ensure_ascii=False)) # ensure_ascii=False để hiển thị tiếng Việt
    if parsed_mcqs_1 and len(parsed_mcqs_1) == num_q_1:
        notebook_logger.info(f"THÀNH CÔNG: Số lượng MCQ ({len(parsed_mcqs_1)}) đã phân tích chính xác cho Trường hợp kiểm thử 1.")
    else:
        notebook_logger.warning(f"CẢNH BÁO: Mong đợi {num_q_1} MCQ, nhưng đã phân tích {len(parsed_mcqs_1) if parsed_mcqs_1 else 0} cho Trường hợp kiểm thử 1.")

    # --- Trường hợp kiểm thử 2: Tạo MCQ cơ bản (5 câu hỏi) ---
    notebook_logger.info("\n--- Trường hợp kiểm thử 2: Tạo MCQ cơ bản (5 câu hỏi) ---")
    topic_2 = "Past Continuous Tense"
    num_q_2 = 5
    notebook_logger.info(f"Yêu cầu {num_q_2} MCQ cơ bản cho chủ đề: '{topic_2}'")
    parsed_mcqs_2 = agent.generate_mcqs_basic(topic=topic_2, num_questions=num_q_2)

    print(f"\n--- Các MCQ đã phân tích cho Trường hợp kiểm thử 2 ({topic_2}, {num_q_2} yêu cầu) ---")
    print(json.dumps(parsed_mcqs_2, indent=2, ensure_ascii=False))
    if parsed_mcqs_2 and len(parsed_mcqs_2) == num_q_2:
        notebook_logger.info(f"THÀNH CÔNG: Số lượng MCQ ({len(parsed_mcqs_2)}) đã phân tích chính xác cho Trường hợp kiểm thử 2.")
    else:
        notebook_logger.warning(f"CẢNH BÁO: Mong đợi {num_q_2} MCQ, nhưng đã phân tích {len(parsed_mcqs_2) if parsed_mcqs_2 else 0} cho Trường hợp kiểm thử 2.")

    # --- Trường hợp kiểm thử 3: Tạo MCQ RAG (5 câu hỏi) ---
    notebook_logger.info("\n--- Trường hợp kiểm thử 3: Tạo MCQ RAG (5 câu hỏi) ---")
    topic_3_user = "past simple" # Nên ánh xạ tới "past simple tense"
    num_q_3 = 5
    notebook_logger.info(f"Yêu cầu {num_q_3} MCQ RAG cho chủ đề người dùng: '{topic_3_user}'")
    parsed_mcqs_3 = agent.generate_mcqs_with_rag(user_topic=topic_3_user, num_questions=num_q_3)

    print(f"\n--- Các MCQ đã phân tích cho Trường hợp kiểm thử 3 (Chủ đề người dùng: '{topic_3_user}', {num_q_3} yêu cầu) ---")
    print(json.dumps(parsed_mcqs_3, indent=2, ensure_ascii=False))
    if parsed_mcqs_3 and len(parsed_mcqs_3) == num_q_3:
        notebook_logger.info(f"THÀNH CÔNG: Số lượng MCQ ({len(parsed_mcqs_3)}) đã phân tích chính xác cho Trường hợp kiểm thử 3.")
    else:
        notebook_logger.warning(f"CẢNH BÁO: Mong đợi {num_q_3} MCQ, nhưng đã phân tích {len(parsed_mcqs_3) if parsed_mcqs_3 else 0} cho Trường hợp kiểm thử 3.")

    # --- Trường hợp kiểm thử 4: Tạo MCQ RAG (chủ đề chung, 5 câu hỏi) ---
    notebook_logger.info("\n--- Trường hợp kiểm thử 4: Tạo MCQ RAG (5 câu hỏi, chủ đề chung) ---")
    topic_4_user = "General English Idioms"
    num_q_4 = 5
    notebook_logger.info(f"Yêu cầu {num_q_4} MCQ RAG cho chủ đề người dùng: '{topic_4_user}'")
    parsed_mcqs_4 = agent.generate_mcqs_with_rag(user_topic=topic_4_user, num_questions=num_q_4)

    print(f"\n--- Các MCQ đã phân tích cho Trường hợp kiểm thử 4 (Chủ đề người dùng: '{topic_4_user}', {num_q_4} yêu cầu) ---")
    print(json.dumps(parsed_mcqs_4, indent=2, ensure_ascii=False))
    if parsed_mcqs_4 and len(parsed_mcqs_4) == num_q_4:
        notebook_logger.info(f"THÀNH CÔNG: Số lượng MCQ ({len(parsed_mcqs_4)}) đã phân tích chính xác cho Trường hợp kiểm thử 4.")
    else:
        notebook_logger.warning(f"CẢNH BÁO: Mong đợi {num_q_4} MCQ, nhưng đã phân tích {len(parsed_mcqs_4) if parsed_mcqs_4 else 0} cho Trường hợp kiểm thử 4.")

    # Retry MCQ generation with a simpler prompt if parsing fails (default: 5 questions)
    notebook_logger.info("\n--- MCQ JSON Retry Demo: If parsing fails, try a simpler prompt (default 5 questions) ---")
    user_topic = "General English Idioms"
    num_questions = 5  # Default is now 5
    parsed_mcqs = agent.generate_mcqs_with_rag(user_topic=user_topic, num_questions=num_questions)

    if not parsed_mcqs or len(parsed_mcqs) != num_questions:
        notebook_logger.warning("MCQ parsing failed on first try. Retrying with a minimal prompt...")
        # Minimal prompt: ask for a JSON array of MCQs, no context, no formatting rules
        minimal_prompt = f"""
You are an AI that generates English MCQs. Output a JSON array of {num_questions} objects. Each object must have: question, option_a, option_b, option_c, option_d, correct_answer_letter (A/B/C/D). Topic: {user_topic}.
"""
        raw_response = query_gemma_gguf(
            prompt=minimal_prompt,
            max_tokens=1024,
            temperature=0.5
        )
        try:
            parsed_mcqs = json.loads(raw_response)
            notebook_logger.info(f"Retry succeeded: Parsed {len(parsed_mcqs)} MCQs from minimal prompt.")
        except Exception as e:
            notebook_logger.error(f"Retry failed: Could not parse MCQs from minimal prompt. Error: {e}")
            parsed_mcqs = []

    print(f"\n--- MCQ JSON Retry Result for topic '{user_topic}' (default 5 questions) ---")
    print(json.dumps(parsed_mcqs, indent=2, ensure_ascii=False))

    # --- Strict JSON-only MCQ generation with improved prompt and model suggestion ---
    notebook_logger.info("\n--- Strict JSON-only MCQ generation with improved prompt and model suggestion ---")
    user_topic = "General English Idioms"
    num_questions = 5
    notebook_logger.info(f"Generating {num_questions} MCQs for topic: '{user_topic}' with strict JSON prompt.")

    strict_json_prompt = (
        f"Output ONLY a valid JSON array of {num_questions} MCQ objects. "
        "Each object must have: question, option_a, option_b, option_c, option_d, correct_answer_letter (A/B/C/D). "
        "No explanation, no extra text. "
        f"Topic: {user_topic}"
    )

    raw_response = query_gemma_gguf(
        prompt=strict_json_prompt,
        max_tokens=1024,
        temperature=0.5
    )
    try:
        parsed_mcqs = json.loads(raw_response)
        notebook_logger.info(f"Strict prompt succeeded: Parsed {len(parsed_mcqs)} MCQs.")
    except Exception as e:
        notebook_logger.error(f"Strict prompt failed: {e}")
        parsed_mcqs = []

    print(f"\n--- Strict JSON MCQ Result for topic '{user_topic}' ---")
    print(json.dumps(parsed_mcqs, indent=2, ensure_ascii=False))

    # NOTE: For best RAG/semantic search, set embedding model to 'all-mpnet-base-v2' in MainCoreAgent.

except Exception as e:
    notebook_logger.critical(f"Đã xảy ra lỗi trong quá trình khởi tạo agent hoặc kiểm thử: {e}", exc_info=True)

finally:
    notebook_logger.info("\nHoàn tất Khối kiểm thử AI Agent.")

# %% [markdown]
# # MCQ Generation/Parsing Issue: Debugging Notes
# 
# The notebook's MCQ generation and parsing logic is running, but the LLM responses for some test cases (especially RAG-based MCQs) are not in the expected JSON or regex-parsable format. This results in empty or failed MCQ extraction for those cases.
# 
# **Observed Problems:**
# - The LLM sometimes returns garbled or irrelevant text instead of a valid JSON array or MCQ block.
# - The fallback regex parser also fails when the LLM output is not close to the expected format.
# 
# **Suggested Next Steps:**
# 1. **Check LLM Prompting:**
#    - Ensure the prompt sent to the LLM is clear, concise, and strictly enforces the output format (JSON array or MCQ block).
#    - Consider simplifying or shortening the prompt if the model context window is exceeded.
# 2. **Improve LLM Output Validation:**
#    - Add more robust post-processing to detect and recover from malformed outputs.
#    - Optionally, retry the LLM call with a simpler prompt if parsing fails.
# 3. **Model/Service Quality:**
#    - If using a local or quantized LLM, try a higher-quality or larger model for better output reliability.
#    - Check for any service-side errors or resource constraints.
# 4. **Manual Fallback:**
#    - If automated parsing fails, consider logging the raw LLM output for manual review and prompt engineering.
# 
# ---
# 
# _This cell was added automatically to help guide further debugging and improvement of the MCQ generation pipeline._