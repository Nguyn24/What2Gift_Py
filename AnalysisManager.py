import uuid
import ast
import pandas as pd
from typing import Dict, List, Optional
from ollama import chat  # type: ignore


PROMPT_TEMPLATE = "ollama_prompt.txt"
DATABASE = "database.csv"
MODEL = "llama3.2:3b"


class Session:
    def __init__(self, session_id: Optional[str] = None) -> None:
        self.session_id = session_id or str(uuid.uuid4())
        self.history: List[Dict[str, str]] = []
        self.system_context = ""

    def add_session(self, role: str, content: str):
        """Add a message to chat history"""
        self.history.append({
            'role': role,
            'content': content
        })

    def get_context_history(self, max_history: int = 20) -> List[Dict]:
        """Get recent chat history for context"""
        if self.system_context:
            history = [{'role': 'system', 'content': self.system_context}]
            recent_messages = self.history[-max_history:]
            history.extend(recent_messages)
            return history
        return self.history[-max_history:]

    def set_system_context(self, context: str):
        """Set or update system context"""
        self.system_context = context


class AnalysisManager:
    def __init__(self) -> None:
        self.data = self._load_data()
        self.categories = self.data.category.unique().tolist()
        self.sessions: Dict[str, Session] = {}

    def _load_data(self) -> pd.DataFrame:
        """Load dataset from CSV file"""
        try:
            data = pd.read_csv(DATABASE)
            return data
        except FileNotFoundError:
            raise FileNotFoundError(f"Database file '{DATABASE}' not found.")

    def _load_system_prompt(self) -> str:
        """Load system prompt from ollama_prompt.txt file"""
        try:
            prompt = PROMPT_TEMPLATE

            with open(str(prompt), 'r', encoding='utf-8') as file:
                return file.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(
                "System prompt file 'ollama_prompt.txt' not found."
            )

    def get_or_create_session(self, session_id: Optional[str] = None):
        """Get existing session or create new one"""
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]

        new_session = Session(session_id)
        self.sessions[new_session.session_id] = new_session
        return new_session

    def clear_session(self, session_id: str) -> bool:
        """Clear a specific session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def _analytical_model(
        self,
        session: Session,
        user_content: str,
        system_content: Optional[str] = None
    ) -> str:
        if system_content:
            session.set_system_context(system_content)

        session.add_session('user', user_content)

        chat_history = session.get_context_history()

        final_response = ""
        for partial in chat(
            model=MODEL,
            messages=chat_history,
            stream=True
        ):
            if partial.message.content is not None:
                final_response += partial.message.content

        session.add_session('assistant', final_response)
        return final_response

    def _model_response(
        self,
        question: str,
        session_id: Optional[str] = None
    ) -> tuple:
        """Main response function using ollama with session support"""
        try:
            session = self.get_or_create_session(session_id)

            base_system_prompt = self._load_system_prompt()

            user_prompt = (
                f"User question: {question}\n\n"
                "Available categories:\n" + "\n".join(self.categories)
            )

            response = self._analytical_model(
                session, user_prompt, base_system_prompt
            )
            return (
                self.search_products(ast.literal_eval(response)),
                session.session_id
            )

        except Exception as e:
            if not session_id:
                session = self.get_or_create_session()
                session_id = session.session_id
            return (
                "Error occurred while processing your form: "
                f"{str(e)}"
            ), session_id

    def search_products(self, filter_dict: dict) -> List[dict]:
        """
        Search for products based on filter criteria

        Args:
            filter_dict: Dictionary containing filter criteria:
                - category: str - Product category
                - sex: str - Gender filter (male/female/unisex)
                - min_price: float - Minimum price
                - max_price: float - Maximum price

        Returns:
            List[dict]: List of products matching the criteria
        """

        mask = pd.Series([True] * len(self.data))

        category = filter_dict.get("category")
        sex = filter_dict.get("sex")
        min_price = filter_dict.get("min_price")
        max_price = filter_dict.get("max_price")

        if category is not None:
            mask &= self.data['category'] == category
        if sex is not None:
            mask &= self.data['sex'] == sex
        if min_price is not None:
            mask &= self.data['price'] >= min_price
        if max_price is not None:
            mask &= self.data['price'] <= max_price

        filtered_data = self.data[mask].reset_index(drop=True)

        if not filtered_data.empty:
            return filtered_data.to_dict('records')
        return []

    def get_all_products(self, question, session_id):
        """
        Get all products in the database

        Args:
            question: str - User question (not used here)
            session_id: Optional[str] - Session ID (not used here)
        Returns:
            Tuple[List[dict], str]: List of all products and session ID
        """
        return self._model_response(question, session_id)
