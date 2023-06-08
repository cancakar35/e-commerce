from decimal import Decimal
from django.db import models
from django.urls import reverse
from mptt.models import MPTTModel, TreeForeignKey
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.template.defaultfilters import slugify
from random import randint
from itertools import groupby
from datetime import date


def unique_slugify(instance, new_slug=None):
    if new_slug is not None:
        slug = new_slug
    else:
        slug = slugify(instance.title)
    if instance.__class__.objects.filter(slug=slug).exists():
        new_slug = "{slug}-{rnd}".format(slug=slug,rnd=str(randint(0,9)))
        return unique_slugify(instance, new_slug)
    
    return slug

class Vendor(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="vendor_account", on_delete=models.CASCADE)
    ContactFullName = models.CharField(max_length=255)
    CompanyName = models.CharField(max_length=255, unique=True, null=False)
    VergiDairesi = models.CharField(max_length=128)
    VKN = models.CharField(max_length=11, unique=True)
    ContactPhone = models.CharField(max_length=16, unique=True, validators=[
      RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Telefon numarasını yanlis bicimde girdiniz."
      ),
    ],)
    country = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now=True, editable=False)

    REQUIRED_FIELDS = ['ContactFullName', 'CompanyName', 'VKN', 'VergiDairesi', 'ContactPhone',
    'country', 'city', 'address']

    def __str__(self):
        return self.CompanyName

    def get_address(self):
        return self.address + " " + self.city + " / " + self.country

    def get_product_list(self):
        return self.products_on_sale.all()
      
    def get_ordered_items(self):
        return self.order_vendor.all()
    
    def get_group_orders(self):
        return {k:list(v) for k,v in groupby(self.order_vendor.all().order_by("-order__created_at"),key=lambda k:k.order)}

class VendorWallet(models.Model):
    vendor = models.OneToOneField(Vendor, related_name="vendor_wallet", on_delete=models.CASCADE)
    balance = models.DecimalField(decimal_places=2, max_digits=18, null=False, default=0.00)

    def __str__(self):
        return self.vendor.CompanyName + " satıcı bakiyesi"

class VendorTransaction(models.Model):
    type_choices = (('1', "Giriş"),('2',"Çıkış"))
    vendor = models.ForeignKey(Vendor, related_name="vendor_transaction", on_delete=models.CASCADE)
    transactionType = models.CharField(max_length=1, choices=type_choices, null=False, blank=False)
    amount = models.DecimalField(decimal_places=2, max_digits=18, null=False)
    info = models.CharField(max_length=256, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return " ".join((self.vendor.CompanyName,self.created_at,"tarihli",self.amount,"TL işlemi"))
    
class ProductCategory(MPTTModel):
    name = models.CharField(verbose_name="Category Name", help_text="Required and unique", max_length=255, unique=True, null=False)
    desc = models.TextField(verbose_name="Category Description", max_length=512)
    slug = models.SlugField(verbose_name="Category Slug", max_length=255, unique=True, editable=False)
    parent = TreeForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now=True, editable=False)
    is_active = models.BooleanField(default=True)

    class MPTTMeta:
        order_insertion_by = ["name"]

    class Meta:
        verbose_name = ("Category")
        verbose_name_plural = ("Categories")

    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        return super(ProductCategory, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("category-page", kwargs={"slug": self.slug})

    def get_category_ancestors(self):
        return self.get_ancestors(include_self=True)
    

class Discount(models.Model):
    name = models.CharField(verbose_name="Discount Name", max_length=255, null=False)
    discount_percent = models.DecimalField(null=False, decimal_places=2, max_digits=5, validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('100.00'))])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name + " %" + str(round(self.discount_percent)) + " indirim"

    def get_display_percent(self):
        return "%" + str(round(self.discount_percent)) + " indirim"


