from django.urls import path
from .views import (
    PostListView, 
    DecryptPostView,
    DirectMessageView, 
    DMPageView,
    OperativeDirectoryView, # <--- NEW IMPORT
    SystemAuditView, 
    AdminUserManagementView, 
    AdminPromoteUserView, 
    AdminUserActionView,
    AdminUserPostsView,
)

urlpatterns = [
    # Global Feed Routes
    path('posts/', PostListView.as_view(), name='posts'),
    path('posts/<int:post_id>/decrypt/', DecryptPostView.as_view(), name='decrypt_post'),
    
    # Direct Messaging Routes
    path('dm/send/', DirectMessageView.as_view(), name='send_dm'),
    path('dm/<str:target_username>/', DirectMessageView.as_view(), name='get_dms'),
    path('dms/page/', DMPageView.as_view(), name='dm_page_html'), 
    
    # NEW: The Public Operative Directory
    path('operatives/', OperativeDirectoryView.as_view(), name='operative_directory'),
    
    # Admin & RBAC Routes
    path('audit/', SystemAuditView.as_view(), name='system_audit'),
    path('admin/users/', AdminUserManagementView.as_view(), name='admin_user_list'),
    path('admin/users/<int:user_id>/promote/', AdminPromoteUserView.as_view(), name='admin_promote'),
    path('admin/users/<int:user_id>/action/', AdminUserActionView.as_view(), name='admin_action'),
    path('admin/users/<int:user_id>/posts/', AdminUserPostsView.as_view(), name='admin_user_posts_api'),
]