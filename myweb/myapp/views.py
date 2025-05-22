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
from django.urls import reverse
from django.db.models import Q
from django.core.validators import validate_email
from ultralytics import YOLO
from PIL import Image

# Create your views here.

# Thiết lập logging
logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(settings.BASE_DIR, 'myapp/models/best.pt')
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
_model = None

SUPPORTED_IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png')
SUPPORTED_VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov')
PROCESSED_FILE_PREFIX = "processed_"
RESULT_SUBDIR = "results"

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

        logger.info(f"Attempting signin for username/email: {username_email}")

        # Tìm người dùng dựa trên username hoặc email
        user = User.objects.filter(Q(username=username_email) | Q(email=username_email)).first()

        if user is not None:
            # Xác thực người dùng với username
            user = authenticate(request, username=user.username, password=password)
            if user is not None:
                login(request, user)
                logger.info(f"User {user.username} signed in successfully")
                # messages.success(request, 'Đăng nhập thành công!')
                return redirect('upload')  
            else:
                logger.warning(f"Failed signin attempt for {username_email}: Incorrect password")
                messages.error(request, 'Mật khẩu không đúng.')
                return render(request, 'myapp/signin.html')
        else:
            logger.warning(f"Failed signin attempt: Username or email {username_email} not found")
            messages.error(request, 'Vui lòng kiểm tra lại tên đăng nhập hoặc email.')
            return render(request, 'myapp/signin.html')
    
    logger.debug("Rendering signin page")
    return render(request, 'myapp/signin.html')

def signup(request):
    if request.method == 'POST':
        username = request.POST['username'].strip()
        email = request.POST['email'].strip()
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        logger.info(f"Attempting signup for username: {username}, email: {email}")

        # Kiểm tra định dạng email
        try:
            validate_email(email)
        except ValidationError:
            logger.warning(f"Signup failed: Invalid email format for {email}")
            messages.error(request, 'Email không hợp lệ.')
            return render(request, 'myapp/signup.html')

        # Kiểm tra mật khẩu khớp
        if password != confirm_password:
            messages.error(request, 'Mật khẩu không khớp.')
            return render(request, 'myapp/signup.html')

        # Trong hàm signup
        existing_user = User.objects.filter(Q(username=username) | Q(email=email)).first()
        if existing_user:
            if existing_user.username == username:
                logger.warning(f"Signup failed: Username {username} already exists")
                messages.error(request, 'Tên người dùng đã tồn tại.')
            else:
                logger.warning(f"Signup failed: Email {email} already exists")
                messages.error(request, 'Email đã được sử dụng.')
            return render(request, 'myapp/signup.html')

        # Tạo người dùng mới
        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()
            logger.info(f"User {username} signed up successfully")
            messages.success(request, 'Đăng ký thành công! Vui lòng đăng nhập.')
            return redirect('signin')
        except ValidationError as e:
            logger.error(f"Signup failed for {username}: Validation error - {str(e)}")
            messages.error(request, 'Đã xảy ra lỗi khi tạo tài khoản.')
            return render(request, 'myapp/signup.html')

    logger.debug("Rendering signup page")
    return render(request, 'myapp/signup.html')

def signout(request):
    logger.debug(f"User {request.user.username} attempting to sign out")
    logout(request)
    logger.info(f"User {request.user.username} signed out successfully")
    # messages.success(request, 'Đăng xuất thành công!')
    return redirect('index')

@login_required
def upload(request):
    logger.debug(f"User {request.user.username} accessed upload page")
    return render(request,'myapp/upload.html')

def get_yolo_model():
    """Tải mô hình YOLO chỉ khi cần."""
    global _model
    logger.debug("Attempting to load YOLO model")
    if _model is None:
        try:
            if not os.path.exists(MODEL_PATH):
                logger.error(f"Model file not found at {MODEL_PATH}")
                raise FileNotFoundError(f"Model file not found at {MODEL_PATH}")
            _model = YOLO(MODEL_PATH).to(DEVICE)
            logger.info(f"YOLO model loaded successfully on {DEVICE}")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to load YOLO model: {str(e)}")
    return _model

def validate_and_save_file(request, media, original_filename):
    """Kiểm tra và lưu file vào database."""
    logger.debug(f"Validating and saving file: {original_filename}")
    try:
        is_image = media.name.lower().endswith(SUPPORTED_IMAGE_EXTENSIONS)
        is_video = media.name.lower().endswith(SUPPORTED_VIDEO_EXTENSIONS)
        if not (is_image or is_video):
            logger.warning(f"Unsupported file format for {media.name}")
            raise ValueError('Định dạng file không được hỗ trợ')

        file_ext = os.path.splitext(media.name)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"

        upload_instance = Upload(
            user=request.user if request.user.is_authenticated else None,
            original_filename=original_filename,
        )
        media.name = unique_filename
        media_field = 'image' if is_image else 'video'
        upload_instance.__setattr__(media_field, media)
        upload_instance.save()
        logger.info(f"File {original_filename} saved successfully as {unique_filename}")
        return upload_instance, is_image, is_video, unique_filename
    except ValidationError as e:
        logger.error(f"Validation error for file {original_filename}: {str(e)}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Failed to save file {original_filename}: {str(e)}", exc_info=True)
        raise

