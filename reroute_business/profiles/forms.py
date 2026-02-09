from django import forms
from .models import EmployerProfile

from reroute_business.resumes import models
from .models import UserProfile
from reroute_business.profiles.constants import USER_STATUS_CHOICES, YES_NO, US_STATES, PRONOUN_CHOICES, LANGUAGE_CHOICES, GENDER_CHOICES, ETHNICITY_CHOICES, RACE_CHOICES

class Step1Form(forms.ModelForm):
    state = forms.ChoiceField(choices = US_STATES)
    class Meta:
        model = UserProfile
        fields = [
            'firstname',
            'lastname',
            'preferred_name',
            'phone_number',
            'personal_email',
            'street_address',
            'city',
            'state',
            'zip_code',
            'bio',
        ] 

    def clean(self):
        cleaned_data = super().clean()

        required_fields = [
            'firstname', 'lastname', 'phone_number',
            'personal_email', 'street_address', 'city', 'state', 'zip_code'
        ]
        for field in required_fields:
            if not cleaned_data.get(field):
                self.add_error(field, 'This field is required.')


class Step2Form(forms.ModelForm):
    pronouns = forms.ChoiceField(choices=PRONOUN_CHOICES)
    pronouns_other = forms.CharField(required=False)

    native_language = forms.ChoiceField(choices=LANGUAGE_CHOICES)
    native_language_other = forms.CharField(required=False)

    birthdate = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        required=True,
        label="Birthdate"
    )


    class Meta:
        model = UserProfile
        fields = [
            'profile_picture',
            'birthdate',
            'pronouns',
            'native_language',
            'year_of_incarceration',
            'year_released',
            'relation_to_reroute',
        ]

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get('pronouns') == 'other' and not cleaned_data.get('pronouns_other'):
            self.add_error('pronouns_other', 'Please specify your pronouns.')

        if cleaned_data.get('native_language') == 'other' and not cleaned_data.get('native_language_other'):
            self.add_error('native_language_other', 'Please specify your native language.')

        required_fields = ['birthdate', 'pronouns', 'native_language']
        for field in required_fields:
            if not cleaned_data.get(field):
                self.add_error(field, 'This field is required.')


    

class Step3Form(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'emergency_contact_firstname',
            'emergency_contact_lastname',
            'emergency_contact_relationship',
            'emergency_contact_phone',
            'emergency_contact_email',
        ]

    def clean(self):
        cleaned_data = super().clean()
        required_fields = self.Meta.fields

        for field in required_fields:
            if not cleaned_data.get(field):
                self.add_error(field, 'This field is required.')

class Step4Form(forms.ModelForm):
    gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Gender"
    )
    ethnicity = forms.ChoiceField(
        choices=ETHNICITY_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Ethnicity"
    )
    race = forms.MultipleChoiceField(
        choices=RACE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Race (check all that apply):"
    )
    disability = forms.ChoiceField(
        choices=YES_NO,
        widget=forms.RadioSelect,
        label="Do you have a disability?",
        required=True
    )
    disability_explanation = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        label="If yes, please briefly describe your disability"
    )
    veteran_status = forms.ChoiceField(
        choices=YES_NO,
        widget=forms.RadioSelect,
        label="Are you a veteran?",
        required=True
    )
    veteran_explanation = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        label="If yes, please describe your service or background"
    )

    status = forms.ChoiceField(
        choices= USER_STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Current Status"
    )



    class Meta:
        model = UserProfile
        fields = [
            'gender',
            'ethnicity',
            'race',
            'disability',
            'disability_explanation',
            'veteran_status',
            'veteran_explanation',
            'status',
        ]

    def clean_gender(self):
        value = self.cleaned_data.get('gender', '').strip()
        if value == '':
            raise forms.ValidationError("Please select your gender.")
        return value

    def clean_ethnicity(self):
        value = self.cleaned_data.get('ethnicity', '').strip()
        if value == '':
            raise forms.ValidationError("Please select your ethnicity.")
        return value
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.race = self.cleaned_data.get('race')  
        if commit:
            profile.save()
        return profile

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get('disability') == 'yes' and not cleaned_data.get('disability_explanation'):
            self.add_error('disability_explanation', 'Please provide a brief explanation.')

        if cleaned_data.get('veteran_status') == 'yes' and not cleaned_data.get('veteran_explanation'):
            self.add_error('veteran_explanation', 'Please describe your service.')


