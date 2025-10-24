from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional
import uvicorn
from AnalysisManager import AnalysisManager

# Khởi tạo FastAPI app
app = FastAPI(
    title="Product API",
    description="API để lấy tất cả sản phẩm",
    version="1.0.0"
)

# Thêm CORS middleware
origins = [
    "http://localhost:5173",  # local FE khi dev
    "https://corvus-fe.vercel.app",  # ✅ FE đã deploy trên Vercel
    "https://what2gift-api.onrender.com/swagger/index.html",  # backend chính
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
        "description": "API sử dụng Hugging Face AI để xử lý và lọc sản phẩm theo yêu cầu",
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
    """
    try:
        # Chuyển JSON sang dict để truyền cho AI
        question_data = prompt.dict()

        # Gọi AI model
        products, session_id = analysis_manager.get_all_products(question_data, None)

        # Nếu AI trả về lỗi
        if isinstance(products, str):
            if "Error occurred" in products:
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

        # Nếu AI không tìm thấy sản phẩm
        if isinstance(products, list) and len(products) == 0:
            # Try rule-based filtering as fallback instead of returning all products
            filter_dict = analysis_manager._rule_based_filtering_from_database(question_data)
            fallback_products = analysis_manager.search_products(filter_dict)
            
            if len(fallback_products) == 0:
                # If still no products, return all products as last resort
                fallback_products = analysis_manager.search_products({})
                note = "No products matched criteria, returned all products"
            else:
                note = "AI found no products, used rule-based filtering"
            
            return {
                "status": "success_with_fallback",
                "prompt": question_data,
                "session_id": session_id,
                "note": note,
                "total_products": len(fallback_products),
                "products": fallback_products[:50]
            }

        return {
            "status": "success",
            "prompt": question_data,
            "session_id": session_id,
            "total_products": len(products) if isinstance(products, list) else 0,
            "products": products
        }

    except Exception as e:
        try:
            fallback_products = analysis_manager.search_products({})
            return {
                "status": "error_with_fallback",
                "prompt": prompt.dict(),
                "error": str(e),
                "note": "Returned all products due to error",
                "total_products": len(fallback_products),
                "products": fallback_products[:20]
            }
        except:
            raise HTTPException(status_code=500, detail=f"Critical error: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "API:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
