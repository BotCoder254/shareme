from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.conf import settings
from .forms import TenantSignupForm
from .models import Tenant, Domain
# import django_tenants.utils
from django.contrib.auth.decorators import user_passes_test

def is_superuser(user):
    return user.is_superuser

def tenant_signup(request):
    """View for new tenant signup"""
    if request.method == 'POST':
        form = TenantSignupForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create the tenant
                    tenant = form.save(commit=False)
                    tenant.schema_name = form.cleaned_data['domain_name']
                    tenant.save()
                    
                    # Create the domain
                    domain_name = form.cleaned_data['domain_name'].lower()
                    host = request.get_host().split(':')[0]
                    domain = Domain()
                    domain.domain = f"{domain_name}.{host}"
                    domain.tenant = tenant
                    domain.is_primary = True
                    domain.save()
                    
                    # Create a superuser for the tenant
                    # In production with django-tenants, we would use tenant_context
                    # But since we're using SQLite for development, we'll create a regular superuser
                    admin_username = form.cleaned_data['admin_username']
                    admin_email = form.cleaned_data['admin_email']
                    admin_password = form.cleaned_data['admin_password']
                    
                    # Check if user already exists
                    if not User.objects.filter(username=admin_username).exists():
                        # Create a new admin user
                        admin_user = User.objects.create_superuser(
                            username=admin_username,
                            email=admin_email,
                            password=admin_password
                        )
                        # Store reference to tenant in user profile or a separate model if needed
                        admin_user.first_name = f"Admin of {tenant.name}"
                        admin_user.save()
                    else:
                        # If user already exists, just add a note in the message
                        messages.info(request, f"Note: The username '{admin_username}' already exists.")
                    
                    # Redirect to a success page
                    messages.success(request, f"Your tenant '{tenant.name}' has been created successfully! You can now access it at {domain.domain}")
                    
                    # Since we're using SQLite, we'll redirect to the success page
                    # In production with actual multi-tenancy, we'd redirect to the tenant domain
                    return HttpResponseRedirect('/tenants/success/')
            except Exception as e:
                messages.error(request, f"Error creating tenant: {str(e)}")
    else:
        form = TenantSignupForm()
    
    return render(request, 'tenants/tenant_signup.html', {'form': form})

def tenant_success(request):
    """Success page after tenant creation"""
    return render(request, 'tenants/tenant_success.html')

@user_passes_test(is_superuser)
def tenant_list(request):
    """List all tenants (superusers only)"""
    tenants = Tenant.objects.all()
    return render(request, 'tenants/tenant_list.html', {'tenants': tenants})

@user_passes_test(is_superuser)
def tenant_detail(request, tenant_id):
    """View tenant details (superusers only)"""
    tenant = Tenant.objects.get(id=tenant_id)
    domains = tenant.domains.all()
    return render(request, 'tenants/tenant_detail.html', {'tenant': tenant, 'domains': domains})
