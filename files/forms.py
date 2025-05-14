from django import forms
from .models import FileItem, FileCategory, Folder, FileShareLink
from django.utils import timezone

class FileUploadForm(forms.ModelForm):
    """Form for uploading files"""
    class Meta:
        model = FileItem
        fields = ['title', 'description', 'file', 'category', 'is_public']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False
        self.fields['category'].required = False
        self.fields['is_public'].label = "Make file public"
        self.fields['is_public'].help_text = "Public files can be accessed by anyone with the link"

class FileCategoryForm(forms.ModelForm):
    """Form for creating file categories"""
    class Meta:
        model = FileCategory
        fields = ['name', 'icon', 'color']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['icon'].help_text = "Icon name from Heroicons or FontAwesome"
        self.fields['color'].widget = forms.TextInput(attrs={'type': 'color'})
        self.fields['color'].help_text = "Choose a color for this category"

class FolderForm(forms.ModelForm):
    """Form for creating and editing folders"""
    class Meta:
        model = Folder
        fields = ['name', 'parent']
        
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Only show folders owned by this user
            self.fields['parent'].queryset = Folder.objects.filter(user=user)
            
        self.fields['parent'].required = False
        self.fields['parent'].label = "Parent Folder"
        self.fields['parent'].help_text = "Leave empty to create in root folder"

class ShareLinkForm(forms.ModelForm):
    """Form for creating file/folder share links"""
    
    # Add fields for handling the password (it will be hashed in the view)
    password = forms.CharField(
        max_length=128, 
        required=False, 
        widget=forms.PasswordInput,
        help_text="Optional: Require a password to access this link"
    )
    
    confirm_password = forms.CharField(
        max_length=128, 
        required=False, 
        widget=forms.PasswordInput,
        help_text="Confirm the password"
    )
    
    expires_in = forms.ChoiceField(
        choices=[
            ('never', 'Never expires'),
            ('1d', '1 day'),
            ('7d', '7 days'),
            ('30d', '30 days'),
            ('custom', 'Custom date')
        ],
        initial='never',
        required=True,
        help_text="Set when this link should expire"
    )
    
    custom_expiry_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        help_text="Custom expiration date and time"
    )
    
    max_access_count = forms.IntegerField(
        required=False,
        min_value=1,
        help_text="Maximum number of times this link can be accessed (optional)"
    )
    
    class Meta:
        model = FileShareLink
        fields = ['max_access_count']
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        expires_in = cleaned_data.get('expires_in')
        custom_expiry_date = cleaned_data.get('custom_expiry_date')
        
        # Validate password confirmation
        if password and password != confirm_password:
            self.add_error('confirm_password', "The passwords don't match")
        
        # Validate custom expiry date if selected
        if expires_in == 'custom' and not custom_expiry_date:
            self.add_error('custom_expiry_date', "Please provide a custom expiration date")
        elif expires_in == 'custom' and custom_expiry_date <= timezone.now():
            self.add_error('custom_expiry_date', "The expiration date must be in the future")
            
        return cleaned_data 