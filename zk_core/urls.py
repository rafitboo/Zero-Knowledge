"""
URL configuration for zk_core project.

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
from django.urls import path, include
from django.views.generic import TemplateView, View
from django.http import HttpResponse
from network.views import AdminConsoleView, AdminUserPostsPageView

class TestProfilePage(View):
    def get(self, request):
        html = '''<!DOCTYPE html>
<html>
<head>
    <title>Test Profile Update</title>
    <style>
        body { font-family: monospace; background: #1a1a1a; color: #00ff00; padding: 20px; }
        input, button { background: #222; color: #00ff00; border: 1px solid #00ff00; padding: 8px; margin: 5px 0; }
        pre { background: #222; border: 1px solid #666; padding: 10px; overflow-x: auto; }
    </style>
</head>
<body>
    <h1>Test Profile Update</h1>
    
    <div>
        <label>Token:</label><br>
        <input type="text" id="tokenInput" placeholder="Paste your JWT token here" style="width: 500px;">
    </div>
    
    <div style="margin-top: 20px;">
        <label>New Email:</label><br>
        <input type="email" id="emailInput" placeholder="newemail@example.com">
    </div>
    
    <div style="margin-top: 20px;">
        <button onclick="testUpdate()">Test PATCH Request</button>
    </div>
    
    <div style="margin-top: 30px; border: 1px solid #00ff00; padding: 10px;">
        <h3>Response:</h3>
        <pre id="response">Waiting for response...</pre>
    </div>

    <script>
        async function testUpdate() {
            const token = document.getElementById('tokenInput').value;
            const email = document.getElementById('emailInput').value;
            
            if (!token) {
                document.getElementById('response').innerText = 'ERROR: Please paste token first';
                return;
            }
            
            if (!email) {
                document.getElementById('response').innerText = 'ERROR: Please enter email';
                return;
            }
            
            console.log('Sending PATCH request...');
            console.log('Token:', token);
            console.log('Email:', email);
            
            try {
                const response = await fetch('/api/accounts/profile/', {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({email: email})
                });
                
                const data = await response.json();
                
                console.log('Response status:', response.status);
                console.log('Response data:', data);
                
                document.getElementById('response').innerText = JSON.stringify(data, null, 2) + '\\n\\nStatus: ' + response.status;
            } catch (err) {
                console.error('Error:', err);
                document.getElementById('response').innerText = 'ERROR: ' + err.message;
            }
        }
    </script>
</body>
</html>'''
        return HttpResponse(html)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('accounts.urls')), 
    path('api/network/', include('network.urls')),
    path('test-profile/', TestProfilePage.as_view(), name='test_profile'),
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('feed/', TemplateView.as_view(template_name='feed.html'), name='feed'),
    path('admin-console/', AdminConsoleView.as_view(), name='admin_console'),
    path('admin-console/users/<int:user_id>/posts/', AdminUserPostsPageView.as_view(), name='admin_user_posts_page'),
]
