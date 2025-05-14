from django.urls import path
from . import views

app_name = 'files'

urlpatterns = [
    path('', views.file_list, name='file_list'),
    path('upload/', views.file_upload, name='file_upload'),
    path('<int:file_id>/', views.file_detail, name='file_detail'),
    path('<int:file_id>/delete/', views.file_delete, name='file_delete'),
    path('<int:file_id>/favorite/', views.file_toggle_favorite, name='file_toggle_favorite'),
    path('<int:file_id>/share/', views.file_share, name='file_share'),
    path('<int:file_id>/download/', views.file_download, name='file_download'),
    path('shared/', views.shared_files, name='shared_files'),
    
    # Folder related URLs
    path('folder/create/', views.create_folder, name='create_folder'),
    path('folder/<int:folder_id>/delete/', views.folder_delete, name='folder_delete'),
    path('folder/<int:folder_id>/share/', views.folder_share, name='folder_share'),
    path('folder/<int:folder_id>/unshare/', views.folder_unshare, name='folder_unshare'),
    path('folder/<int:folder_id>/contents/', views.folder_contents, name='folder_contents'),
    
    # Share link URLs
    path('<int:file_id>/create-share-link/', views.create_file_share_link, name='create_file_share_link'),
    path('folder/<int:folder_id>/create-share-link/', views.create_folder_share_link, name='create_folder_share_link'),
    path('share-links/<int:file_id>/', views.manage_share_links, name='manage_share_links', kwargs={'folder_id': None}),
    path('share-links/folder/<int:folder_id>/', views.manage_share_links, name='manage_folder_share_links', kwargs={'file_id': None}),
    path('share-links/delete/<int:link_id>/', views.delete_share_link, name='delete_share_link'),
] 