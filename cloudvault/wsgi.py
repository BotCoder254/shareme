"""
WSGI config for cloudvault project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloudvault.settings')

application = get_wsgi_application()

# # We need to explicitly ensure that the tenant middleware is wrapped around the application
# class TenantWSGIMiddleware:
#     def __init__(self, application):
#         self.application = application
#         self.tenant_middleware = TenantMainMiddleware(lambda environ, start_response: None)
# 
#     def __call__(self, environ, start_response):
#         domain_model = get_tenant_domain_model()
#         domain = environ.get('HTTP_HOST', '').split(':')[0]
#         environ['HTTP_X_TENANT_DOMAIN'] = domain
#         self.tenant_middleware.process_request(environ)
#         return self.application(environ, start_response)
# 
# application = TenantWSGIMiddleware(application)
