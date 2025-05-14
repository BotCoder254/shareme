from django.db import models
import uuid

# Create your models here.

class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    schema_name = models.CharField(max_length=63, unique=True)
    created_on = models.DateField(auto_now_add=True)
    paid_until = models.DateField(null=True, blank=True)
    on_trial = models.BooleanField(default=True)
    logo = models.ImageField(upload_to='tenant_logos', null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    
    def __str__(self):
        return self.name

class Domain(models.Model):
    domain = models.CharField(max_length=253, unique=True, db_index=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='domains')
    is_primary = models.BooleanField(default=True)
    
    def __str__(self):
        return self.domain
