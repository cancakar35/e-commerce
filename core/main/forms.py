from django import forms
from .models import Account, Vendor

class RegisterForm(forms.ModelForm):
    phone = forms.CharField(max_length=19, widget=forms.TextInput(attrs={'placeholder':'Telefon Numarası','type':'tel'}))
    dob = forms.DateField(widget=forms.SelectDateWidget(years=range(2021,1900,-1)), label="Doğum Tarihi")
    name = forms.CharField(max_length=70, widget=forms.TextInput(attrs={'placeholder':'Ad'}))
    lastname = forms.CharField(max_length=70, widget=forms.TextInput(attrs={'placeholder':'Soyad'}))
    class Meta:
        model = Account
        fields = ('email', 'password')
        widgets = {
                   'email':forms.EmailInput(attrs={'placeholder':'E-posta Adresi'}),
                   'password':forms.PasswordInput(attrs={'placeholder':'Şifre'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        try:
            Account.objects.get(email=email)
        except Exception as e:
            return email
        raise forms.ValidationError(f"Bu email başka bir hesapta kullanılıyor.")
    
    def clean_phone(self):
        phone = self.cleaned_data['phone']
        try:
            Account.objects.get(phone=phone)
        except Exception as e:
            return phone
        raise forms.ValidationError(f"Bu telefon numarası başka bir hesapta kullanılıyor.")



class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder':'E-posta'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder':'Şifre'}))
    class Meta:
        fields =  ('email', 'password')


class VendorRegisterForm(forms.ModelForm):
    phone = forms.CharField(max_length=19, widget=forms.TextInput(attrs={'placeholder':'Telefon Numarası','type':'tel'}))
    fullname = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'placeholder':'Ad Soyad'}))
    companyName = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'placeholder':'Mağaza Adı'}))
    vergiDairesi = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'placeholder':'Vergi Dairesi'}))
    VKN = forms.CharField(max_length=11, widget=forms.TextInput(attrs={'placeholder':'VKN veya TCKN', 'inputmode':'numeric'}))
    country = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'placeholder':'Ülke'}))
    city = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'placeholder':'Şehir'}))
    address = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'placeholder':'Tam Adres'}))

    class Meta:
        model = Account
        fields = ('email', 'password')
        widgets = {
                   'email':forms.EmailInput(attrs={'placeholder':'E-posta Adresi'}),
                   'password':forms.PasswordInput(attrs={'placeholder':'Şifre'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        try:
            Account.objects.get(email=email)
        except Exception as e:
            return email
        raise forms.ValidationError(f"Bu email başka bir hesapta kullanılıyor.")
    
    def clean_phone(self):
        phone = self.cleaned_data['phone']
        try:
            Account.objects.get(phone=phone)
        except Exception as e:
            return phone
        raise forms.ValidationError(f"Bu telefon numarası başka bir hesapta kullanılıyor.")
    
    def clean_VKN(self):
        VKN = self.cleaned_data["VKN"]
        try:
            Vendor.objects.get(VKN=VKN)
        except Exception as e:
            if VKN.isnumeric():
                return VKN
            raise forms.ValidationError("Lütfen geçerli bir VKN/TCKN giriniz.")
        raise forms.ValidationError("Bu VKN/TCKN başka bir hesapta kullanılıyor.")