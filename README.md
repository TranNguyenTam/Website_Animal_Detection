# 🐾 Website\_Animal\_Detection

Project Django nhận diện động vật với giao diện web.

---

## 🔧 1. Clone repo

```bash
git clone https://github.com/TranNguyenTam/Website_Animal_Detection.git
cd Website_Animal_Detection
```

---

## 📆 2. Tạo virtual environment & cài đặt thư viện

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

pip install -r myweb/requirements.txt
```

---

## 📁 3. Tạo database

```bash
python manage.py migrate
```

> Ảnh project dùng SQLite. Nếu dùng MySQL, hãy cập nhật `myweb/settings.py` trước khi migrate.

---

## 👤 4. Tạo superuser (tùy chọn)

```bash
python manage.py createsuperuser
```

---

## ✨ 5. Chạy server

```bash
python manage.py runserver
```

Mở trình duyệt tại: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 📜 6. Tạo file `requirements.txt` (nếu chưa có)

```bash
pip freeze > myweb/requirements.txt
git add myweb/requirements.txt
git commit -m "Add requirements.txt"
git push
```

---

## 📝 7. `.gitignore` khuyên dùng

```gitignore
myweb/venv/
__pycache__/
*.pyc
*.log
myweb/media/
*.mp4
*.dll
.vscode/
```

---

## ✅ Tóm tắt

```bash
git clone <repo-url>
cd Website_Animal_Detection
python -m venv venv
venv\Scripts\activate     # hoặc source ...
pip install -r myweb/requirements.txt
python manage.py migrate
python manage.py createsuperuser   # tùy chọn
python manage.py runserver
```

---

## ℹ️ Ghi chú

* Nếu gặp lỗi MySQL: kiểm tra service có chạy và config trong `settings.py`
* Nếu muốn đống góp: vui lòng tạo pull request hoặc issue

Chúc bạn thành công! 🚀
