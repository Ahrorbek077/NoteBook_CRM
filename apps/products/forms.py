from django import forms
from apps.products.models import Product, Category


class ProductForm(forms.ModelForm):

    class Meta:
        model = Product
        fields = [
            "name",
            "category",
            "price",
            "image"
        ]

        widgets = {

            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Product name"
            }),

            "category": forms.Select(attrs={
                "class": "form-control"
            }),

            "price": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Price"
            }),

            "image": forms.FileInput(attrs={
                "class": "form-control"
            }),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']

    def clean_name(self):
        name = self.cleaned_data['name'].strip()

        if Category.all_objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Bunday category allaqachon mavjud!")

        return name