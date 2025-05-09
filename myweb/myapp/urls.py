from django.contrib import admin
from django.urls import path,include
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('base/', views.base, name='base'),
    path('about/', views.about, name='about'),
    path('service/', views.service, name='service'),
    path('animal/', views.animal, name='animal'),
    path('testimonial/', views.testimonial, name='testimonial'),
    path('error/', views.error, name='error'),
    path('contact/', views.contact, name='contact'),
    path('signin/', views.signin, name='signin'),
    path('signup/', views.signup, name='signup'),
    path('signout/', views.signout, name='signout'),
    path('upload/', views.upload, name='upload'),
    path('upload_media/', views.upload_media, name='upload_media'),
    path('history/', views.history, name='history'),
]