class Product(models.Model):
    brand = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255, null=False, blank=False)
    desc = models.TextField(max_length=512, blank=True)
    slug = models.SlugField(max_length=255, unique=True, editable=False)
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = unique_slugify(self)
        return super(Product, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("product-detail", kwargs={"slug": self.slug})

    def get_vendor_list(self):
        return sorted(self.product_vendors.all(), key=lambda obj:obj.get_final_price())

    def get_prdVendor(self, vendor):
        return self.product_vendors.get(vendor=vendor)

    def get_first_image(self):
        for img in self.images.all():
            if img.is_first:
                return img
        return self.images.first()
    
    def get_images(self):
        return self.images.all()
    
    def get_specifications(self):
        return self.specifications.all()

    def get_category_ancestors(self):
        return self.category.get_ancestors(include_self=True)

class ProductVendorPrice(models.Model):
    product = models.ForeignKey(Product, related_name="product_vendors", on_delete=models.CASCADE)
    vendor = models.ForeignKey(Vendor, related_name="products_on_sale", on_delete=models.CASCADE)
    inventory = models.JSONField(null=False)
    price = models.DecimalField(decimal_places=2, max_digits=18, null=False)
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.vendor.CompanyName + " " + self.product.title

    def get_final_price(self):
        if self.discount == None:
            return self.price
        return round(self.price - (self.price * (self.discount.discount_percent/100)),2)
    

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(default='noimg.png')
    is_first = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.product.title + " " + "Image"

class ProductSpecification(models.Model):
    product = models.ForeignKey(Product, related_name='specifications', on_delete=models.CASCADE)
    title = models.CharField(max_length=24)

    def __str__(self):
        return self.product.title + " " + self.title + " Özelliği"
    
    def get_spec_values(self):
        return self.specvalues.all()

class SpecificationValue(models.Model):
    specification = models.ForeignKey(ProductSpecification, related_name='specvalues', on_delete=models.CASCADE)
    value = models.CharField(max_length=64)

    def __str__(self):
        return self.specification.title + " " + self.value
class MyAccountManager(BaseUserManager):
    def create_user(self, email, password=None):
        if not email:
            raise ValueError("Email adresi gereklidir.")
        user  = self.model(
                email=self.normalize_email(email),
            )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        user = self.create_user(
                email=self.normalize_email(email),
                password=password
            )
        user.is_user = True
        user.is_vendor = False
        user.is_admin = True
        user.is_staff=True
        user.is_superuser=True
        user.save(using=self._db)
        User.objects.create(user=user, name="Admin", lastname="Admin", phone="", dob=date(2000,1,1))
        return user

class Account(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(verbose_name='email', max_length=60, unique=True)
    is_user = models.BooleanField(default=False)
    is_vendor = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(verbose_name='date joined', auto_now_add=True)
    last_login = models.DateTimeField(verbose_name="last login", auto_now=True)

    USERNAME_FIELD = 'email'

    objects = MyAccountManager()

    def save(self, *args, **kwargs):
        if self.is_user and self.is_vendor:
            return
        super(Account, self).save(*args, **kwargs)

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return self.is_admin

class User(models.Model):
    genders = (('E','Erkek'),('K', 'Kadın'))
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="user_account", on_delete=models.CASCADE)
    name = models.CharField(max_length=70)
    lastname = models.CharField(max_length=70)
    dob = models.DateField(auto_now=False, auto_now_add=False, null=False)
    gender = models.CharField(max_length=1, choices=genders, null=True)
    phone = models.CharField(max_length=16, unique=True, validators=[
      RegexValidator(
        regex=r'^(((\+)?(90)|0)[-| ]?)?((\d{3})[-| ]?(\d{3})[-| ]?(\d{2})[-| ]?(\d{2}))$',
        message="Telefon numarasını yanlış biçimde girdiniz."
      ),
    ],)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now=True, editable=False)

    REQUIRED_FIELDS = ['name', 'lastname', 'phone']

    def __str__(self):
        return self.user.email

    def get_full_name(self):
        return self.name + " " + self.lastname

    def get_addresses(self):
        return self.user_address.all()

    def get_address(self, adresId):
        return self.user_address.get(pk=adresId)

class UserAddress(models.Model):
    user = models.ForeignKey(User, related_name='user_address', on_delete=models.CASCADE)
    name = models.CharField(max_length=70, default="")
    lastname = models.CharField(max_length=70, default="")
    phone = models.CharField(max_length=16, validators=[
      RegexValidator(
        regex=r'^(((\+)?(90)|0)[-| ]?)?((\d{3})[-| ]?(\d{3})[-| ]?(\d{2})[-| ]?(\d{2}))$',
        message="Telefon numarasını yanlis bicimde girdiniz."
      ),
    ],)
    title = models.CharField(max_length=64, default="Ev", null=False, blank=False)
    city = models.CharField(max_length=250, null=False, blank=False)
    district = models.CharField(max_length=250, null=False, blank=False)
    neighborhood = models.CharField(max_length=250, null=False, blank=False)
    address = models.TextField(max_length=250, null=False)
    tckn = models.CharField(max_length=11, null=False, blank=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now=True, editable=False)
    
    class Meta:
        verbose_name = "Kullanici Adresi"
        verbose_name_plural = "Kullanici Adresleri"

    def __str__(self):
        return self.name + " " + self.lastname + " " + self.title

    def get_full_address(self):
        return f"{self.address} {self.neighborhood}/{self.district}/{self.city}"
    
