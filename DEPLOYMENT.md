# Hướng dẫn Deploy lên Render - SỬ DỤNG HUGGING FACE API

## Vấn đề đã fix

Lỗi `[Errno -2] Name or service not known` xảy ra vì:
- Ollama server không available trên Render
- URL `host.docker.internal:11434` không hoạt động trên production

## Giải pháp đã implement

### 1. Thay thế Ollama bằng Hugging Face API
- **MIỄN PHÍ**: 30,000 requests/tháng
- **Không cần server riêng**
- **Hoạt động ngay trên Render**

### 2. Cải thiện Error Handling
- Kiểm tra Hugging Face API availability
- Fallback graceful khi API không available
- Error messages tiếng Việt rõ ràng

### 3. Environment Configuration
- Sử dụng `HUGGINGFACE_API_TOKEN` environment variable (optional)
- Hoạt động không cần token (limited free tier)

## Cách deploy với Hugging Face API

### ✅ Khuyến nghị: Sử dụng Hugging Face API (MIỄN PHÍ)

### Cách deploy:

1. **Push code lên GitHub**
2. **Connect repository với Render**
3. **Set environment variables** (optional):
   - `HUGGINGFACE_API_TOKEN`: Token từ Hugging Face (để tăng limit)
   - `PYTHON_VERSION`: 3.11.0
4. **Deploy ngay** - không cần cấu hình gì thêm!

### Lấy Hugging Face API Token (optional):

1. Đăng ký tài khoản tại [huggingface.co](https://huggingface.co)
2. Vào Settings > Access Tokens
3. Tạo token mới
4. Set environment variable trên Render: `HUGGINGFACE_API_TOKEN=your_token_here`

**Lưu ý**: Không cần token vẫn hoạt động được (limited free tier)

## Test deployment

Sau khi deploy, test endpoint:
```bash
curl -X POST "https://your-app.onrender.com/products" \
  -H "Content-Type: application/json" \
  -d '{
    "gift_recipient": "bố",
    "sex": "nam", 
    "occasion": "sinh nhật",
    "Preferences": "accessory",
    "budget": "500.000"
  }'
```

## Fallback behavior

Nếu Ollama không available, API sẽ:
- Trả về status `ai_prompt_error_fallback`
- Note: "AI không hiểu hoặc prompt sai. Đã trả về toàn bộ sản phẩm."
- Trả về tất cả sản phẩm (fallback)
