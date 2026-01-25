import pandas as pd
import joblib
import json
import os

def load_resources(model_dir='.'):
    """
    Hàm tải mô hình và cấu hình (Load Model & Config).
    Nên gọi hàm này 1 lần khi khởi động ứng dụng.
    """
    # Định nghĩa đường dẫn file
    files = {
        'model': os.path.join(model_dir, 'xgboost_salinity_model.pkl'),
        'features': os.path.join(model_dir, 'model_features.json'),
        'thresholds': os.path.join(model_dir, 'salinity_thresholds.json')
    }

    # Kiểm tra file tồn tại
    for name, path in files.items():
        if not os.path.exists(path):
            raise FileNotFoundError(f"❌ Thiếu file quan trọng: {path}. Hãy chạy train_model.py trước.")

    # Tải dữ liệu
    print("⏳ Đang tải mô hình XGBoost và cấu hình...")
    model = joblib.load(files['model'])
    
    with open(files['features'], 'r', encoding='utf-8') as f:
        feature_names = json.load(f)['feature_names']
        
    with open(files['thresholds'], 'r', encoding='utf-8') as f:
        # Lấy ngưỡng tứ phân vị đã lưu
        thresholds = json.load(f)['quartile_based']
    
    print("✅ Đã tải xong resources!")
    return {
        'model': model,
        'feature_names': feature_names,
        'thresholds': thresholds
    }

def predict_salinity(input_data, resources):
    """
    Hàm dự báo độ mặn cho 1 điểm dữ liệu.
    
    Args:
        input_data (dict): Dictionary chứa các biến đầu vào.
                           VD: {'temp_dry_mean_dry': 30, 'dem_mean': 5, ...}
        resources (dict):  Biến trả về từ hàm load_resources() bên trên.
        
    Returns:
        dict: Kết quả gồm giá trị dự báo, mức độ và màu sắc.
    """
    model = resources['model']
    features = resources['feature_names']
    t = resources['thresholds']
    
    # 1. Chuyển input thành DataFrame & sắp xếp đúng cột
    try:
        df = pd.DataFrame([input_data])
        # Lọc và sắp xếp cột y hệt lúc train (quan trọng!)
        df = df[features]
    except KeyError as e:
        return {"error": f"Thiếu biến đầu vào: {e}"}
    except Exception as e:
        return {"error": f"Lỗi dữ liệu: {str(e)}"}

    # 2. Thực hiện dự báo
    try:
        pred_value = float(model.predict(df)[0])
    except Exception as e:
        return {"error": f"Lỗi mô hình: {str(e)}"}

    # 3. Phân loại theo ngưỡng Tứ phân vị
    if pred_value < t['low_threshold']:
        level = "Thấp (An toàn)"
        color = "#2ecc71" # Màu xanh lá
        risk_score = 1
    elif pred_value > t['high_threshold']:
        level = "Cao (Nguy hiểm)"
        color = "#e74c3c" # Màu đỏ
        risk_score = 3
    else:
        level = "Trung bình"
        color = "#f1c40f" # Màu vàng
        risk_score = 2

    # 4. Trả về kết quả
    return {
        "salinity_value": round(pred_value, 4), # Giá trị độ mặn (dS/m)
        "warning_level": level,                 # Nhãn cảnh báo
        "color_hex": color,                     # Mã màu hiển thị Web/App
        "risk_score": risk_score                # Điểm rủi ro (1-3)5
    }

# ==========================================
# 👇 VÍ DỤ CÁCH SỬ DỤNG (Copy phần này để test)
# ==========================================
if __name__ == "__main__":
    # 1. Khởi động (Chỉ làm 1 lần)
    try:
        app_resources = load_resources() # Tải model
        
        # 2. Giả lập dữ liệu từ người dùng nhập
        user_input = {
            'temp_dry_mean_dry': 33.5,   # Nắng nóng
            'dem_mean': 2.5,             # Vùng trũng thấp
            'solar_sum_mua_kho': 1600,   # Bức xạ cao
            'rain_dry_sum': 10,          # Không mưa
            'hr_mua_kho': 95                # Chỉ số khô hạn rất cao
        }
        
        # 3. Gọi hàm dự báo
        result = predict_salinity(user_input, app_resources)
        
        # 4. Hiển thị kết quả
        print("\n--- KẾT QUẢ DỰ BÁO ---")
        print(f"🌡️ Độ mặn dự báo: {result['salinity_value']} dS/m")
        print(f"⚠️ Mức độ:        {result['warning_level']}")
        print(f"🎨 Mã màu:        {result['color_hex']}")
        
    except Exception as err:
        print(f"Lỗi chương trình: {err}")