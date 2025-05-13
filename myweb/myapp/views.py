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
from .models import Upload
from django.forms import ValidationError
from django.http import HttpResponseNotFound, JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
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
def upload_media(request):
    if request.method == 'POST' and request.FILES.get('media'):
        media = request.FILES['media']
        original_filename = request.POST.get('original_filename')

        # Tạo tên file duy nhất để tránh trùng lặp
        file_ext = os.path.splitext(media.name)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"

        # Định nghĩa loại file (image hoặc video)
        is_image = media.name.lower().endswith(('.jpg', '.jpeg', '.png'))
        is_video = media.name.lower().endswith(('.mp4', '.avi', '.mov'))

        if not (is_image or is_video):
            return JsonResponse({'success': False, 'error': 'Định dạng file không được hỗ trợ'})
        
        # Tạo đối tượng Upload để lưu vào database
        upload_instance = Upload(
            user=request.user if request.user.is_authenticated else None,
            original_filename = original_filename,
        )
        
        # Gán file vào field tương ứng (image hoặc video)
        media.name = unique_filename
        media_field = 'image' if is_image else 'video'
        upload_instance.__setattr__(media_field, media)

        # Lưu file gốc
        try:
            # Lưu đối tượng vào database
            upload_instance.save()
        except Exception as e:
            logger.error(f"Lỗi khi lưu vào database: {str(e)}")
            return JsonResponse({'success': False, 'error': f'Lưu file thất bại: {str(e)}'})

        # Lấy đường dẫn file đã lưu từ database
        file_path = os.path.join(settings.MEDIA_ROOT, upload_instance.__getattribute__(media_field).name)

        # Tải mô hình YOLOv8
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = YOLO(os.path.join(settings.BASE_DIR, 'myapp/models/best.pt')).to(device)
            
        except Exception as e:
            # logger.error(f"Lỗi khi tải mô hình: {str(e)}")
            return JsonResponse({'success': False, 'error': f'Tải mô hình thất bại: {str(e)}'})

        # Xử lý file
        output_filename = f"processed_{unique_filename}"
        output_path = os.path.join(settings.RESULTS_DIR, output_filename)  
        file_url = f"{settings.MEDIA_URL}results/{output_filename}"

        try:
            if is_image:
                # Nhận diện với YOLOv8
                results = model(file_path)

                # Vẽ kết quả lên ảnh
                annotated_img = results[0].plot()  # Kết quả là BGR

                # Chuyển từ BGR sang RGB
                annotated_img_rgb = cv2.cvtColor(annotated_img, cv2.COLOR_BGR2RGB)

                # Lưu ảnh đã nhận diện
                Image.fromarray(annotated_img_rgb).save(output_path)

            elif is_video:
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

            # Lưu đường dẫn file kết quả vào database
            upload_instance.result.name = os.path.join('results', output_filename)
            upload_instance.save()

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

@csrf_exempt
def download_file(request, filename):
    file_path = os.path.join(settings.RESULTS_DIR, filename)

    if not os.path.exists(file_path):
        return HttpResponseNotFound('File not found')

    original_name = request.GET.get('name', filename)

    mime_type, _ = mimetypes.guess_type(file_path)
    response = FileResponse(open(file_path, 'rb'), content_type=mime_type)
    response['Content-Disposition'] = f'attachment; filename="{original_name}"'
    return response

@login_required
def history(request):
    uploads = Upload.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'myapp/history.html', {'uploads': uploads})