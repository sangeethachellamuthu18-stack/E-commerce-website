from django import forms
from .models import UsersRegister  # Import from the same app

class UsersRegisterForm(forms.ModelForm):
    class Meta:
        model = UsersRegister
        fields = '__all__'

