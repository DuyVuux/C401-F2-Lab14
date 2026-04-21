import json
import os

def count_failed_cases(file_path="reports/benchmark_results.json"):
    """
    Giang thực hiện: Đếm số lượng test cases có trạng thái 'fail'
    """
    if not os.path.exists(file_path):
        print(f"⚠️ Cảnh báo: Không tìm thấy file {file_path}")
        return 0

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            results = json.load(f)
            
        # Đếm các kết quả có status là 'fail' (không phân biệt hoa thường)
        failed_cases = [r for r in results if r.get("status", "").lower() == "fail"]
        
        return len(failed_cases)
    except Exception as e:
        print(f"❌ Lỗi khi đọc file: {e}")
        return 0

# Cách tích hợp vào hàm main:
# num_fails = count_failed_cases()
# print(f"Tổng số case bị lỗi: {num_fails}")

if __name__ == "__main__":
    num_fails = count_failed_cases()
    print(f"Tổng số case bị lỗi: {num_fails}")