class EmploymentInfoForm(forms.ModelForm):
    # Note: these map to actual fields on UserProfile
    class Meta:
        model = UserProfile
        fields = [
            'work_in_us',          # yes/no: authorized to work in US
            'sponsorship_needed',  # yes/no: needs sponsorship
            'lgbtq',               # yes/no
            'disability',          # yes/no
            'gender',              # free text/choice
            'veteran_status',      # yes/no (correct field name)
            'status',              # journey status (optional but useful)
        ]


# -------------------------------------------------------
# EmployerProfileForm
# -------------------------------------------------------
# Lightweight ModelForm to edit employer details without
# changing any backend logic or models. We include only
# fields guaranteed by the current EmployerProfile model.
# If your EmployerProfile model includes additional fields
# like `phone`, `address`, `state`, or `verified`, simply
# add them to the fields list below.
class EmployerProfileForm(forms.ModelForm):
    class Meta:
        model = EmployerProfile
        fields = [
            'company_name',
            'website',
            'description',
            'logo',
            'background_image',
            # Optional: add 'phone', 'address', 'state', 'verified' here if present in your model
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'placeholder': 'Company name'}),
            'website': forms.URLInput(attrs={'placeholder': 'https://example.com'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Brief description of your company'}),
        }
        labels = {
            'company_name': 'Company Name',
            'website': 'Website',
            'description': 'Description',
            'logo': 'Company Logo',
            'background_image': 'Hero Background (optional)',
        }

    def clean_logo(self):
        """
        Basic server-side validation for uploaded logo files.
        - Max size: 2 MB
        - Allowed content types: JPEG, PNG, GIF, WEBP
        """
        logo = self.cleaned_data.get('logo')
        if not logo:
            return logo

        # Size check
        max_bytes = 2 * 1024 * 1024  # 2 MB
        size = getattr(logo, 'size', 0) or 0
        if size > max_bytes:
            raise forms.ValidationError("Logo file is too large (max 2MB).")

        # Content type check (best-effort; some storage backends may not set it)
        allowed = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        ctype = getattr(logo, 'content_type', None)
        if ctype and ctype.lower() not in allowed:
            raise forms.ValidationError("Unsupported logo type. Use JPG, PNG, GIF, or WebP.")

        return logo

    def clean_background_image(self):
        bg = self.cleaned_data.get('background_image')
        if not bg:
            return bg
        max_bytes = 5 * 1024 * 1024  # 5 MB for hero images
        size = getattr(bg, 'size', 0) or 0
        if size > max_bytes:
            raise forms.ValidationError("Background image is too large (max 5MB).")
        allowed = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        ctype = getattr(bg, 'content_type', None)
        if ctype and ctype.lower() not in allowed:
            raise forms.ValidationError("Unsupported image type. Use JPG, PNG, GIF, or WebP.")
        return bg


class EmployerOnboardingForm(forms.ModelForm):
    class Meta:
        model = EmployerProfile
        fields = ['company_name', 'website', 'description']
        widgets = {
            'company_name': forms.TextInput(attrs={'placeholder': 'Company name'}),
            'website': forms.URLInput(attrs={'placeholder': 'https://example.com'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Tell candidates about your mission.'}),
        }
        labels = {
            'company_name': 'Company name',
            'website': 'Website (optional)',
            'description': 'Company description (optional)',
        }
