
<h2 align="center">
    <a href="https://dainam.edu.vn/vi/khoa-cong-nghe-thong-tin">
    🎓 Faculty of Information Technology (DaiNam University)
    </a>
</h2>
<h2 align="center">
   Nhận diện phương tiện giao thông và biển số xe
</h2>
<div align="center">
    <p align="center">
      <img src="https://github.com/Tank97king/LapTrinhMang/blob/main/CHAT%20TCP/%E1%BA%A2nh/aiotlab_logo.png?raw=true" alt="AIoTLab Logo" width="170"/>
      <img src="https://github.com/Tank97king/LapTrinhMang/blob/main/CHAT%20TCP/%E1%BA%A2nh/fitdnu_logo.png?raw=true" alt="FITDNU Logo" width="180"/>
      <img src="https://github.com/Tank97king/LapTrinhMang/blob/main/CHAT%20TCP/%E1%BA%A2nh/dnu_logo.png?raw=true" alt="DaiNam University Logo" width="200"/>
    </p>

[![AIoTLab](https://img.shields.io/badge/AIoTLab-green?style=for-the-badge)](https://www.facebook.com/DNUAIoTLab)
[![Faculty of Information Technology](https://img.shields.io/badge/Faculty%20of%20Information%20Technology-blue?style=for-the-badge)](https://dainam.edu.vn/vi/khoa-cong-nghe-thong-tin)
[![DaiNam University](https://img.shields.io/badge/DaiNam%20University-orange?style=for-the-badge)](https://dainam.edu.vn)

</div>



## 📖 1. Giới thiệu hệ thống

Hệ thống Phân tích Tài chính Doanh nghiệp được phát triển bằng FastAPI, cung cấp API tự động hóa toàn bộ quy trình xử lý dữ liệu tài chính doanh nghiệp — từ đọc, phân tích, tính toán chỉ số, đánh giá rủi ro, đến xuất báo cáo định dạng CSV, Excel, hoặc PDF.

Mục tiêu của hệ thống là:

Giúp sinh viên, nhà phân tích tài chính, doanh nghiệp nhanh chóng đánh giá hiệu quả tài chính, nguy cơ rủi ro, và khả năng thanh toán của doanh nghiệp.

Hỗ trợ xuất dữ liệu trực tiếp vào Power BI để trực quan hóa các chỉ số.

Cung cấp khả năng lưu trữ dữ liệu lịch sử vào SQLite, phục vụ cho các phân tích theo quý, năm hoặc biến động theo thời gian.

---

## 🔧 2. Công nghệ sử dụng
                                                                                                         
- Ngôn ngữ: Python
- Framework API: FastAPI                                                                                              
- Data Handling: pandas, numpy                                                        
- Database: SQLite3                                                      
- Xuất báo cáo:reportlab                                                                                 
- ETL Module (etl/data_processing.py:Custom         
- Môi trường triển khai: Uvicorn                                                                                                      |
- Công cụ hỗ trợ: Power BI, Excel                                                                           |

---


## 🚀 3. Hình ảnh các chức năng

<p align="center">
<img src="https://github.com/Vnguiien/financial-analysis/blob/main/docs/image.png" width="500">
</p>

<p align="center">
  <em>Hình 1: Tổng quan dữ liệu  </em>
</p>

<p align="center">
<img src="https://github.com/Vnguiien/financial-analysis/blob/main/docs/z7134376209446_be076197bc19129432d4eacfd10f12c4.jpg" width="500">
    
</p>
<p align="center">
  <em> Hình 2: Phân tích tài chính </em>
</p>


<p align="center">
 <img src="https://github.com/Vnguiien/financial-analysis/blob/main/docs/z7134377254232_de615f920cf525b3042996622751dbbb.jpg" width="500">
</p>
<p align="center">
  <em> Hình 3: Xu hướng theo thời gian .</em>
</p>

<p align="center"> 

 <img src="https://github.com/Vnguiien/financial-analysis/blob/main/docs/z7134377956202_122d45f952416eb75113d29048687206.jpg" width="500">
</p>
<p align="center">
  <em> Hình 4: Phân tích rủi do doang nghiệp </em>
</p>

<p align="center"> 

 <img src="https://github.com/Vnguiien/financial-analysis/blob/main/docs/z7134380996297_1c17edc59fcd18ea0409268f30966ee4.jpg" width="500">
</p>
<p align="center">
  <em> Hình 5: Biểu đò tài chính </em>
</p>

## 📝 4. Hướng dẫn cài đặt và sử dụng

Dưới đây là các bước cấu hình và chạy dự án trên Windows . Giả định bạn đang ở thư mục gốc của dự án (chứa `backend` và `frontend`).

### 4.1. Yêu cầu hệ thống

Python ≥ 3.10

pip ≥ 22.0

Hệ điều hành: Windows 


### 4.2. Cài đặt môi trường ảo

python -m venv venv
venv\Scripts\activate   # Windows
# hoặc
source venv/bin/activate  # macOS/Linux


### 4.3. Cài đặt các thư viện cần thiết

pip install -r requirements.txt


### 4.4. Chạy backend (API + serve frontend)

1. Vào thư mục `backend` và chạy Uvicorn:

```powershell
cd backend
# chạy server (sử dụng host 0.0.0.0 nếu muốn truy cập từ máy khác)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

2. Mở trình duyệt và truy cập:

- Giao diện frontend: http://127.0.0.1:8000/  (FastAPI sẽ serve thư mục `frontend`)
- API health: http://127.0.0.1:8000/health

### 4.5. Chạy hệ thống


uvicorn app:app --reload


## 5.👤Thông tin liên hệ  
Họ tên: Nguyễn Văn Nguyên  
Lớp: CNTT 16-01.  
Email: nvn60211@gmail.com.

© 2025 AIoTLab, Faculty of Information Technology, DaiNam University. All rights reserved.

---



