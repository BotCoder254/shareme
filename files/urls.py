from django.urls import path
from . import views

app_name = 'files'

urlpatterns = [
    path('', views.file_list, name='file_list'),
    path('upload/', views.file_upload, name='file_upload'),
    path('<int:file_id>/', views.file_detail, name='file_detail'),
    path('<uuid:file_id>/', views.file_detail, name='file_detail'),
    path('<int:file_id>/download/', views.file_download, name='file_download'),
    path('<uuid:file_id>/download/', views.file_download, name='file_download'),
    path('<int:file_id>/delete/', views.file_delete, name='file_delete'),
    path('<uuid:file_id>/delete/', views.file_delete, name='file_delete'),
    path('<int:file_id>/restore/', views.file_restore, name='file_restore'),
    path('<uuid:file_id>/restore/', views.file_restore, name='file_restore'),
    path('<int:file_id>/favorite/', views.file_toggle_favorite, name='file_toggle_favorite'),
    path('<uuid:file_id>/favorite/', views.file_toggle_favorite, name='file_toggle_favorite'),
    path('<int:file_id>/share/', views.file_share, name='file_share'),
    path('<uuid:file_id>/share/', views.file_share, name='file_share'),
    path('shared/', views.shared_files, name='shared_files'),
    
    # Folder related URLs
    path('folder/create/', views.create_folder, name='create_folder'),
    path('folder/<int:folder_id>/delete/', views.folder_delete, name='folder_delete'),
    path('folder/<uuid:folder_id>/delete/', views.folder_delete, name='folder_delete'),
    path('folder/<int:folder_id>/share/', views.folder_share, name='folder_share'),
    path('folder/<uuid:folder_id>/share/', views.folder_share, name='folder_share'),
    path('folder/<int:folder_id>/unshare/', views.folder_unshare, name='folder_unshare'),
    path('folder/<uuid:folder_id>/unshare/', views.folder_unshare, name='folder_unshare'),
    path('folder/<int:folder_id>/contents/', views.folder_contents, name='folder_contents'),
    path('folder/<uuid:folder_id>/contents/', views.folder_contents, name='folder_contents'),
    path('folders/<int:folder_id>/', views.folder_contents, name='folder_contents'),
    path('folders/<uuid:folder_id>/', views.folder_contents, name='folder_contents'),
    
    # Share link URLs
    path('<int:file_id>/create-share-link/', views.create_file_share_link, name='create_file_share_link'),
    path('<uuid:file_id>/create-share-link/', views.create_file_share_link, name='create_file_share_link'),
    path('folder/<int:folder_id>/create-share-link/', views.create_folder_share_link, name='create_folder_share_link'),
    path('folder/<uuid:folder_id>/create-share-link/', views.create_folder_share_link, name='create_folder_share_link'),
    path('share-links/<int:file_id>/', views.manage_share_links, name='manage_share_links', kwargs={'folder_id': None}),
    path('share-links/<uuid:file_id>/', views.manage_share_links, name='manage_share_links', kwargs={'folder_id': None}),
    path('share-links/folder/<int:folder_id>/', views.manage_share_links, name='manage_folder_share_links', kwargs={'folder_id': None}),
    path('share-links/folder/<uuid:folder_id>/', views.manage_share_links, name='manage_folder_share_links', kwargs={'folder_id': None}),
    path('share-links/delete/<int:link_id>/', views.delete_share_link, name='delete_share_link'),
    path('share-links/delete/<uuid:link_id>/', views.delete_share_link, name='delete_share_link'),

    # Trash management
    path('empty-trash/', views.empty_trash, name='empty_trash'),
    
    # File version management
    path('<int:file_id>/versions/<int:version_id>/set-current/', views.file_version_set_current, name='file_version_set_current'),
    path('<uuid:file_id>/versions/<uuid:version_id>/set-current/', views.file_version_set_current, name='file_version_set_current'),
    path('<int:file_id>/versions/<int:version_id>/download/', views.file_version_download, name='file_version_download'),
    path('<uuid:file_id>/versions/<uuid:version_id>/download/', views.file_version_download, name='file_version_download'),
    path('<int:file_id>/versions/<int:version_id>/delete/', views.file_version_delete, name='file_version_delete'),
    path('<uuid:file_id>/versions/<uuid:version_id>/delete/', views.file_version_delete, name='file_version_delete'),

    # New URLs for collaboration features
    path('<int:file_id>/comments/', views.file_comments, name='file_comments'),
    path('comments/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    path('comments/<int:comment_id>/edit/', views.edit_comment, name='edit_comment'),
    path('<int:file_id>/collaborate/', views.start_collaboration, name='start_collaboration'),
    path('collaboration/<int:session_id>/join/', views.join_collaboration, name='join_collaboration'),
    path('collaboration/<int:session_id>/end/', views.end_collaboration, name='end_collaboration'),

    # Collaboration URLs
    path('file/<uuid:file_id>/start-collaboration/', views.start_collaboration, name='start_collaboration'),
    path('file/<int:file_id>/start-collaboration/', views.start_collaboration, name='start_collaboration'),
    path('collaboration/<uuid:session_id>/join/', views.join_collaboration, name='join_collaboration'),
    path('collaboration/<int:session_id>/join/', views.join_collaboration, name='join_collaboration'),
    path('collaboration/<uuid:session_id>/end/', views.end_collaboration, name='end_collaboration'),
    path('collaboration/<int:session_id>/end/', views.end_collaboration, name='end_collaboration'),
    path('collaboration/<uuid:session_id>/update/', views.update_collaboration, name='update_collaboration'),
    path('collaboration/<int:session_id>/update/', views.update_collaboration, name='update_collaboration'),
    path('collaboration/<uuid:session_id>/chat/', views.send_chat_message, name='send_chat_message'),
    path('collaboration/<int:session_id>/chat/', views.send_chat_message, name='send_chat_message'),
    
    # Comment URLs
    path('file/<uuid:file_id>/comments/', views.view_comments, name='view_comments'),
    path('file/<int:file_id>/comments/', views.view_comments, name='view_comments'),
    path('comment/<uuid:comment_id>/reply/', views.add_reply, name='add_reply'),
    path('comment/<int:comment_id>/reply/', views.add_reply, name='add_reply'),
    path('comment/<uuid:comment_id>/edit/', views.edit_comment, name='edit_comment'),
    path('comment/<int:comment_id>/edit/', views.edit_comment, name='edit_comment'),
    path('comment/<uuid:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
] 