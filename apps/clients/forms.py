from django import forms
from apps.products.models import Client, Region


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'phone', 'address', 'region']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'region': forms.Select(attrs={'class': 'form-select'}),
        }

class RegionForm(forms.ModelForm):
    class Meta:
        model = Region
        fields = ['name', 'order']

    def clean_name(self):
        name = self.cleaned_data['name'].strip()

        if Region.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Bunday region mavjud!")

        return name