def process_image(file_path, output_path):
    """Xử lý ảnh với YOLOv8 và lưu kết quả."""
    logger.debug(f"Processing image: {file_path}")
    try:
        model = get_yolo_model()
        results = model(file_path)
        annotated_img = results[0].plot()
        annotated_img_rgb = cv2.cvtColor(annotated_img, cv2.COLOR_BGR2RGB)
        Image.fromarray(annotated_img_rgb).save(output_path)
        logger.info(f"Image processed and saved to {output_path}")
    except cv2.error as e:
        logger.error(f"OpenCV error processing image {file_path}: {str(e)}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Failed to process image {file_path}: {str(e)}", exc_info=True)
        raise

def process_video(file_path, output_path, frame_skip=1):
    """Xử lý video với YOLOv8, bỏ qua frame để tối ưu hiệu suất."""
    logger.debug(f"Processing video: {file_path} with frame_skip={frame_skip}")
    try:
        model = get_yolo_model()
        cap = cv2.VideoCapture(file_path)
        fourcc = cv2.VideoWriter_fourcc(*'H264')
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if frame_count % frame_skip == 0:
                results = model(frame)
                annotated_frame = results[0].plot()
            else:
                annotated_frame = frame
            out.write(annotated_frame)
            frame_count += 1

        cap.release()
        out.release()
        logger.info(f"Video processed and saved to {output_path}")
    except cv2.error as e:
        logger.error(f"OpenCV error processing video {file_path}: {str(e)}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Failed to process video {file_path}: {str(e)}", exc_info=True)
        raise

@csrf_exempt
def upload_media(request):
    """Xử lý tải lên và nhận diện ảnh/video với YOLOv8."""
    logger.debug(f"Received {request.method} request for upload_media")
    if request.method == 'POST' and request.FILES.get('media'):
        media = request.FILES['media']
        original_filename = request.POST.get('original_filename')
        user = request.user.username
        logger.info(f"User {user} uploading file: {original_filename}")

        try:
            # Kiểm tra và lưu file
            upload_instance, is_image, is_video, unique_filename = validate_and_save_file(request, media, original_filename)
            file_path = os.path.join(settings.MEDIA_ROOT, upload_instance.__getattribute__('image' if is_image else 'video').name)

            # Xử lý file và lưu kết quả
            output_filename = f"{PROCESSED_FILE_PREFIX}{unique_filename}"
            output_path = os.path.join(settings.RESULTS_DIR, output_filename)
            file_url = f"{settings.MEDIA_URL}{RESULT_SUBDIR}/{output_filename}"

            if is_image:
                process_image(file_path, output_path)
            else:
                process_video(file_path, output_path)

            # Lưu kết quả vào database
            upload_instance.result.name = os.path.join(RESULT_SUBDIR, output_filename)
            upload_instance.save()
            logger.info(f"Processed file saved to database for {original_filename}")

            # Tạo tên file tải xuống
            name, ext = os.path.splitext(original_filename)
            download_filename = f"{name}_ket_qua{ext}"

            download_url = reverse('download_file', args=[output_filename]) + f"?name={download_filename}"
            logger.info(f"Upload successful for {original_filename}, download URL: {download_url}")

            return JsonResponse({
                'success': True,
                'url': file_url,
                'download_url': download_url,
                'download_filename': download_filename
            })
        
        except ValueError as e:
            logger.warning(f"Validation error for user {user}, file {original_filename}: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
        except Exception as e:
            logger.error(f"Processing failed for user {user}, file {original_filename}: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'error': f'Xử lý thất bại: {str(e)}'})
    
    logger.warning(f"Invalid request: method={request.method}, has_media={bool(request.FILES.get('media'))}")
    return JsonResponse({'success': False, 'error': 'Không có file hoặc yêu cầu không hợp lệ'})

@csrf_exempt
def download_file(request, filename):
    """Cung cấp file đã xử lý để tải xuống."""
    file_path = os.path.join(settings.RESULTS_DIR, filename)
    logger.debug(f"Attempting to download file: {filename}")

    if not os.path.exists(file_path):
        return HttpResponseNotFound('File not found')

    original_name = request.GET.get('name', filename)
    mime_type, _ = mimetypes.guess_type(file_path)
    response = FileResponse(open(file_path, 'rb'), content_type=mime_type)
    response['Content-Disposition'] = f'attachment; filename="{original_name}"'
    logger.info(f"File {filename} served for download as {original_name}")
    return response

@login_required
def history(request):
    """Hiển thị lịch sử tải lên cho người dùng đã xác thực."""
    logger.debug(f"User {request.user.username} accessing upload history")
    uploads = Upload.objects.filter(user=request.user).order_by('-uploaded_at')
    logger.info(f"Retrieved {uploads.count()} upload records for user {request.user.username}")
    return render(request, 'myapp/history.html', {'uploads': uploads})