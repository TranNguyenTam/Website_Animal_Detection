from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.forms import ValidationError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
from django.conf import settings
from ultralytics import YOLO
import cv2
import numpy as np
from PIL import Image
import uuid
import torch

# Create your views here.

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

@csrf_exempt
def upload_media(request):
    if request.method == 'POST' and request.FILES.get('media'):
        media = request.FILES['media']
        # Tạo tên file duy nhất để tránh trùng lặp
        file_ext = os.path.splitext(media.name)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"

        # Đường dẫn lưu file gốc trong thư mục upload
        file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

        # Lưu file gốc
        with open(file_path, 'wb+') as destination:
            for chunk in media.chunks():
                destination.write(chunk)

        # Tải mô hình YOLOv8
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = YOLO(os.path.join(settings.BASE_DIR, 'myapp/models/best.pt')).to(device)

        # Xử lý file
        output_filename = f"processed_{unique_filename}"
        output_path = os.path.join(settings.DETECT_DIR, output_filename)
        file_url = f"{settings.MEDIA_URL}detect/{output_filename}"

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

        return JsonResponse({'success': True, 'url': file_url})

    return JsonResponse({'success': False, 'error': 'Không có file hoặc yêu cầu không hợp lệ'})

def history(request):
    return render(request,'myapp/history.html')