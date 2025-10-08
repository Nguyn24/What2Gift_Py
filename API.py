from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional
import uvicorn
from AnalysisManager import AnalysisManager
import os
# Khởi tạo FastAPI app
app = FastAPI(
    title="Product API",
    description="API để lấy tất cả sản phẩm",
    version="1.0.0"
)

# Thêm CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo AnalysisManager
analysis_manager = AnalysisManager()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Product AI API",
        "version": "1.0.0",
        "description": "API sử dụng AI để xử lý và lọc sản phẩm theo yêu cầu",
        "endpoints": {
            "/products": "Lấy sản phẩm đã được AI xử lý theo yêu cầu JSON",
            "/docs": "API Documentation"
        },
        "example_usage": {
            "url": "/products",
            "method": "POST",
            "example_body": {
                "gift_recipient": "bố",
                "sex": "nam",
                "occasion": "sinh nhật",
                "Preferences": "phụ kiện",
                "budget": "500.000"
            }
        }
    }


# 🧩 Định nghĩa model cho prompt JSON
class GiftPrompt(BaseModel):
    gift_recipient: str
    sex: str
    occasion: str
    Preferences: Optional[str] = None
    budget: Optional[str] = None


@app.post("/products", response_model=Dict)
async def get_all_products(prompt: GiftPrompt):
    """
    Lấy sản phẩm đã được xử lý qua AI model
    Nếu prompt sai, thiếu dữ liệu hoặc AI không hiểu -> trả về toàn bộ sản phẩm
    """
    try:
        # Chuyển JSON sang dict để truyền cho AI
        question_data = prompt.dict()

        # ✅ Kiểm tra prompt có bị trống hoặc thiếu thông tin quan trọng không
        required_fields = ["gift_recipient", "sex", "occasion"]
        if any(not question_data.get(f) for f in required_fields):
            fallback_products = analysis_manager.search_products({})
            return {
                "status": "invalid_prompt_fallback",
                "prompt": question_data,
                "note": "Thiếu thông tin bắt buộc trong prompt. Đã trả về toàn bộ sản phẩm.",
                "total_products": len(fallback_products),
                "products": fallback_products[:20]
            }

        # ✅ Gọi AI model
        products, session_id = analysis_manager.get_all_products(question_data, None)

        # ✅ Nếu AI trả về lỗi hoặc không hiểu prompt
        if isinstance(products, str):
            if "Error occurred" in products or "invalid" in products.lower() or "prompt" in products.lower():
                fallback_products = analysis_manager.search_products({})
                return {
                    "status": "ai_prompt_error_fallback",
                    "prompt": question_data,
                    "session_id": session_id,
                    "note": "AI không hiểu hoặc prompt sai. Đã trả về toàn bộ sản phẩm.",
                    "error_detail": products,
                    "total_products": len(fallback_products),
                    "products": fallback_products[:20]
                }
            else:
                raise HTTPException(status_code=500, detail=products)

        # ✅ Nếu AI không tìm thấy sản phẩm
        if isinstance(products, list) and len(products) == 0:
            fallback_products = analysis_manager.search_products({})
            return {
                "status": "no_match_fallback",
                "prompt": question_data,
                "session_id": session_id,
                "note": "Không có sản phẩm phù hợp hoặc prompt quá chung chung. Đã trả về toàn bộ sản phẩm.",
                "total_products": len(fallback_products),
                "products": fallback_products[:50]
            }

        # ✅ Trường hợp thành công
        return {
            "status": "success",
            "prompt": question_data,
            "session_id": session_id,
            "total_products": len(products) if isinstance(products, list) else 0,
            "products": products
        }

    except Exception as e:
        # ✅ Fallback cuối cùng nếu có lỗi bất ngờ
        try:
            fallback_products = analysis_manager.search_products({})
            return {
                "status": "error_with_fallback",
                "prompt": prompt.dict(),
                "error": str(e),
                "note": "Đã xảy ra lỗi, trả về toàn bộ sản phẩm.",
                "total_products": len(fallback_products),
                "products": fallback_products[:20]
            }
        except:
            raise HTTPException(status_code=500, detail=f"Critical error: {str(e)}")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))  # <-- dùng PORT do Render cấp
    uvicorn.run(app, host="0.0.0.0", port=port)