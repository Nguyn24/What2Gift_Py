import uuid
import ast
import os
import pandas as pd
import requests
import json
from typing import Dict, List, Optional

PROMPT_TEMPLATE = "huggingface_prompt.txt"
DATABASE = "database.csv"
# Hugging Face model - sử dụng model miễn phí không cần auth
MODEL = "gpt2"
HF_API_URL = "https://api-inference.huggingface.co/models/gpt2"


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

        # ✅ Tạo Hugging Face API client
        self.hf_token = os.getenv("HUGGINGFACE_API_TOKEN", None)
        try:
            # Test Hugging Face API connection
            if self.hf_token:
                headers = {"Authorization": f"Bearer {self.hf_token}"}
                response = requests.get("https://api-inference.huggingface.co/models", headers=headers)
                if response.status_code == 200:
                    self.hf_available = True
                    print("Hugging Face API connected successfully")
                else:
                    self.hf_available = False
                    print(f"Hugging Face API error: {response.status_code}")
            else:
                # Try without token (limited free tier)
                self.hf_available = True
                print("Using Hugging Face API without token (limited)")
        except Exception as e:
            print(f"Hugging Face API not available: {e}")
            self.hf_available = False

    def _load_data(self) -> pd.DataFrame:
        try:
            return pd.read_csv(DATABASE)
        except FileNotFoundError:
            raise FileNotFoundError(f"Database file '{DATABASE}' not found.")

    def _load_system_prompt(self) -> str:
        try:
            with open(PROMPT_TEMPLATE, 'r', encoding='utf-8') as file:
                prompt = file.read().strip()
                
            # Inject actual database categories into prompt
            categories_list = ", ".join([f"'{cat}'" for cat in self.categories])
            prompt = prompt.replace("Available categories:\n" + "\n".join(self.categories), 
                                  f"Available categories: {categories_list}")
            
            return prompt
        except FileNotFoundError:
            raise FileNotFoundError("System prompt file 'huggingface_prompt.txt' not found.")

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
        if not self.hf_available:
            raise Exception("Hugging Face API is not available")
            
        if system_content:
            session.set_system_context(system_content)

        session.add_session('user', user_content)
        
        # Tạo prompt tối ưu cho Hugging Face API
        full_prompt = f"{system_content}\n\nUser Request: {user_content}\nAssistant Response:"
        
        # Gọi Hugging Face API với parameters tối ưu
        headers = {}
        if self.hf_token:
            headers["Authorization"] = f"Bearer {self.hf_token}"
        
        payload = {
            "inputs": full_prompt,
            "parameters": {
                "max_length": 150,
                "temperature": 0.3,  # Lower temperature for more consistent output
                "do_sample": True,
                "return_full_text": False,
                "top_p": 0.9,
                "repetition_penalty": 1.1,
                "pad_token_id": 50256  # GPT-2 pad token
            }
        }
        
        try:
            response = requests.post(HF_API_URL, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    generated_text = result[0].get("generated_text", "")
                    # Clean up the response to extract only the dictionary
                    final_response = self._extract_dict_from_response(generated_text)
                else:
                    final_response = str(result)
            else:
                raise Exception(f"Hugging Face API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            raise Exception(f"Error calling Hugging Face API: {str(e)}")

        session.add_session('assistant', final_response)
        return final_response

    def _extract_dict_from_response(self, text: str) -> str:
        """
        Extract Python dictionary from Hugging Face response
        """
        import re
        
        # Look for dictionary pattern in the response
        dict_pattern = r'\{[^}]*\}'
        matches = re.findall(dict_pattern, text)
        
        if matches:
            # Return the first valid dictionary found
            return matches[0]
        
        # If no dictionary found, try to clean the text
        cleaned = text.strip()
        
        # Remove common prefixes/suffixes
        prefixes_to_remove = [
            "Assistant Response:",
            "Response:",
            "Answer:",
            "Output:",
            "Result:"
        ]
        
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        
        return cleaned

    def _rule_based_filtering_from_database(self, question_data: dict) -> dict:
        """
        Rule-based filtering dựa trên database thực tế - FALLBACK MIỄN PHÍ
        """
        filter_dict = {}
        
        # Map Vietnamese to database categories
        category_mapping = {
            'áo sơ mi': 'shirt', 'áo thun': 'shirt', 'áo polo': 'shirt',
            'quần jeans': 'pants', 'quần tây': 'pants', 'quần jogger': 'pants',
            'váy': 'dress', 'đầm': 'dress',
            'áo khoác': 'jacket', 'áo bomber': 'jacket', 'áo dù': 'jacket',
            'áo hoodie': 'hoodie', 'áo nỉ': 'hoodie',
            'quần short': 'shorts', 'quần đùi': 'shorts',
            'áo len': 'sweater', 'áo cardigan': 'sweater',
            'quần legging': 'leggings', 'quần bó': 'leggings',
            'áo vest': 'vest', 'áo gile': 'vest',
            'đồng hồ': 'watch',
            'ví': 'wallet', 'ví da': 'wallet',
            'túi xách': 'bag', 'balo': 'bag', 'cặp': 'bag',
            'giày': 'shoes', 'dép': 'shoes', 'sandal': 'shoes',
            'mũ': 'hat', 'nón': 'hat',
            'phụ kiện': 'accessory', 'đồ phụ kiện': 'accessory',
            'thắt lưng': 'belt', 'dây nịt': 'belt',
            'khăn': 'scarf', 'khăn quàng': 'scarf',
            'tất': 'socks', 'vớ': 'socks',
            'kính': 'glasses', 'mắt kính': 'glasses',
            'nước hoa': 'perfume', 'perfume': 'perfume'
        }
        
        # Extract category from preferences
        if 'preferences' in question_data and question_data['preferences']:
            pref = question_data['preferences'].lower()
            for viet, eng in category_mapping.items():
                if viet in pref:
                    filter_dict['category'] = eng
                    break
        
        # Map gender
        if 'sex' in question_data:
            sex = question_data['sex'].lower()
            if sex in ['nam', 'male']:
                filter_dict['sex'] = 'male'
            elif sex in ['nữ', 'female']:
                filter_dict['sex'] = 'female'
            else:
                filter_dict['sex'] = 'unisex'
        
        # Parse budget based on database price range (69k - 7.99M)
        if 'budget' in question_data and question_data['budget']:
            try:
                budget_str = question_data['budget'].replace('.', '').replace(',', '').replace('đ', '').replace('vnd', '').strip()
                budget = int(budget_str)
                
                # Smart price ranges based on database
                if budget < 200000:
                    filter_dict['min_price'] = 69000
                    filter_dict['max_price'] = 200000
                elif budget < 500000:
                    filter_dict['min_price'] = int(budget * 0.5)
                    filter_dict['max_price'] = int(budget * 1.2)
                elif budget < 1000000:
                    filter_dict['min_price'] = int(budget * 0.6)
                    filter_dict['max_price'] = int(budget * 1.3)
                elif budget < 3000000:
                    filter_dict['min_price'] = int(budget * 0.7)
                    filter_dict['max_price'] = int(budget * 1.4)
                else:
                    filter_dict['min_price'] = int(budget * 0.8)
                    filter_dict['max_price'] = 7990000
            except:
                filter_dict['min_price'] = 69000
                filter_dict['max_price'] = 500000
        
        return filter_dict

    def _model_response(self, question: str, session_id: Optional[str] = None) -> tuple:
        try:
            session = self.get_or_create_session(session_id)
            
            # Try Hugging Face API first if available
            if self.hf_available:
                try:
                    base_system_prompt = self._load_system_prompt()
                    user_prompt = f"User question: {question}\n\nAvailable categories: {', '.join(self.categories)}"
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
                    # AI failed, fallback to rule-based
                    pass
            
            # Fallback to rule-based filtering (MIỄN PHÍ)
            if isinstance(question, dict):
                filter_dict = self._rule_based_filtering_from_database(question)
                products = self.search_products(filter_dict)
                return (products, session.session_id)
            else:
                # If question is string, return all products
                return (self.search_products({}), session.session_id)

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