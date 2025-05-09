from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.forms import ValidationError

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

def history(request):
    return render(request,'myapp/history.html')