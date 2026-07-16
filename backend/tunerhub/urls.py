"""
URL configuration for tunerhub project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, re_path
from community.views import create_garage_vehicle, create_post, create_project_record, current_user, delete_post, login_user, logout_user, private_messages, register_user, send_private_message, site_data, toggle_follow_user, update_profile, upload_avatar
from tunerhub.views import frontend_app

urlpatterns = [
    path('api/site-data/', site_data, name='site-data'),
    path('api/auth/me/', current_user, name='current-user'),
    path('api/auth/register/', register_user, name='register-user'),
    path('api/auth/login/', login_user, name='login-user'),
    path('api/auth/logout/', logout_user, name='logout-user'),
    path('api/auth/profile/', update_profile, name='update-profile'),
    path('api/auth/avatar/', upload_avatar, name='upload-avatar'),
    path('api/users/<int:user_id>/follow/', toggle_follow_user, name='toggle-follow-user'),
    path('api/users/<int:user_id>/message/', send_private_message, name='send-private-message'),
    path('api/messages/', private_messages, name='private-messages'),
    path('api/posts/create/', create_post, name='create-post'),
    path('api/posts/<int:post_id>/delete/', delete_post, name='delete-post'),
    path('api/garage/create/', create_garage_vehicle, name='create-garage-vehicle'),
    path('api/projects/create/', create_project_record, name='create-project-record'),
    path('admin/', admin.site.urls),
    re_path(r'^(?!api/|admin/|static/|media/).*$', frontend_app, name='frontend-app'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
