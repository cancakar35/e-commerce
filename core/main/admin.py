from django.contrib import admin

from .models import (Account, Discount, Product, ProductCategory, ProductImage,
                        ProductSpecification, SpecificationValue, UserAddress, Vendor,
                        ProductVendorPrice, Order, OrderItem, OrderAddress, User,
                        VendorWallet, VendorTransaction, ProductRatings)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'last_login')
    search_fields = ('email',)
    readonly_fields = ('id', 'date_joined', 'last_login')
    fieldsets = (
        ('Kullanıcı Bilgileri', {'fields':('id','email','date_joined','last_login')}),
        ('İzinler', {'fields':('is_user','is_vendor','is_admin','is_staff','is_active')}),
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'lastname', 'get_email', 'get_lastlogin')
    search_fields = ('name','lastname')
    readonly_fields = ('id', 'user', 'created_at', 'modified_at')

    @admin.display(description='Email')
    def get_email(self, obj):
        return obj.user.email

    @admin.display(description="Last Login")
    def get_lastlogin(self, obj):
        return obj.user.last_login

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('id', 'CompanyName', 'get_lastlogin')
    search_fields = ('VKN', 'CompanyName', 'ContactFullName')
    readonly_fields = ('id', 'user', 'created_at', 'modified_at')

    @admin.display(description="Last Login")
    def get_lastlogin(self, obj):
        return obj.user.last_login

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    search_fields = ('name',)

@admin.register(VendorWallet)
class VendorWalletAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_company_name')
    search_fields = ('id', 'get_company_name')
    readonly_fields = ('id', 'balance', 'vendor')

    @admin.display(description="Vendor CompanyName")
    def get_company_name(self, obj):
        return obj.vendor.CompanyName
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    

@admin.register(VendorTransaction)
class VendorTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_company_name')
    search_fields = ('id', 'get_company_name')
    readonly_fields = ('id', 'transactionType', 'amount', 'created_at', 'vendor')

    @admin.display(description="Vendor CompanyName")
    def get_company_name(self, obj):
        return obj.vendor.CompanyName
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
@admin.register(ProductRatings)
class ProductRatingsAdmin(admin.ModelAdmin):
    readonly_fields = ("product", "user", "vendor", "order", "created_at")

    def has_add_permission(self, request, obj=None):
        return False

admin.site.register(Product)
admin.site.register(ProductImage)
admin.site.register(ProductSpecification)
admin.site.register(SpecificationValue)
admin.site.register(Discount)
admin.site.register(UserAddress)
admin.site.register(ProductVendorPrice)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(OrderAddress)
