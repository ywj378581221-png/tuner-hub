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
from community.views import article_comments, article_detail, change_password, confirm_password_reset, create_article, create_content_report, create_garage_vehicle, create_post, create_project_record, current_user, delete_article, delete_post, login_user, logout_user, mark_private_message_read, post_comments, private_messages, register_user, request_password_reset, send_private_message, site_data, toggle_article_like, toggle_article_save, toggle_follow_user, toggle_post_like, toggle_post_save, update_email, update_profile, upload_avatar
from tunerhub.views import frontend_app

urlpatterns = [
    path('api/site-data/', site_data, name='site-data'),
    path('api/auth/me/', current_user, name='current-user'),
    path('api/auth/register/', register_user, name='register-user'),
    path('api/auth/login/', login_user, name='login-user'),
    path('api/auth/logout/', logout_user, name='logout-user'),
    path('api/auth/profile/', update_profile, name='update-profile'),
    path('api/auth/email/', update_email, name='update-email'),
    path('api/auth/password/', change_password, name='change-password'),
    path('api/auth/password-reset/request/', request_password_reset, name='request-password-reset'),
    path('api/auth/password-reset/confirm/', confirm_password_reset, name='confirm-password-reset'),
    path('api/auth/avatar/', upload_avatar, name='upload-avatar'),
    path('api/users/<int:user_id>/follow/', toggle_follow_user, name='toggle-follow-user'),
    path('api/users/<int:user_id>/message/', send_private_message, name='send-private-message'),
    path('api/messages/', private_messages, name='private-messages'),
    path('api/messages/<int:message_id>/read/', mark_private_message_read, name='mark-private-message-read'),
    path('api/posts/create/', create_post, name='create-post'),
    path('api/posts/<int:post_id>/save/', toggle_post_save, name='toggle-post-save'),
    path('api/posts/<int:post_id>/like/', toggle_post_like, name='toggle-post-like'),
    path('api/posts/<int:post_id>/comments/', post_comments, name='post-comments'),
    path('api/posts/<int:post_id>/delete/', delete_post, name='delete-post'),
    path('api/articles/create/', create_article, name='create-article'),
    path('api/articles/<int:article_id>/', article_detail, name='article-detail'),
    path('api/articles/<int:article_id>/save/', toggle_article_save, name='toggle-article-save'),
    path('api/articles/<int:article_id>/like/', toggle_article_like, name='toggle-article-like'),
    path('api/articles/<int:article_id>/comments/', article_comments, name='article-comments'),
    path('api/articles/<int:article_id>/delete/', delete_article, name='delete-article'),
    path('api/reports/create/', create_content_report, name='create-content-report'),
    path('api/garage/create/', create_garage_vehicle, name='create-garage-vehicle'),
    path('api/projects/create/', create_project_record, name='create-project-record'),
    path('admin/', admin.site.urls),
    re_path(r'^(?!api/|admin/|static/|media/).*$', frontend_app, name='frontend-app'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
