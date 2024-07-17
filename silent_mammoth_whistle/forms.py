from django import forms
from .models import *

class WhistleForm(forms.ModelForm):
	class Meta:
		model = Whistle
		fields = '__all__'
