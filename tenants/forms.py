from django import forms
from .models import Tenant
from django.core.exceptions import ValidationError

class TenantSignupForm(forms.ModelForm):
    domain_name = forms.CharField(max_length=100, help_text="Your subdomain (e.g. 'company' for company.example.com)")
    admin_username = forms.CharField(max_length=100, help_text="Username for the tenant admin")
    admin_email = forms.EmailField(help_text="Email for the tenant admin")
    admin_password = forms.CharField(widget=forms.PasswordInput, help_text="Password for the tenant admin")
    admin_password_confirm = forms.CharField(widget=forms.PasswordInput, help_text="Confirm the password")
    
    class Meta:
        model = Tenant
        fields = ('name', 'description')
    
    def clean_domain_name(self):
        domain = self.cleaned_data['domain_name'].lower()
        if Tenant.objects.filter(schema_name=domain).exists():
            raise ValidationError("This domain name is already taken")
        return domain
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("admin_password")
        password_confirm = cleaned_data.get("admin_password_confirm")
        
        if password and password_confirm and password != password_confirm:
            raise ValidationError("Passwords do not match")
        
        return cleaned_data 