class UserFavs(models.Model):
    user = models.ForeignKey(User, related_name="user_favs", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    class Meta:
        ordering = ["-created_at"]


class OrderAddress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="user_order_address", on_delete=models.CASCADE)
    name = models.CharField(max_length=70, default="")
    lastname = models.CharField(max_length=70, default="")
    phone = models.CharField(max_length=16)
    title = models.CharField(max_length=64, null=False, blank=False)
    city = models.CharField(max_length=250, null=False, blank=False)
    district = models.CharField(max_length=250, null=False, blank=False)
    neighborhood = models.CharField(max_length=250, null=False)
    address = models.TextField(max_length=250, null=False)
    tckn = models.CharField(max_length=11, null=False, blank=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        verbose_name = "Siparis Adresi"
        verbose_name_plural = "Siparis Adresleri"


class Order(models.Model):
    status_choices = (("1","İşleme Alındı"),("2","Hazırlanıyor"),("3","Kargoya Verildi"),("4","Teslim Edildi"),("5","İade"), ("6", "İptal Edildi"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="user_order", on_delete=models.CASCADE)
    deliveryAddress = models.ForeignKey(OrderAddress, related_name="order_address_delivery", on_delete=models.RESTRICT)
    billingAddress = models.ForeignKey(OrderAddress, related_name="order_billing_address", on_delete=models.RESTRICT)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Siparis"
        verbose_name_plural = "Siparisler"

    def __str__(self):
        return self.user.email + " " + str(self.created_at) + " tarihli siparişi."

    def get_absolute_url(self):
        return reverse("user-order-detail", kwargs={"ordNo": self.id})

    def get_status_name(self, code):
        for i in self.status_choices:
            if i[0] == code:
                return i[1]
    
    def get_order_items(self):
        return self.order_items.all()

    def is_all_status(self, status):
        return all([item.status==status for item in self.order_items.all()])

    def get_total_status(self):
        items_status = [item.status for item in self.order_items.all()]
        if all(x==items_status[0] for x in items_status):
            if items_status[0] == "4":
                return "Teslim Edildi"
            elif items_status[0] == "3":
                return "Kargoya Verildi"
            elif items_status[0] == "5":
                return "İade Edildi"
            elif items_status[0] == "6":
                return "İptal Edildi"
                
        return "Devam Ediyor"

    def get_group_order_items(self):
        return {k:list(v) for k,v in groupby(self.order_items.all(), key=lambda x: x.vendor)}

    def get_total_quantity(self):
        return sum([item.quantity for item in self.order_items.all()])

    def get_total(self):
        return sum(self.order_items.values_list("totalPrice", flat=True))

class OrderItem(models.Model):
    status_choices = (("1","İşleme Alındı"),("2","Hazırlanıyor"),("3","Kargoya Verildi"),("4","Teslim Edildi"),("5","İade"), ("6", "İptal Edildi"))
    order = models.ForeignKey(Order, related_name="order_items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="order_product", on_delete=models.CASCADE)
    vendor = models.ForeignKey(Vendor, related_name="order_vendor", on_delete=models.CASCADE)
    specs = models.JSONField(null=True)
    totalPrice = models.DecimalField(decimal_places=2, max_digits=18, null=False)
    deliveryURL = models.URLField(max_length=500, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=1, choices=status_choices, default="1")

    class Meta:
        verbose_name = "Siparis Urunu"
        verbose_name_plural = "Siparis Urunleri"

    def __str__(self):
        return str(self.order.id) + " nolu sipariş " + str(self.quantity) + " adet " + self.product.title

    def get_status(self):
        for i in self.status_choices:
            if i[0] == self.status:
                return i[1]

    def get_specs_text(self):
        return "-".join(self.specs.values())

class ProductRatings(models.Model):
    product = models.ForeignKey(Product, related_name="product_ratings", on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name="user_product_ratings", on_delete=models.CASCADE)
    vendor = models.ForeignKey(Vendor, related_name="vendor_product_ratings", on_delete=models.CASCADE)
    order = models.OneToOneField(OrderItem, related_name="order_product_ratings", on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(default=5)
    comment = models.CharField(max_length=256, blank=True)
    created_at = models.DateField(auto_now_add=True, editable=False)

    class Meta:
        verbose_name = "Urun Degerlendirmesi"
        verbose_name_plural = "Urun Degerlendirmeleri"

    def __str__(self):
        return self.product.title + " urun degerlendirmesi"
    
    def get_masked_user_name(self):
        return self.user.name[0]+"*"*3 + " " + self.user.lastname[0]+"*"*3
    
    def get_pos_rating(self):
        return "*"*self.rating
    
    def get_neg_rating(self):
        return "*"*(5-self.rating)
