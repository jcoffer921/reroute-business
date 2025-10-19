from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django import forms

from resumes.models import Application
from profiles.models import UserProfile, EmployerProfile


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("job", "applicant", "status")
    list_filter = ("status",)
    search_fields = ("job__title", "applicant__username")

# Resume admin is managed in the 'resumes' app admin.

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "user_uid", "phone_number", "birthdate", "status", "account_status")
    list_filter = ("account_status", "status")
    search_fields = ("user__username", "user_uid", "phone_number", "bio")
    readonly_fields = ("user_uid",)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)


# =========================
# Extend built-in User admin with Employer toggle
# =========================

class EmployerFlagListFilter(admin.SimpleListFilter):
    title = 'Employer status'
    parameter_name = 'is_employer'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Employer'),
            ('0', 'Not employer'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(groups__name__in=['Employer', 'Employers']).distinct()
        if self.value() == '0':
            return queryset.exclude(groups__name__in=['Employer', 'Employers']).distinct()
        return queryset


class UserChangeWithEmployerForm(forms.ModelForm):
    is_employer_admin = forms.BooleanField(label='Employer status', required=False)

    class Meta:
        model = User
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.instance
        if user and user.pk:
            is_emp = user.groups.filter(name__in=['Employer', 'Employers']).exists()
            self.fields['is_employer_admin'].initial = is_emp


class UserAddWithEmployerForm(forms.ModelForm):
    # Mirror the default add form fields (username, password1/2 are provided by BaseUserAdmin add_fieldsets)
    is_employer_admin = forms.BooleanField(label='Employer status', required=False, initial=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')


class UserAdmin(BaseUserAdmin):
    form = UserChangeWithEmployerForm
    add_form = UserAddWithEmployerForm

    list_display = BaseUserAdmin.list_display + ('is_employer_admin_flag',)
    list_filter = BaseUserAdmin.list_filter + (EmployerFlagListFilter,)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role', {'fields': ('is_employer_admin',)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Role', {'fields': ('is_employer_admin',)}),
    )

    def is_employer_admin_flag(self, obj):
        return obj.groups.filter(name__in=['Employer', 'Employers']).exists()

    is_employer_admin_flag.boolean = True
    is_employer_admin_flag.short_description = 'Employer'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Toggle Employer group and optional EmployerProfile based on checkbox
        wants_employer = bool(form.cleaned_data.get('is_employer_admin'))
        employer_group, _ = Group.objects.get_or_create(name='Employer')

        if wants_employer:
            obj.groups.add(employer_group)
            # Ensure an EmployerProfile exists for convenience
            EmployerProfile.objects.get_or_create(user=obj, defaults={'company_name': obj.username})
        else:
            obj.groups.remove(employer_group)
            # Do not delete EmployerProfile automatically; keep data safe


# Re-register the built-in User with our extended admin
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, UserAdmin)
