import uuid
import ast
import os
import pandas as pd
from typing import Dict, List, Optional
from ollama import Client  # ✅ Dùng Client thay vì chat()

PROMPT_TEMPLATE = "ollama_prompt.txt"
DATABASE = "database.csv"
MODEL = "llama3.2:3b"


class Session:
    def __init__(self, session_id: Optional[str] = None) -> None:
        self.session_id = session_id or str(uuid.uuid4())
        self.history: List[Dict[str, str]] = []
        self.system_context = ""

    def add_session(self, role: str, content: str):
        self.history.append({'role': role, 'content': content})

    def get_context_history(self, max_history: int = 20) -> List[Dict]:
        if self.system_context:
            history = [{'role': 'system', 'content': self.system_context}]
            history.extend(self.history[-max_history:])
            return history
        return self.history[-max_history:]

    def set_system_context(self, context: str):
        self.system_context = context


class AnalysisManager:
    def __init__(self) -> None:
        self.data = self._load_data()
        self.categories = self.data.category.unique().tolist()
        self.sessions: Dict[str, Session] = {}

        # ✅ Tạo client Ollama, cho phép đọc từ ENV nếu bạn deploy
        host = os.getenv("OLLAMA_API_BASE_URL", "http://host.docker.internal:11434/")
        self.client = Client(host=host)

    def _load_data(self) -> pd.DataFrame:
        try:
            return pd.read_csv(DATABASE)
        except FileNotFoundError:
            raise FileNotFoundError(f"Database file '{DATABASE}' not found.")

    def _load_system_prompt(self) -> str:
        try:
            with open(PROMPT_TEMPLATE, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError("System prompt file 'ollama_prompt.txt' not found.")

    def get_or_create_session(self, session_id: Optional[str] = None):
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        new_session = Session(session_id)
        self.sessions[new_session.session_id] = new_session
        return new_session

    def clear_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def _analytical_model(self, session: Session, user_content: str, system_content: Optional[str] = None) -> str:
        if system_content:
            session.set_system_context(system_content)

        session.add_session('user', user_content)
        chat_history = session.get_context_history()
        final_response = ""

        # ✅ Dùng self.client.chat() thay vì chat()
        stream = self.client.chat(
            model=MODEL,
            messages=chat_history,
            stream=True
        )

        for partial in stream:
            if "message" in partial and "content" in partial["message"]:
                final_response += partial["message"]["content"]

        session.add_session('assistant', final_response)
        return final_response

    def _model_response(self, question: str, session_id: Optional[str] = None) -> tuple:
        try:
            session = self.get_or_create_session(session_id)
            base_system_prompt = self._load_system_prompt()
            user_prompt = f"User question: {question}\n\nAvailable categories:\n" + "\n".join(self.categories)
            response = self._analytical_model(session, user_prompt, base_system_prompt)

            # ✅ Chuyển chuỗi AI trả về thành dict (nếu AI format chuẩn)
            try:
                parsed = ast.literal_eval(response)
                if isinstance(parsed, dict):
                    return (self.search_products(parsed), session.session_id)
            except Exception:
                pass  # fallback nếu không parse được

            # Nếu không parse được hoặc không hợp lệ
            return (f"Error occurred: Invalid AI response format -> {response}", session.session_id)

        except Exception as e:
            if not session_id:
                session = self.get_or_create_session()
                session_id = session.session_id
            return (f"Error occurred while processing your form: {str(e)}", session_id)

    def search_products(self, filter_dict: dict) -> List[dict]:
        mask = pd.Series([True] * len(self.data))
        if 'category' in filter_dict:
            mask &= self.data['category'] == filter_dict['category']
        if 'sex' in filter_dict:
            mask &= self.data['sex'] == filter_dict['sex']
        if 'min_price' in filter_dict:
            mask &= self.data['price'] >= filter_dict['min_price']
        if 'max_price' in filter_dict:
            mask &= self.data['price'] <= filter_dict['max_price']
        filtered = self.data[mask].reset_index(drop=True)
        return filtered.to_dict('records') if not filtered.empty else []

    def get_all_products(self, question, session_id):
        return self._model_response(question, session_id)
def handle_question(analysis_manager: AnalysisManager, prompt) -> dict:
    try:
        question_data = prompt.question.strip()
        if not question_data:
            fallback_products = analysis_manager.search_products({})
            return {
                "status": "empty_prompt_fallback",
                "prompt": question_data,
                "note": "Prompt trống. Đã trả về toàn bộ sản phẩm.",
                "products": fallback_products
            }
        response = analysis_manager.get_all_products(question_data, prompt.session_id)
        return {
            "status": "success",
            "prompt": question_data,
            "response": response
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }