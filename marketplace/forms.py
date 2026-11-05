import base64
import uuid
from decimal import Decimal
from django import forms
from django.core.files.base import ContentFile
from django.contrib.auth.models import User
from .models import Listing, SellerProfile, SellerReview, ReportedListing


class UserRegisterForm(forms.ModelForm):
    full_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Full Name',
            'class': 'w-full bg-[#F3F4FB] text-slate-800 placeholder-slate-400 px-4 py-3.5 rounded-lg text-sm border border-transparent focus:border-[#2250EB] focus:bg-white focus:outline-hidden transition-all'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Email',
            'class': 'w-full bg-[#F3F4FB] text-slate-800 placeholder-slate-400 px-4 py-3.5 rounded-lg text-sm border border-transparent focus:border-[#2250EB] focus:bg-white focus:outline-hidden transition-all'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password',
            'id': 'regPassword',
            'class': 'w-full bg-[#F3F4FB] text-slate-800 placeholder-slate-400 px-4 py-3.5 rounded-lg text-sm border border-transparent focus:border-[#2250EB] focus:bg-white focus:outline-hidden transition-all pr-11'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm password',
            'id': 'regConfirmPassword',
            'class': 'w-full bg-[#F3F4FB] text-slate-800 placeholder-slate-400 px-4 py-3.5 rounded-lg text-sm border border-transparent focus:border-[#2250EB] focus:bg-white focus:outline-hidden transition-all pr-11'
        })
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Phone number (optional)',
            'class': 'w-full bg-[#F3F4FB] text-slate-800 placeholder-slate-400 px-4 py-3.5 rounded-lg text-sm border border-transparent focus:border-[#2250EB] focus:bg-white focus:outline-hidden transition-all'
        })
    )

    class Meta:
        model = User
        fields = ['full_name', 'email', 'password']

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        pwd = cleaned_data.get("password")
        pwd_confirm = cleaned_data.get("confirm_password")

        if pwd and pwd_confirm and pwd != pwd_confirm:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data


class ProfileUpdateForm(forms.ModelForm):
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-xs text-slate-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-emerald-50 file:text-emerald-700 hover:file:bg-emerald-100 cursor-pointer'
        })
    )
    store_banner = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-xs text-slate-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-emerald-50 file:text-emerald-700 hover:file:bg-emerald-100 cursor-pointer'
        })
    )
    selfie_base64 = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = SellerProfile
        fields = [
            'avatar',
            'store_banner',
            'phone_number',
            'whatsapp_number',
            'shop_address',
            'state',
            'area',
            'instagram_handle',
            'facebook_handle',
            'tiktok_handle',
            'bio',
            'id_document',
        ]
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'placeholder': '08012345678',
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-purple-500 text-sm bg-white'
            }),
            'whatsapp_number': forms.TextInput(attrs={
                'placeholder': '2348012345678',
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-purple-500 text-sm bg-white'
            }),
            'shop_address': forms.TextInput(attrs={
                'placeholder': 'e.g. Shop B12, Emab Plaza, Wuse 2, Abuja',
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-purple-500 text-sm bg-white'
            }),
            'state': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-purple-500 text-sm bg-white cursor-pointer'
            }),
            'area': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-purple-500 text-sm bg-white cursor-pointer'
            }),
            'instagram_handle': forms.TextInput(attrs={
                'placeholder': '@yourstore',
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-purple-500 text-sm bg-white'
            }),
            'facebook_handle': forms.TextInput(attrs={
                'placeholder': 'facebook.com/yourstore',
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-purple-500 text-sm bg-white'
            }),
            'tiktok_handle': forms.TextInput(attrs={
                'placeholder': '@yourstore',
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-purple-500 text-sm bg-white'
            }),
            'bio': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Tell buyers about your shop, warranty, or delivery policies...',
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-purple-500 text-sm bg-white'
            }),
            'id_document': forms.ClearableFileInput(attrs={
                'class': 'block w-full text-xs text-slate-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100 cursor-pointer'
            }),
        }

    def save(self, commit=True):
        profile = super().save(commit=False)
        selfie_data = self.cleaned_data.get('selfie_base64')

        if selfie_data and ';base64,' in selfie_data:
            format_str, img_str = selfie_data.split(';base64,')
            ext = format_str.split('/')[-1]
            if ext == 'jpeg':
                ext = 'jpg'
            file_name = f"selfie_{profile.user.id}_{uuid.uuid4().hex[:8]}.{ext}"
            profile.selfie_image.save(file_name, ContentFile(base64.b64decode(img_str)), save=False)

        if commit:
            profile.save()
        return profile


