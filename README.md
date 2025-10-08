# Product AI API

API sử dụng AI (Ollama) để xử lý và lọc sản phẩm theo yêu cầu của người dùng.

## Đặc điểm chính

- Sử dụng AI model (llama3.2:3b) để hiểu và xử lý câu hỏi của user
- Tự động lọc và trả về sản phẩm phù hợp với yêu cầu
- API đơn giản chỉ với 1 endpoint chính

## Cài đặt

1. Cài đặt dependencies:
```bash
pip install -r requirements.txt
```

2. Đảm bảo Ollama đã được cài đặt và model llama3.2:3b available

3. Chạy API:
```bash
python API.py
```

## Endpoint

### GET `/products`

Xử lý câu hỏi/yêu cầu của user qua AI và trả về sản phẩm phù hợp.

**Parameters:**
- `question` (query parameter): Câu hỏi hoặc yêu cầu của bạn

**Ví dụ sử dụng:**

```
GET /products
GET /products?question={"gift_recipient": "bố", "sex": "nam", "occasion": "sinh nhật", "Preferences": "áo", "budget": "500.000"}
```

**Response:**
```json
{
    "status": "success",
    "question": "Tôi muốn tìm áo sơ mi nam giá rẻ",
    "session_id": "abc123...",
    "total_products": 5,
    "products": [
        {
            "product_id": 1,
            "category": "shirt",
            "product_name": "Áo Sơ Mi Nam",
            "brand": "Canifa",
            "price": 249000,
            "stock": 80,
            "rating": 4.7,
            "num_reviews": 21,
            "description": "Kiểu dáng thanh lịch, dễ phối",
            "sex": "male"
        }
    ]
}
```

## Cách hoạt động

1. User gửi câu hỏi qua parameter `question`
2. AI model phân tích câu hỏi và hiểu ý định
3. Tạo filter criteria phù hợp (category, sex, price range, etc.)
4. Lọc sản phẩm từ database theo criteria
5. Trả về kết quả đã được lọc

## Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Files

- `API.py` - FastAPI main file
- `AnalysisManager.py` - AI processing logic
- `database.csv` - Product database
- `ollama_prompt.txt` - AI system prompt