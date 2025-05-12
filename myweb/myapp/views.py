import torch
import os
import cv2
import uuid
import logging
import sys
import mimetypes

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.forms import ValidationError
from django.http import HttpResponseNotFound, JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from ultralytics import YOLO
from PIL import Image

# Create your views here.

# Đảm bảo console hỗ trợ UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def index(request):
    return render(request,'myapp/index.html')

def base(request):
    return render(request,'myapp/base.html')

def about(request):
    return render(request,'myapp/about.html')

def service(request):
    return render(request,'myapp/service.html')

def animal(request):
    return render(request,'myapp/animal.html')

def testimonial(request):
    return render(request,'myapp/testimonial.html')

def error(request):
    return render(request,'myapp/404.html')

def contact(request):
    return render(request,'myapp/contact.html')

def signin(request):
    if request.method == 'POST':
        username_email = request.POST['username_email']
        password = request.POST['password']

        # Tìm người dùng dựa trên username hoặc email
        user = User.objects.filter(username=username_email).first() or User.objects.filter(email=username_email).first()

        if user is not None:
            # Xác thực người dùng với username
            user = authenticate(request, username=user.username, password=password)
            if user is not None:
                login(request, user)
                # messages.success(request, 'Đăng nhập thành công!')
                return redirect('upload')  
            else:
                messages.error(request, 'Mật khẩu không đúng.')
                return render(request, 'myapp/signin.html')
        else:
            messages.error(request, 'Tên đăng nhập hoặc email không tồn tại.')
            return render(request, 'myapp/signin.html')
    
    return render(request, 'myapp/signin.html')

def signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        # Kiểm tra mật khẩu khớp
        if password != confirm_password:
            messages.error(request, 'Mật khẩu không khớp.')
            return render(request, 'myapp/signup.html')

        # Kiểm tra username đã tồn tại
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Tên người dùng đã tồn tại.')
            return render(request, 'myapp/signup.html')

        # Kiểm tra email đã tồn tại
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email đã được sử dụng.')
            return render(request, 'myapp/signup.html')

        # Tạo người dùng mới
        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()
            messages.success(request, 'Đăng ký thành công! Vui lòng đăng nhập.')
            return redirect('signin')
        except ValidationError as e:
            messages.error(request, 'Đã xảy ra lỗi khi tạo tài khoản.')
            return render(request, 'myapp/signup.html')

    return render(request, 'myapp/signup.html')

def signout(request):
    logout(request)
    # messages.success(request, 'Đăng xuất thành công!')
    return redirect('index')

def upload(request):
    return render(request,'myapp/upload.html')

# Thiết lập logging
logger = logging.getLogger(__name__)

@csrf_exempt
def download_file(request, filename):
    file_path = os.path.join(settings.DETECT_DIR, filename)

    if not os.path.exists(file_path):
        return HttpResponseNotFound('File not found')

    original_name = request.GET.get('name', filename)

    mime_type, _ = mimetypes.guess_type(file_path)
    response = FileResponse(open(file_path, 'rb'), content_type=mime_type)
    response['Content-Disposition'] = f'attachment; filename="{original_name}"'
    return response

@csrf_exempt
def upload_media(request):
    if request.method == 'POST' and request.FILES.get('media'):
        media = request.FILES['media']
        original_filename = request.POST.get('original_filename')

        # Tạo tên file duy nhất để tránh trùng lặp
        file_ext = os.path.splitext(media.name)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"

        # Đường dẫn lưu file gốc trong thư mục upload
        file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

        # Lưu file gốc
        try:
            with open(file_path, 'wb+') as destination:
                for chunk in media.chunks():
                    destination.write(chunk)

        except Exception as e:
            # logger.error(f"Lỗi khi lưu file: {str(e)}")
            return JsonResponse({'success': False, 'error': f'Lưu file thất bại: {str(e)}'})

        # Tải mô hình YOLOv8
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = YOLO(os.path.join(settings.BASE_DIR, 'myapp/models/best.pt')).to(device)
            
        except Exception as e:
            # logger.error(f"Lỗi khi tải mô hình: {str(e)}")
            return JsonResponse({'success': False, 'error': f'Tải mô hình thất bại: {str(e)}'})

        # Xử lý file
        output_filename = f"processed_{unique_filename}"
        output_path = os.path.join(settings.DETECT_DIR, output_filename)
        file_url = f"{settings.MEDIA_URL}detect/{output_filename}"

        try:
            if media.name.lower().endswith(('.jpg', '.jpeg', '.png')):
                # Nhận diện với YOLOv8
                results = model(file_path)

                # Vẽ kết quả lên ảnh
                annotated_img = results[0].plot()  # Kết quả là BGR

                # Chuyển từ BGR sang RGB
                annotated_img_rgb = cv2.cvtColor(annotated_img, cv2.COLOR_BGR2RGB)

                # Lưu ảnh đã nhận diện
                annotated_img_pil = Image.fromarray(annotated_img_rgb)
                annotated_img_pil.save(output_path)

            elif media.name.lower().endswith(('.mp4', '.avi', '.mov')):
                # Xử lý video
                cap = cv2.VideoCapture(file_path)
                fourcc = cv2.VideoWriter_fourcc(*'H264')
                fps = cap.get(cv2.CAP_PROP_FPS)
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                # Tạo video đầu ra
                out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break

                    # Nhận diện với YOLOv8
                    results = model(frame)
                    annotated_frame = results[0].plot()  # Vẽ bounding box và nhãn

                    # Ghi frame đã nhận diện vào video đầu ra
                    out.write(annotated_frame)

                cap.release()
                out.release()
            else:
                return JsonResponse({'success': False, 'error': 'Định dạng file không được hỗ trợ'})

            # Tạo tên file tải xuống
            if original_filename:
                name, ext = os.path.splitext(original_filename)
                download_filename = f"{name}_ket_qua{ext}"
            else:
                download_filename = f"ket_qua{file_ext}"

            # logger.info(f"Xử lý file thành công")

            download_url = f"/download/{output_filename}?name={download_filename}"

            return JsonResponse({'success': True,
                                  'url': file_url,
                                  'download_url': download_url,
                                  'download_filename': download_filename})
        
        except Exception as e:
            # logger.error(f"Lỗi khi xử lý file: {str(e)}")
            return JsonResponse({'success': False, 'error': f'Xử lý thất bại: {str(e)}'})

    return JsonResponse({'success': False, 'error': 'Không có file hoặc yêu cầu không hợp lệ'})

def history(request):
    return render(request,'myapp/history.html')