class ListingForm(forms.ModelForm):
    # Job-specific fields
    company_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. Paystack Nigeria Ltd',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-purple-500 text-sm bg-white'
        })
    )
    min_salary = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Min Salary (e.g. 50000)',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-purple-500 text-sm bg-white'
        })
    )
    max_salary = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Max Salary (e.g. 100000)',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-purple-500 text-sm bg-white'
        })
    )
    job_type = forms.ChoiceField(
        required=False,
        choices=[
            ('full_time', 'Full-time'),
            ('part_time', 'Part-time'),
            ('contract', 'Contract'),
            ('internship', 'Internship'),
            ('remote', 'Remote / Work From Home'),
        ],
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-purple-500 text-sm bg-white cursor-pointer'
        })
    )
    experience_level = forms.ChoiceField(
        required=False,
        choices=[
            ('entry', 'Entry Level / Fresher'),
            ('mid', 'Mid-Level (2-5 Years)'),
            ('senior', 'Senior / Executive (5+ Years)'),
            ('intern', 'Student / Intern'),
        ],
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-purple-500 text-sm bg-white cursor-pointer'
        })
    )
    minimum_experience = forms.ChoiceField(
        required=False,
        choices=[
            ('0', 'No Experience Required'),
            ('1', '1 Year'),
            ('2', '2 Years'),
            ('3_5', '3 - 5 Years'),
            ('5_plus', 'More than 5 Years'),
        ],
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-purple-500 text-sm bg-white cursor-pointer'
        })
    )

    # Property-specific fields
    property_type = forms.ChoiceField(
        required=False,
        choices=[
            ('flat_apartment', 'Flat / Apartment'),
            ('self_contain', 'Self Contain / Mini Flat'),
            ('duplex', 'Duplex / Semi-Detached'),
            ('land', 'Land / Plot'),
            ('commercial', 'Shop / Office Space'),
        ],
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-purple-500 text-sm bg-white cursor-pointer'
        })
    )
    bedrooms = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Bedrooms (e.g. 2)',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-purple-500 text-sm bg-white'
        })
    )
    bathrooms = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Bathrooms (e.g. 2)',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-purple-500 text-sm bg-white'
        })
    )
    furnishing = forms.ChoiceField(
        required=False,
        choices=[
            ('unfurnished', 'Unfurnished'),
            ('semi_furnished', 'Semi-Furnished'),
            ('furnished', 'Fully Furnished'),
        ],
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-purple-500 text-sm bg-white cursor-pointer'
        })
    )

    class Meta:
        model = Listing
        fields = ['title', 'category', 'subcategory', 'price', 'condition', 'state', 'area', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'e.g. Senior Backend Developer (Django) or 2 Bedroom Flat',
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-purple-500 text-sm bg-white'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-purple-500 text-sm bg-white cursor-pointer'
            }),
            'subcategory': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-purple-500 text-sm bg-white cursor-pointer'
            }),
            'price': forms.NumberInput(attrs={
                'placeholder': 'Asking Price (₦)',
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-purple-500 text-sm bg-white'
            }),
            'condition': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-purple-500 text-sm bg-white cursor-pointer'
            }),
            'state': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-purple-500 text-sm bg-white cursor-pointer'
            }),
            'area': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-purple-500 text-sm bg-white cursor-pointer'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe duties, qualifications, work hours, or property specs thoroughly...',
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-purple-500 text-sm bg-white'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Condition and price are explicitly optional so non-physical listings don't fail validation
        self.fields['condition'].required = False
        self.fields['price'].required = False

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        cat_name = category.name.lower() if category else ''

        price = cleaned_data.get('price')
        min_sal = cleaned_data.get('min_salary')

        if 'job' in cat_name:
            if not min_sal and not price:
                self.add_error('min_salary', "Please enter a minimum salary for this job.")
        else:
            if price is None:
                self.add_error('price', "Please enter an asking price.")

        return cleaned_data

    def save(self, commit=True):
        listing = super().save(commit=False)
        category = self.cleaned_data.get('category')
        cat_name = category.name.lower() if category else ''

        extra = listing.extra_fields or {}

        if 'job' in cat_name:
            extra['company_name'] = self.cleaned_data.get('company_name', '')
            extra['min_salary'] = str(self.cleaned_data.get('min_salary') or '')
            extra['max_salary'] = str(self.cleaned_data.get('max_salary') or '')
            extra['job_type'] = self.cleaned_data.get('job_type', 'full_time')
            extra['experience_level'] = self.cleaned_data.get('experience_level', 'entry')
            extra['minimum_experience'] = self.cleaned_data.get('minimum_experience', '0')
            min_val = self.cleaned_data.get('min_salary')
            listing.price = Decimal(str(min_val)) if min_val else Decimal('0.00')
            listing.condition = None
        elif 'prop' in cat_name or 'real estate' in cat_name:
            extra['property_type'] = self.cleaned_data.get('property_type', 'flat_apartment')
            extra['bedrooms'] = self.cleaned_data.get('bedrooms') or 0
            extra['bathrooms'] = self.cleaned_data.get('bathrooms') or 0
            extra['furnishing'] = self.cleaned_data.get('furnishing', 'unfurnished')
            listing.condition = None

        listing.extra_fields = extra

        if commit:
            listing.save()
        return listing


class ReportListingForm(forms.ModelForm):
    class Meta:
        model = ReportedListing
        fields = ['reason', 'details']
        widgets = {
            'reason': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-xs bg-white cursor-pointer'
            }),
            'details': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Provide specific details for moderation review...',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-xs bg-white'
            }),
        }


class SellerReviewForm(forms.ModelForm):
    class Meta:
        model = SellerReview
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(
                choices=[(5, '⭐⭐⭐⭐⭐ (5 Stars)'), (4, '⭐⭐⭐⭐ (4 Stars)'), (3, '⭐⭐⭐ (3 Stars)'), (2, '⭐⭐ (2 Stars)'), (1, '⭐ (1 Star)')],
                attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-xs bg-white cursor-pointer'}
            ),
            'comment': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Share your experience with this seller...',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-xs bg-white'
            }),
        }