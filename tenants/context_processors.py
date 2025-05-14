def tenant_context(request):
    """
    Add tenant information to the template context
    """
    context = {}
    
    # Since we're not using tenants currently, provide empty defaults
    context['current_tenant'] = None
    context['current_domain'] = None
    context['is_public_schema'] = True
    
    return context 