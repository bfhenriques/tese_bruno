from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views, monitor

urlpatterns = [
    # path('', views.index, name='index'),
    path('', views.index, name="index"),
    path('views/', views.views, name='view_views'),
    path('views/add/', views.add_view, name='add_view'),
    path('views/edit/<int:pk>/', views.edit_view, name='edit_view'),
    path('views/delete/<int:pk>/', views.delete_view, name='delete_view'),

    path('timelines/', views.timelines, name='view_timelines'),
    path('timelines/add/', views.add_timeline, name='add_timeline'),
    path('timelines/edit/<int:pk>/', views.edit_timeline, name='edit_timeline'),
    path('timelines/delete/<int:pk>/', views.delete_timeline, name='delete_timeline'),

    path('contents/', views.contents, name='view_contents'),
    path('contents/add/', views.add_content, name='add_content'),
    path('contents/edit/<int:pk>/', views.edit_content, name='edit_content'),
    path('contents/delete/<int:pk>/', views.delete_content, name='delete_content'),
    path('contents/preview/<int:pk>/', views.download_content, name='download_content'),

    path('users/', views.users, name='view_users'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/edit/<int:pk>/', views.edit_user, name='edit_user'),
    path('users/delete/<int:pk>/', views.delete_user, name='delete_user'),

    path('permissions/contents/<int:pk>/', views.permissions_contents, name='permissions_contents'),
    path('permissions/timelines/<int:pk>/', views.permissions_timelines, name='permissions_timelines'),
    path('permissions/views/<int:pk>/', views.permissions_views, name='permissions_views'),

    path('monitor/new_monitor/', monitor.new_monitor),
    path('monitor/check_for_changes/', monitor.check_for_changes),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
