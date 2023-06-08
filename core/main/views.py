from django.http import JsonResponse, HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.db.models import Q
from django.db import transaction
from django.contrib import messages
from django.core.exceptions import PermissionDenied, BadRequest, ObjectDoesNotExist
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from .cart import Cart
from .models import (Account, ProductVendorPrice, User, UserFavs, Product, ProductCategory, Vendor, UserAddress,
                      Order, OrderItem, OrderAddress, Discount, ProductImage, ProductSpecification, SpecificationValue,
                      VendorWallet, VendorTransaction, ProductRatings)
from .forms import RegisterForm, LoginForm, VendorRegisterForm
from .decorators import user_required, vendor_required
from io import BytesIO
import json
import re
import iyzipay
import xlsxwriter


def check_email(email):
    try:
        Account.objects.get(email=email)
    except:
        return True
    return False

def check_phone(phone):
    try:
        Account.objects.get(phone=phone)
    except:
        return True
    return False

def format_phone(phone):
    matches = re.match(r'^(((\+)?(90)|0)[-| ]?)?((\d{3})[-| ]?(\d{3})[-| ]?(\d{2})[-| ]?(\d{2}))$', phone)
    if matches:
        return "+90" + matches.group(5).replace(" ", "")
    return None

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def handler404(request, exception):
    return render(request, "404.html", status=404)

def register(request):
    if request.user.is_authenticated and not request.user.is_vendor:
        return redirect("index")
    form = RegisterForm()
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data.get("name")
            lastname = form.cleaned_data.get("lastname")
            email = form.clean_email().lower()
            dob = form.cleaned_data.get("dob")
            phone = format_phone(str(form.clean_phone()))
            if phone is None:
                messages.error(request, "Kayıt Başarısız: Telefon Numarası Yanlış Biçimde Girildi!")
                return redirect("register")
            
            newUser = Account(email=email, is_user=True, is_vendor=False)
            newUser.set_password(form.cleaned_data.get("password"))
            newUser.save()
            User.objects.create(user=newUser,name=name, lastname=lastname, dob=dob, phone=phone)
            login(request, newUser)
            messages.success(request, "Başarıyla kayıt oldunuz!")
            if "next" in request.GET:
                return redirect(request.GET.get("next"))
            return redirect("index")
        else:
            messages.warning(request, "Kayıt Başarısız! Bilgileri kontrol edip tekrar deneyiniz.")
            return render(request, "register.html",{"form":form})

    return render(request, "register.html", {"form":form})

def user_login(request):
    if request.user.is_authenticated and not request.user.is_vendor:
        return redirect("index")
    form = LoginForm(request.POST or None)
    if form.is_valid():
        email = form.cleaned_data.get("email").lower()
        password = form.cleaned_data.get("password")
        user = authenticate(email=email, password=password)
        if user is None:
            messages.warning(request, "Kullanıcı adı veya parola hatalı!")
            return render(request, "login.html",{"form":form})
        if user.is_vendor:
            messages.warning(request, "Satıcı hesabıyla giriş yapılamaz")
            return render(request, "login.html", {"form":form})
        messages.success(request, "Başarıyla giriş yaptınız.")
        login(request, user)
        if "next" in request.GET:
            return redirect(request.GET.get("next"))
        return redirect("index")
    return render(request, "login.html", {"form":form})

@login_required
def user_logout(request):
    logout(request)
    messages.success(request, "Başarıyla çıkış yaptınız.")
    return redirect("index")

def index(request):
    paginator = Paginator(Product.objects.all().order_by("-created_at"), 40)
    page_no = request.GET.get("page")
    return render(request, "index.html", {'page': paginator.get_page(page_no)})

def productDetail(request, slug):
    
    product = get_object_or_404(Product, slug=slug, is_active=True)
    if not product.product_vendors.exists():
        return redirect("index")
    context = {'product':product, 'comments':product.product_ratings.all().order_by("-created_at")}
    if "vendor" in request.GET:
        try:
            vendor = Vendor.objects.get(id=int(request.GET.get("vendor")))
            context["prdVendor"] = product.product_vendors.get(vendor=vendor)
        except:
            context["prdVendor"] = product.get_vendor_list()[0]
    else:
        context["prdVendor"] = product.get_vendor_list()[0]
    if request.user.is_authenticated and request.user.is_user:
        context["is_fav"] = True if request.user.user_account.user_favs.filter(product=product).exists() else False
    return render(request, "productDetail.html", context)

def checkSpecsStock(request, slug):
    if request.method == "GET":
        product = get_object_or_404(Product, slug=slug, is_active=True)
        specs = request.GET.get("specs")
        if not specs:
            return JsonResponse({"status":"fail"}, status=400)
        stock = sorted(product.product_vendors.filter(**{f"inventory__{specs}__gt":0}), key=lambda obj:obj.get_final_price())
        if stock:
            return JsonResponse({"bestvendor":stock[0].vendor.CompanyName,"bestprice":stock[0].get_final_price(),"best_total_price":stock[0].price,"best_vendor_id":stock[0].vendor.id,"best_vendor_disc":stock[0].discount.get_display_percent() if stock[0].discount else None,"vendors":[str(i.vendor.id) for i in stock]})
        else:
            return JsonResponse({"nostock":True})
    return HttpResponseForbidden()

def search(request):
    query = request.GET.get("q")
    if query:
        products = Product.objects.filter(Q(title__icontains=query)|Q(brand__icontains=query)|Q(desc__icontains=query)|Q(category__in=ProductCategory.objects.get_queryset_descendants(include_self=True, queryset=ProductCategory.objects._mptt_filter(name__icontains=query))))
        return render(request, "search.html", {"products":products})
    return redirect("index")

def categoryPage(request, slug):
    category = get_object_or_404(ProductCategory, slug=slug, is_active=True)
    products = Product.objects.filter(category__in=ProductCategory.objects.get(slug=slug).get_descendants(include_self=True)).order_by("-created_at")
    paginator = Paginator(products, 40)
    page_no = request.GET.get("page")
    return render(request, "categoryPage.html", {'category':category, 'page_products': paginator.get_page(page_no)})

@login_required
@user_required
def user_profile(request):
    if request.method == "POST":
        if 'email' in request.POST:
            user = request.user
            usermodel = request.user.user_account
            email = request.POST.get('email').lower()
            name = request.POST.get('firstname')
            lastname = request.POST.get('lastname')
            phone = request.POST.get('phone')
            phone = format_phone(str(phone)) if phone is not None else None
            dob_day = request.POST.get('dob_day')
            dob_month = request.POST.get('dob_month')
            dob_year = request.POST.get('dob_year')
            gender = request.POST.get('gender')
            
            if phone is None:
                messages.error(request, "HATA : Telefon Numarası Yanlış Biçimde Girildi!")
                return redirect("user-profile")


            if (email != user.email and not check_email(email)):
                messages.warning(request, "HATA : Bu E-Posta Adresi Kullanılıyor!")
                return redirect("user-profile")

            if (phone != usermodel.phone and not check_phone(phone)):
                messages.warning(request, "HATA : Bu Telefon Numarası Kullanılıyor!")
                return redirect("user-profile")

            if (all((email, name, lastname, phone, dob_day, dob_month, dob_year))):
                user.email = email
                usermodel.name = name
                usermodel.lastname = lastname
                usermodel.phone = phone
                usermodel.dob = date(int(dob_year),int(dob_month), int(dob_day))
                if gender != None:
                    usermodel.gender = gender
                user.save()
                usermodel.save()
                messages.success(request, "Değişiklikler Başarıyla Kaydedildi.")
                return redirect("user-profile")
            else:
                messages.warning(request, "HATA : BİLGİLER GÜNCELLENEMEDİ")
                return redirect("user-profile")

        else:
            if 'oldPassword' in request.POST:
                if (request.user.check_password(request.POST.get('oldPassword'))):
                    if len(request.POST.get('newPassword')) < 8:
                        messages.warning(request, "HATA: YENİ ŞİFRE EN AZ 8 KARAKTER OLMALIDIR!")
                        return redirect("user-profile")
                    request.user.set_password(request.POST.get('newPassword'))
                    request.user.save()
                    update_session_auth_hash(request, request.user)
                    messages.success(request, "Şifreniz Başarıyla Değiştirildi.")
                    return redirect("user-profile")
                else:
                    messages.warning(request, "HATA: HATALI ŞİFRE!")
                    return redirect("user-profile")

    return render(request, "userProfile.html")

@login_required
@user_required
def user_favs(request):
    return render(request, "favs.html", {"favs":UserFavs.objects.filter(user=request.user.user_account)})

@login_required
@user_required
def user_add_fav(request):
    if request.method == "POST":
        prd_id = request.POST.get("product")
        if prd_id and prd_id.isnumeric():
            try:
                prd = Product.objects.get(id=int(prd_id))
            except ObjectDoesNotExist:
                return JsonResponse({},status=400)
            UserFavs.objects.create(user=request.user.user_account, product=prd)
            return JsonResponse({"status":"success"})
        return JsonResponse({},status=400)
    return HttpResponseForbidden()

@login_required
@user_required
def user_remove_fav(request):
    if request.method == "POST":
        prd_id = request.POST.get("product")
        if prd_id and prd_id.isnumeric():
            try:
                fav = UserFavs.objects.get(user=request.user.user_account, product__id=int(prd_id))
            except ObjectDoesNotExist:
                return JsonResponse({}, status=400)
            fav.delete()
            return JsonResponse({"status":"success"})
    return HttpResponseForbidden()

def cart_detail(request):
    cart = Cart(request)
    return render(request, "cart.html", {'cart':cart})

def add_to_cart(request):
    if request.method == "POST":
        cart = Cart(request)
        product_id = int(request.POST.get("product_id"))
        product_qty = int(request.POST.get("quantity"))
        vendor = request.POST.get("vendor")
        product_specs = json.loads(request.POST.get("productspecs"))
        get_object_or_404(Product, id=product_id)
        add_st = cart.add(product_id=product_id, quantity=product_qty, vendor=vendor, **product_specs)
        if add_st == None:
            return JsonResponse({'status':'fail'}, status=400)
        return JsonResponse({'status':'success', 'quantity':add_st})
    raise PermissionDenied

def remove_from_cart(request):
    if request.method == "POST":
        cart = Cart(request)
        item_id = request.POST.get("item_id")
        cart.remove(item_id)
        return JsonResponse({'status':'success', 'quantity':len(cart), 'total_price':cart.get_total_cost()})

    raise PermissionDenied

def update_cart(request):
    if request.method == "POST":
        cart = Cart(request)
        item_id = request.POST.get("item_id")
        quantity = int(request.POST.get("quantity"))
        st = cart.update(item_id, quantity)
        if st == None:
            return JsonResponse({'status':'fail'}, status=400)
        return JsonResponse({'status':'success', 'quantity':len(cart), 'quantity_item': quantity,'item_total_price':cart.get_new_total(item_id), 'total_price':cart.get_total_cost()})

    raise PermissionDenied

def clear_cart(request):
    if request.method == "POST":
        cart = Cart(request)
        cart.clear()
        return JsonResponse({'status':'success'})
        
    raise PermissionDenied

@login_required
@user_required
def user_address(request):
    if request.method == "POST":
        title = request.POST.get('addressTitle')
        firstname = request.POST.get('addressName')
        lastname = request.POST.get('addressLastName')
        phone = request.POST.get('addressPhone')
        phone = format_phone(str(phone)) if phone is not None else None
        city = request.POST.get('addressCity')
        district = request.POST.get('addressDistrict')
        neighbor = request.POST.get('addressNeighbor')
        addressLine = request.POST.get('addressLine')
        tckn = request.POST.get('tckn')
        tckn = tckn if tckn is not None or tckn.isnumeric() else None
        if phone is None:
            messages.error(request, "HATA : Telefon Numarası Yanlış Biçimde Girildi!")
            next_url = request.GET.get("next", "user-address")
            return redirect(next_url)
        if not all((title, firstname, lastname, phone, city, district, neighbor, addressLine)):
            messages.error(request, "HATA : Eksik Bilgi!")
            next_url = request.GET.get("next", "user-address")
            return redirect(next_url)

        if 'adresId' in request.POST:
            address = get_object_or_404(UserAddress, id=int(request.POST.get("adresId")))
            if address.user == request.user.user_account:
                address.title = title
                address.name = firstname
                address.lastname = lastname
                address.phone = phone
                address.city = city
                address.district = district
                address.neighborhood = neighbor
                address.address = addressLine
                address.tckn = tckn
                address.save()
                messages.success(request, "Değişiklikler Başarıyla Kaydedildi.")
                return redirect("user-address")
            else:
                messages.warning(request, "HATA : BİLGİLER GÜNCELLENEMEDİ")
                return redirect("user-address")
        else:
            address = UserAddress()
            address.user = request.user.user_account
            address.title = title
            address.name = firstname
            address.lastname = lastname
            address.phone = phone
            address.city = city
            address.district = district
            address.neighborhood = neighbor
            address.address = addressLine
            address.tckn = tckn
            address.save()
            messages.success(request, "Yeni Adres Başarıyla Eklendi!")
            next_url = request.GET.get("next", "user-address")
            return redirect(next_url)

    return render(request, "userAddress.html")

@login_required
@user_required
def user_address_remove(request):
    if request.method == "POST":
        address = get_object_or_404(UserAddress, id=int(request.POST.get("adresId")))
        if address.user == request.user.user_account:
            address.delete()
            return JsonResponse({'status':'success'})
    
    raise PermissionDenied

@login_required
@user_required
def checkout(request):
    cart = Cart(request)
    if len(cart) == 0:
        messages.error(request, "Sepetinizde ürün bulunmamaktadır!")
        return redirect("index")
    
    if request.method == "POST":
        shipping_address = request.POST.get("shippingAddr")
        billing_address = request.POST.get("billingAddr")
        if all((shipping_address, billing_address)) and str(shipping_address).isdigit() and str(billing_address).isdigit():
            shipping_address = get_object_or_404(UserAddress, id=int(shipping_address), user=request.user.user_account)
            billing_address = get_object_or_404(UserAddress, id=int(billing_address), user=request.user.user_account)
            options = {
                'api_key': iyzipay.api_key, # ! iyzico api key
                'secret_key': iyzipay.secret_key, # ! iyzico secret key
                'base_url': 'sandbox-api.iyzipay.com'
            }

            buyer = {
                'id': request.user.user_account.id,
                'name': billing_address.name,
                'surname': billing_address.lastname,
                'email': request.user.email,
                'identityNumber': billing_address.tckn,
                'registrationAddress': billing_address.get_full_address(),
                'ip': get_client_ip(request),
                'city': billing_address.city,
                'country': 'Turkey'
            }

            payment_card = {
                'cardHolderName': request.POST.get('cc-name'),
                'cardNumber': request.POST.get('cc-number').replace(" ",""),
                'expireMonth': request.POST.get('cc-exp',"01/00")[:2],
                'expireYear': "20"+request.POST.get('cc-exp',"01/00")[3:],
                'cvc': request.POST.get('cc-cvc'),
                'registerCard': '0'
            }
            
            shipping = {
                'contactName': shipping_address.name,
                'city': shipping_address.city,
                'country': "Turkey",
                'address': shipping_address.get_full_address()
            }

            billing = {
                'contactName': billing_address.name,
                'city': billing_address.city,
                'country': "Turkey",
                'address': billing_address.get_full_address()
            }

            basket_items = [
                {
                    'id': item["id"],
                    'name':item["product"].title,
                    'category1':item["product"].category.name,
                    'itemType': 'PHYSICAL',
                    'price': str(item["product"].get_prdVendor(item["vendor"]).get_final_price()*item["quantity"])
                }
                for item in cart
            ]

            req = {
                'locale': 'tr',
                'price': str(cart.get_total_cost()),
                'paidPrice': str(cart.get_total_cost()),
                'currency': 'TRY',
                'installment': '1', # taksit kısmı ayarlanacak
                'paymentCard': payment_card,
                'buyer': buyer,
                'shippingAddress': shipping,
                'billingAddress': billing,
                'basketItems': basket_items,
                "callbackUrl": "http://127.0.0.1:8000/checkout",
            }

            payment = iyzipay.ThreedsInitialize().create(req, options)
            result = json.loads(payment.read().decode("utf-8"))

            if result["status"] == "success":
                with transaction.atomic():
                    teslimat = OrderAddress(user=request.user)
                    fatura = OrderAddress(user=request.user)
                    teslimat.name = shipping_address.name
                    teslimat.lastname = shipping_address.lastname
                    teslimat.phone = shipping_address.phone
                    teslimat.title = shipping_address.title
                    teslimat.city = shipping_address.city
                    teslimat.district = shipping_address.district
                    teslimat.neighborhood = shipping_address.neighborhood
                    teslimat.address = shipping_address.address
                    teslimat.tckn = shipping_address.tckn
                    
                    fatura.name = billing_address.name
                    fatura.lastname = billing_address.lastname
                    fatura.phone = billing_address.phone
                    fatura.title = billing_address.title
                    fatura.city = billing_address.city
                    fatura.district = billing_address.district
                    fatura.neighborhood = billing_address.neighborhood
                    fatura.address = billing_address.address
                    fatura.tckn = billing_address.tckn
                    teslimat.save()
                    fatura.save()

                    newOrder = Order(user=request.user)
                    newOrder.deliveryAddress = teslimat
                    newOrder.billingAddress = fatura
                    newOrder.save()
                    payVendors = dict()
                    for item in cart:
                        newItem = OrderItem(order=newOrder)
                        newItem.product = item["product"]
                        newItem.vendor = get_object_or_404(Vendor, id=item["vendor"])
                        newItem.specs = item["specs"]
                        newItem.quantity = item["quantity"]
                        prdVendor = item["product"].get_prdVendor(item["vendor"])
                        key = "-".join(newItem.specs.values()) if newItem.specs else ""
                        if int(prdVendor.inventory[key])-newItem.quantity >= 0:
                            prdVendor.inventory[key] = str(int(prdVendor.inventory[key])-newItem.quantity)
                            prdVendor.save()
                        else:
                            messages.error(request, "Sipariş başarısız! " + newItem.product.title + " yetersiz stok!")
                            del newItem
                            newOrder.delete()
                            fatura.delete()
                            teslimat.delete()
                            return redirect("cart-detail")
                        newItem.totalPrice = item["product"].get_prdVendor(item["vendor"]).get_final_price()*newItem.quantity
                        payVendors[newItem.vendor] = newItem.totalPrice + payVendors[newItem.vendor] if newItem.vendor in payVendors else newItem.totalPrice
                        newItem.save()
                    for vnd, totals in payVendors.items():
                        vndWlt = get_object_or_404(VendorWallet, vendor=vnd)
                        newTransaction = VendorTransaction(vendor=vnd)
                        newTransaction.transactionType = '1'
                        newTransaction.amount = totals - totals*Decimal('0.05') # ! Komisyon oranı 0.05
                        newTransaction.info = f'{newOrder.id} numaralı siparişten kazancınız'
                        newTransaction.save()
                        vndWlt.balance += newTransaction.amount
                        vndWlt.save()
                cart.clear()
                request.session["newOrderNo"] = newOrder.id
                return redirect("order-success")
            else:
                messages.error(request, "Ödeme başarısız! "+ result["errorCode"] + ": " + result["errorMessage"])
                return redirect("checkout")
        else:
            messages.error(request, "Hata: Geçersiz adres.")
            return redirect("checkout")

        
    return render(request, "checkout.html", {'cart':cart})


@login_required
@user_required
def user_orders(request):
    if "filtre" in request.GET:
        filtre = request.GET.get("filtre")
        if filtre and filtre in ["4","5","6"]:
            orders = Order.objects.filter(id__in=[i.id for i in Order.objects.all() if i.is_all_status(filtre)]).order_by("-created_at")
    else:
        orders = Order.objects.filter(user=request.user, is_active=True).order_by("-created_at")

    return render(request, "userOrders.html", {'orders':orders})

@login_required
@user_required
def user_order_detail(request, ordNo):
    order = get_object_or_404(Order, id=ordNo, user=request.user, is_active=True)
    if not order.is_active:
        messages.warning(request, "Bu siparişe erişilemez.")
        return redirect("user-orders")
    if request.method == "POST":
        cancelItems = [item[11:] for item in request.POST if item.startswith("cancelItem-") and request.POST.get(item)=="on"]
        if len(cancelItems) == 0:
            messages.warning(request, "Lütfen iptal etmek istediğiniz ürünleri seçiniz!")
            return render(request, "userOrderDetail.html", {'order': order})

        for item in cancelItems:
            selectedItem = get_object_or_404(OrderItem, id=item, order=order)
            selectedItem.status = "6"
            selectedItem.save()
            vndWlt = get_object_or_404(VendorWallet, vendor=selectedItem.vendor)
            newTransaction = VendorTransaction(vendor=selectedItem.vendor)
            newTransaction.transactionType = '2'
            newTransaction.amount = selectedItem.totalPrice - selectedItem.totalPrice*Decimal('0.05')
            newTransaction.info = f'İptal edilen ürünler'
            newTransaction.save()
            vndWlt.balance -= newTransaction.amount
            vndWlt.save()

        messages.success(request, "Seçtiğiniz ürünler iptal edildi.")

    return render(request, "userOrderDetail.html", {'order': order})

@login_required
@user_required
def orderAddRating(request):
    if request.method == "POST":
        itemId = request.POST.get("itemId")
        rating = request.POST.get("rating")
        comment = request.POST.get("comment", "")
        if (itemId and rating and rating.isnumeric()):
            try:
                item = OrderItem.objects.get(id=int(itemId))
            except ObjectDoesNotExist:
                return JsonResponse({"status":"fail"}, status=404)
            newPrdRating = ProductRatings(user=request.user.user_account)
            newPrdRating.product = item.product
            newPrdRating.vendor = item.vendor
            newPrdRating.order = item
            newPrdRating.rating = int(rating)
            newPrdRating.comment = comment
            newPrdRating.save()
            return JsonResponse({"status":"success"})
        return JsonResponse({"status":"fail"}, status=404)

    return HttpResponseForbidden()

@login_required
@user_required
def orderBuyAgain(request):
    if request.method == "POST":
        cart = Cart(request)
        itemId = int(request.POST.get("itemId"))
        orderItem = get_object_or_404(OrderItem, id=itemId)
        product_id = orderItem.product.id
        product_qty = orderItem.quantity
        vendor = str(orderItem.vendor.id)
        product_specs = orderItem.specs
        cart.add(product_id=product_id, quantity=product_qty, vendor=vendor, **product_specs)
        return JsonResponse({'status':'success'})
    return HttpResponseForbidden()

@login_required
@user_required
def orderRefundItem(request, ordNo):
    order = get_object_or_404(Order, id=ordNo, user=request.user, is_active=True)
    if not order.is_active:
        messages.warning(request, "Bu siparişe erişilemez.")
        return redirect("user-orders")
    if request.method == "POST":
        refundItems = [item[11:] for item in request.POST if item.startswith("refundItem-") and request.POST.get(item)=="on"]
        if len(refundItems) == 0:
            messages.warning(request, "Lütfen iade etmek istediğiniz ürünleri seçiniz!")
            return render(request, "userOrderDetail.html", {'order': order})

        for item in refundItems:
            selectedItem = get_object_or_404(OrderItem, id=item, order=order)
            selectedItem.status = "5"
            selectedItem.save()
            vndWlt = get_object_or_404(VendorWallet, vendor=selectedItem.vendor)
            newTransaction = VendorTransaction(vendor=selectedItem.vendor)
            newTransaction.transactionType = '2'
            newTransaction.amount = selectedItem.totalPrice - selectedItem.totalPrice*Decimal('0.05')
            newTransaction.info = f'İade edilen ürünler'
            newTransaction.save()
            vndWlt.balance -= newTransaction.amount
            vndWlt.save()

        messages.success(request, "Seçtiğiniz ürünler iade edildi.")
        return redirect("user-order-detail", ordNo=order.id)
    return HttpResponseForbidden()

@login_required
@user_required
def orderSuccess(request):
    if "newOrderNo" in request.session:
        ordNo = request.session["newOrderNo"]
        del request.session["newOrderNo"]
        return render(request, "orderSuccess.html", {"ordNo": ordNo})
    return redirect("index")

def satici(request):
    if request.user.is_authenticated and request.user.is_vendor:
        return redirect("vendorPanel")
    return redirect("vendorLogin")

def vendorLogin(request):
    if request.user.is_authenticated and not request.user.is_user:
        return redirect("vendorPanel")
    form = LoginForm(request.POST or None)
    if form.is_valid():
        email = form.cleaned_data.get("email").lower()
        password = form.cleaned_data.get("password")
        user = authenticate(email=email, password=password)
        if user is None or user.is_user:
            messages.warning(request, "Kullanıcı adı veya parola hatalı!")
            return render(request, "vendorLogin.html",{"form":form})
        messages.success(request, "Başarıyla giriş yaptınız.")
        login(request, user)
        if "next" in request.GET:
            return redirect(request.GET.get("next"))
        return redirect("vendorPanel")
    return render(request, "vendorLogin.html", {"form":form})

def vendorRegister(request):
    if request.user.is_authenticated and not request.user.is_user:
        return redirect("vendorPanel")
    form = VendorRegisterForm()
    if request.method == "POST":
        form = VendorRegisterForm(request.POST)
        if form.is_valid():
            fullname = form.cleaned_data.get("fullname")
            email = form.clean_email().lower()
            phone = format_phone(str(form.clean_phone()))
            companyName = form.cleaned_data.get("companyName")
            vergiDairesi = form.cleaned_data.get("vergiDairesi")
            VKN = form.clean_VKN()
            country = form.cleaned_data.get("country")
            city = form.cleaned_data.get("city")
            address = form.cleaned_data.get("address")
            if phone is None:
                messages.error(request, "Kayıt Başarısız: Telefon Numarası Yanlış Biçimde Girildi!")
                return redirect("vendorRegister")
            
            newUser = Account(email=email, is_user=False, is_vendor=True)
            newUser.set_password(form.cleaned_data.get("password"))
            newUser.save()
            newVendor = Vendor.objects.create(user=newUser, ContactFullName=fullname, CompanyName=companyName,
            VergiDairesi=vergiDairesi, VKN=VKN, ContactPhone=phone, country=country, city=city, address=address)
            VendorWallet.objects.create(vendor=newVendor)
            login(request, newUser)
            messages.success(request, "Başarıyla kayıt oldunuz!")
            if "next" in request.GET:
                return redirect(request.GET.get("next"))
            return redirect("vendorPanel")
        else:
            messages.warning(request, "Kayıt Başarısız! Bilgileri kontrol edip tekrar deneyiniz.")
            return render(request, "vendorRegister.html",{"form":form})

    return render(request, "vendorRegister.html", {'form':form})

@login_required(login_url="/satici/login")
def vendor_logout(request):
    logout(request)
    messages.success(request, "Başarıyla çıkış yaptınız.")
    return redirect("vendorLogin")

@login_required(login_url="/satici/login")
@vendor_required
def vendorPanel(request):
    month_names = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
    today = date.today()
    sales = request.user.vendor_account.get_ordered_items()
    sales_stat = len(sales.filter(order__created_at__date=today))
    earn_stat = request.user.vendor_account.vendor_transaction.filter(Q(created_at__month=today.month)&Q(created_at__year=today.year))
    earn_stat = sum([i.amount if i.transactionType=='1' else -i.amount for i in earn_stat])
    graph_date_range = [today-relativedelta(months=i) for i in range(11,-1,-1)]
    graph_stat = {month_names[j.month-1]:len(sales.filter(Q(order__created_at__month=j.month)&Q(order__created_at__year=j.year))) for j in graph_date_range}
    return render(request, "vendorPanel.html",{"sells":sales_stat, "earn":earn_stat, "graph_stat":graph_stat})

@login_required(login_url="/satici/login")
@vendor_required
def getVendorSellStats(request):
    filtre = request.GET.get("q")
    if filtre:
        today = date.today()
        if filtre=="0":
            sell_stat = len(request.user.vendor_account.order_vendor.filter(order__created_at__date=today))
        elif filtre=="1":
            sell_stat = len(request.user.vendor_account.order_vendor.filter(Q(order__created_at__month=today.month)&Q(order__created_at__year=today.year)))
        elif filtre=="2":
            sell_stat = len(request.user.vendor_account.order_vendor.filter(order__created_at__year=today.year))
        else:
            return JsonResponse({}, status=400)
        
        return JsonResponse({"stat":sell_stat})
    
    return JsonResponse({}, status=400)

@login_required(login_url="/satici/login")
@vendor_required
def getVendorIncomeStats(request):
    filtre = request.GET.get("q")
    if filtre:
        today = date.today()
        if filtre=="0":
            earn = request.user.vendor_account.vendor_transaction.filter(created_at__date=today)
        elif filtre=="1":
            earn = request.user.vendor_account.vendor_transaction.filter(Q(created_at__month=today.month)&Q(created_at__year=today.year))
        elif filtre=="2":
            earn = request.user.vendor_account.vendor_transaction.filter(created_at__year=today.year)
        else:
            return JsonResponse({},status=400)
        
        income_stat = sum([i.amount if i.transactionType=='1' else -i.amount for i in earn])
        return JsonResponse({"stat":income_stat})
    
    return JsonResponse({},status=400)

@login_required(login_url="/satici/login")
@vendor_required
def vendorProductList(request):
    if request.method == "POST":
        ind = request.POST.get("index")
        sort = request.POST.get("sort")
        query = request.POST.get("search")
        if not ind: return BadRequest
        if ind == '0':
            indexFilter = request.user.vendor_account.products_on_sale.all()
        elif ind == '1':
            indexFilter = request.user.vendor_account.products_on_sale.filter(is_active=True)
        elif ind == '2':
            prd = request.user.vendor_account.products_on_sale
            indexFilter = prd.filter(id__in=[x.id for x in prd.all() if 0 in x.inventory.values()])
        elif ind == '3':
            indexFilter = request.user.vendor_account.products_on_sale.filter(is_active=False)
        else:
            return BadRequest

        if query:
            indexFilter = indexFilter.filter(Q(product__brand__icontains=query)|Q(product__title__icontains=query))

        if sort:
            if sort == '0':
                indexFilter = sorted(indexFilter, key=lambda obj:obj.get_final_price())
            elif sort == '1':
                indexFilter = sorted(indexFilter, key=lambda obj:obj.get_final_price(), reverse=True)
            elif sort == '2':
                indexFilter = indexFilter.order_by("-modified_at")
            elif sort == '3':
                indexFilter = indexFilter.order_by("modified_at")
            else:
                return BadRequest
        else:
            indexFilter = indexFilter.order_by("-modified_at")
        data = [{'index':i.id,'image':i.product.get_first_image().image.url if i.product.images.exists() else "", 'title':i.product.brand+" "+i.product.title,
                'price':i.get_final_price(), 'minprice':i.product.get_vendor_list()[0].get_final_price(),
                'date':i.modified_at, 'active':int(i.is_active)} for i in indexFilter]
        return JsonResponse({'data':data})

    return render(request, "vendorProductList.html", {"products":request.user.vendor_account.get_product_list().order_by("-modified_at"),"discounts":Discount.objects.filter(is_active=True).order_by("-modified_at")})

@login_required(login_url="/satici/login")
@vendor_required
def vendorProductListExcel(request):
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory':True})
    worksheet = workbook.add_worksheet('MyStoreÜrünListesi')
    worksheet.set_column('A:H',20)
    bold = workbook.add_format({'bold':True})
    products = request.user.vendor_account.get_product_list()
    row = 1
    col = 0
    for line in products:
        worksheet.write(row, col, line.product.brand+" "+line.product.title)
        worksheet.write(row, col+1, line.inventory[""] if len(line.inventory)==1 and "" in line.inventory else json.dumps(line.inventory))
        worksheet.write(row, col+2, line.price)
        worksheet.write(row, col+3, line.get_final_price())
        worksheet.write(row, col+4, line.discount.get_display_percent() if line.discount else "İNDİRİM YOK")
        worksheet.write(row, col+5, line.is_active)
        worksheet.write(row, col+6, datetime.strftime(timezone.localtime(line.created_at), "%d.%m.%Y %H:%M"))
        worksheet.write(row, col+7, datetime.strftime(timezone.localtime(line.modified_at), "%d.%m.%Y %H:%M"))
        row += 1
    
    worksheet.write('A1', 'Ürün Bilgisi', bold)
    worksheet.write('B1', 'Stok Adedi', bold)
    worksheet.write('C1', 'Fiyat', bold)
    worksheet.write('D1', 'İndirimli Fiyat', bold)
    worksheet.write('E1', 'İndirim', bold)
    worksheet.write('F1', 'Satışta', bold)
    worksheet.write('G1', 'Eklenme Zamanı', bold)
    worksheet.write('H1', 'Son Güncelleme', bold)
    workbook.close()
    output.seek(0)
    response = HttpResponse(output.read(), headers={
        'Content-Type': 'application/vnd.ms-excel',
        'Content-Disposition': 'attachment; filename="MyStoreÜrünListesi.xlsx"'
        })
    return response

@login_required(login_url="/satici/login")
@vendor_required
def vendorEditProduct(request, ind):
    if request.method == "GET":
        try:
            item = ProductVendorPrice.objects.get(vendor=request.user.vendor_account, id=ind)
        except ObjectDoesNotExist:
            return JsonResponse({"status":"fail"}, status=404)
        return JsonResponse({"price": item.price, "discount":item.discount.id if item.discount else "YOK", "is_active":item.is_active})
    elif request.method == "POST":
        try:
            item = ProductVendorPrice.objects.get(vendor=request.user.vendor_account, id=ind)
        except ObjectDoesNotExist:
            return JsonResponse({"status":"fail"}, status=404)
        newPrice = request.POST.get("newPrice")
        newDiscount = request.POST.get("newDiscount")
        saleActive = request.POST.get("saleActive")
        if all((newPrice, newDiscount)):
            if float(newPrice) < 0:
                return BadRequest
            with transaction.atomic():
                item.price = Decimal(newPrice)
                item.discount = Discount.objects.get(pk=int(newDiscount)) if newDiscount != "YOK" or newDiscount.isnumeric() else None
                item.is_active = True if saleActive == "true" else False
                item.save()
            return JsonResponse({"price":item.get_final_price(), "date":item.modified_at, "active":item.is_active})
        return JsonResponse({"status":"fail"}, status=400)
    return HttpResponseForbidden()

@login_required(login_url="/satici/login")
@vendor_required
def vendorAddProduct(request):
    if request.method == "POST":
        productTitle = request.POST.get("productTitle")
        productBrand = request.POST.get("productBrand")
        productCategory = request.POST.get("productCategory")
        productDesc = request.POST.get("productDesc")
        productImage = request.FILES.getlist("productImage")
        productPrice = request.POST.get("productPrice")
        productDiscount = request.POST.get("productDiscount")
        productStock = request.POST.get("productStock")
        productSpecName = request.POST.getlist("specName")
        productSpecValue = request.POST.getlist("specValue")
        if all((productTitle,productCategory,productPrice, productStock)):
            with transaction.atomic():
                newProduct = Product()
                newPrdVendor = ProductVendorPrice()
                newProduct.title = productTitle
                if productBrand:
                    newProduct.brand = productBrand
                newProduct.category = ProductCategory.objects.get(pk=int(productCategory))
                if productDesc:
                    newProduct.desc = productDesc
                newProduct.save()
                if not productImage:
                    newProductImage = ProductImage(product=newProduct)
                    newProductImage.is_first = True
                    newProductImage.save()
                for img in productImage:
                    newProductImage = ProductImage()
                    newProductImage.product = newProduct
                    newProductImage.image = img
                    newProductImage.alt_text = productTitle
                    newProductImage.save()
                if not newProduct.images.filter(is_first=True).exists():
                    setFirst = newProduct.images.first()
                    setFirst.is_first = True
                    setFirst.save()
                newPrdVendor.product = newProduct
                newPrdVendor.vendor = request.user.vendor_account
                newPrdVendor.inventory = json.loads(productStock)
                newPrdVendor.price = Decimal(productPrice)
                if productDiscount:
                    newPrdVendor.discount = Discount.objects.get(pk=int(productDiscount))
                newPrdVendor.save()
                if (productSpecName and productSpecValue) and len(productSpecName)==len(productSpecValue):
                    for i in range(len(productSpecName)):
                        newProductSpec = ProductSpecification()
                        newProductSpec.product = newProduct
                        newProductSpec.title = productSpecName[i]
                        newProductSpec.save()
                        for value in productSpecValue[i].split(","):
                            newPorductSpecValue = SpecificationValue()
                            newPorductSpecValue.specification = newProductSpec
                            newPorductSpecValue.value = value
                            newPorductSpecValue.save()
            messages.success(request, "Yeni ürün başarıyla eklendi.")
            return redirect("vendorProductList")
        
        messages.warning(request, "Lütfen gerekli alanları doldurunuz.")
        return redirect("vendorAddProduct")
                

    return render(request, "vendorProductAdd.html", {"categories": ProductCategory.objects.filter(is_active=True).order_by("name"), "discounts":Discount.objects.filter(is_active=True).order_by("-modified_at")})

@login_required(login_url="/satici/login")
@vendor_required
def vendorGetStock(request, ind):
    if request.method == "GET":
        prd = get_object_or_404(ProductVendorPrice, vendor=request.user.vendor_account, id=ind)
        specs = {spec.title:list(spec.specvalues.values_list("value",flat=True)) for spec in prd.product.get_specifications()}
        return JsonResponse({'specs':specs, 'stock':prd.inventory})
    
    return HttpResponseForbidden()

@login_required(login_url="/satici/login")
@vendor_required
def vendorUpdateStock(request):
    if request.method == "POST":
        stock = request.POST.get("stock")
        ind = request.POST.get("index")
        if not stock or not ind:
            return JsonResponse({"status":"fail"}, status=400)
        prd = get_object_or_404(ProductVendorPrice, vendor=request.user.vendor_account, id=int(ind))
        try:
            prd.inventory = json.loads(stock)
            prd.save()
        except ValueError as e:
            return JsonResponse({"status":"fail"}, status=400)
        return JsonResponse({"date":prd.modified_at})

    return HttpResponseForbidden()

@login_required(login_url="/satici/login")
@vendor_required
def vendorProfile(request):
    if request.method == "POST":
        if 'oldPass' in request.POST and 'newPass' in request.POST:
            if (request.user.check_password(request.POST.get('oldPass'))):
                if len(request.POST.get('newPass')) < 8:
                    messages.warning(request, "YENİ ŞİFRE EN AZ 8 KARAKTER OLMALIDIR!")
                    return redirect("vendorProfile")
                request.user.set_password(request.POST.get('newPass'))
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, "Şifreniz Başarıyla Değiştirildi.")
                return redirect("vendorProfile")
            else:
                messages.warning(request, "HATALI ŞİFRE!")
                return redirect("vendorProfile")
    return render(request, "vendorProfile.html", {"vendor":request.user.vendor_account})

@login_required(login_url="/satici/login")
@vendor_required
def vendorOrders(request):
    if "filtre" in request.GET:
        query = request.GET.get("filtre")
        if query not in ["1","2","3","4","5","6"]:
            return HttpResponseBadRequest()
        orders = {k:list(v) for k,v in request.user.vendor_account.get_group_orders().items() if all([i.status == query for i in v])}
    else:
        orders = request.user.vendor_account.get_group_orders()
    return render(request, "vendorOrders.html", {"orders":orders})

@login_required(login_url="/satici/login")
@vendor_required
def vendorOrderDetail(request, ordNo):
    order = get_object_or_404(Order, id=ordNo, is_active=True)
    if request.user.vendor_account.id not in order.order_items.values_list("vendor", flat=True):
        return HttpResponseForbidden()
    
    return render(request, "vendorOrderDetail.html", {"order":order, "items":request.user.vendor_account.order_vendor.filter(order=order)})

@login_required(login_url="/satici/login")
@vendor_required
def vendorOrderItemCancel(request, ordNo):
    if request.method == "POST":
        try:
            order = Order.objects.get(id=ordNo, is_active=True)
        except ObjectDoesNotExist:
            return JsonResponse({"status":"fail"}, status=404)
        if request.user.vendor_account.id not in order.order_items.values_list("vendor", flat=True):
            return HttpResponseForbidden()
        if "is_all" in request.POST:
            totals = 0
            for item in request.user.vendor_account.order_vendor.filter(order=order, status__in=["1","2"]):
                item.status = "6"
                item.save()
                totals += item.totalPrice
            totals -= Decimal(totals)*Decimal('0.05')
            vndWlt = get_object_or_404(VendorWallet, vendor=request.user.vendor_account)
            vndWlt.balance -= Decimal(totals)
            vndWlt.save()
            newTransaction = VendorTransaction(vendor=request.user.vendor_account)
            newTransaction.transactionType = '2'
            newTransaction.amount = totals
            newTransaction.info = f'{order.id} numaralı sipariş iptali'
            newTransaction.save()
            return JsonResponse({"status":"success"})
        else:
            itemId = int(request.POST.get("index"))
            try:
                item = request.user.vendor_account.order_vendor.get(order=order, id=itemId, status__in=["1","2"])
            except ObjectDoesNotExist:
                return JsonResponse({"status":"fail"}, status=404)
            item.status = "6"
            item.save()
            vndWlt = get_object_or_404(VendorWallet, vendor=request.user.vendor_account)
            newTransaction = VendorTransaction(vendor=request.user.vendor_account)
            newTransaction.transactionType = '2'
            newTransaction.amount = item.totalPrice - item.totalPrice*Decimal('0.05')
            newTransaction.info = f'Sipariş ürün iptali'
            newTransaction.save()
            vndWlt.balance -= Decimal(newTransaction.amount)
            vndWlt.save()
            return JsonResponse({"status":"success"})
    return HttpResponseForbidden()

@login_required(login_url="/satici/login")
@vendor_required
def vendorOrderItemChPrepared(request, ordNo):
    if request.method == "POST":
        try:
            order = Order.objects.get(id=ordNo, is_active=True)
        except ObjectDoesNotExist:
            return JsonResponse({"status":"fail"}, status=404)
        if request.user.vendor_account.id not in order.order_items.values_list("vendor", flat=True):
            return HttpResponseForbidden()
        if "is_all" in request.POST:
            for item in request.user.vendor_account.order_vendor.filter(order=order, status="1"):
                item.status = "2"
                item.save()
            return JsonResponse({"status":"success"})
        else:
            itemId = int(request.POST.get("index"))
            try:
                item = request.user.vendor_account.order_vendor.get(order=order, id=itemId, status="1")
            except ObjectDoesNotExist:
                return JsonResponse({"status":"fail"}, status=404)
            item.status = "2"
            item.save()
            return JsonResponse({"status":"success"})
    return HttpResponseForbidden()

@login_required(login_url="/satici/login")
@vendor_required
def vendorOrderItemCargo(request, ordNo):
    if request.method == "POST":
        try:
            order = Order.objects.get(id=ordNo, is_active=True)
        except ObjectDoesNotExist:
            return JsonResponse({"status":"fail"}, status=404)
        if request.user.vendor_account.id not in order.order_items.values_list("vendor", flat=True):
            return HttpResponseForbidden()
        if "cargoURL" in request.POST:
            if "index" in request.POST:
                itemId = int(request.POST.get("index"))
                try:
                    item = request.user.vendor_account.order_vendor.get(order=order, id=itemId)
                except ObjectDoesNotExist:
                    return JsonResponse({"status":"fail"}, status=404)
                item.deliveryURL = request.POST.get("cargoURL")
                item.status = "3"
                item.save()
                return JsonResponse({"status":"success"})
            elif "is_all" in request.POST:
                cargoURL = request.POST.get("cargoURL")
                for item in request.user.vendor_account.order_vendor.filter(order=order, status__in=["1","2"]):
                    item.deliveryURL = cargoURL
                    item.status = "3"
                    item.save()
                return JsonResponse({"status":"success"})

    return HttpResponseForbidden()

@login_required(login_url="/satici/login")
@vendor_required
def vendorSellProduct(request):
    if request.method == "POST":
        productPrice = request.POST.get("price")
        productDiscount = request.POST.get("discount")
        productStock = request.POST.get("stock")
        ind = request.POST.get("index")
        if all((ind,productPrice,productDiscount,productStock)) and ind.isnumeric():
            product = get_object_or_404(Product, id=int(ind))
            with transaction.atomic():
                newPrdVendor = ProductVendorPrice()
                newPrdVendor.product = product
                newPrdVendor.vendor = request.user.vendor_account
                newPrdVendor.inventory = json.loads(productStock)
                newPrdVendor.price = Decimal(productPrice)
                newPrdVendor.discount = Discount.objects.get(id=int(productDiscount)) if productDiscount != "YOK" and productDiscount.isnumeric() else None
                newPrdVendor.save()
            messages.success(request, "Ürün satışta!")
            return redirect("vendorSellProduct")
        return HttpResponseBadRequest()
    if "prd" in request.GET:
        try:
            item = Product.objects.get(id=int(request.GET.get("prd")))
            price = item.get_vendor_list()[0].get_final_price() if item.product_vendors.exists() else None
            specs = {spec.title:list(spec.specvalues.values_list("value",flat=True)) for spec in item.get_specifications()}
        except ObjectDoesNotExist:
            return JsonResponse({"status":"fail"}, status=404)
        return JsonResponse({"price":price,"specs":specs,"image":item.get_first_image().image.url,"link":item.get_absolute_url()})
    return render(request, "vendorSellProduct.html", {"discounts": Discount.objects.all().order_by("-modified_at")})

@login_required(login_url="/satici/login")
@vendor_required
def vendorSellSearch(request):
    if request.method == "GET":
        query = request.GET.get("query")
        if query:
            vendorItems = [item.product.id for item in request.user.vendor_account.get_product_list()]
            items = Product.objects.filter(Q(title__icontains=query)|Q(brand__icontains=query)|Q(desc__icontains=query)).exclude(id__in=vendorItems)
            return JsonResponse([{"id":item.id, "product":item.brand+" "+item.title} for item in items], safe=False)
        return JsonResponse({"status":"fail"}, status=400)
    return HttpResponseForbidden()

@login_required(login_url="/satici/login")
@vendor_required
def vendorWallet(request):
    try:
        wallet = VendorWallet.objects.get(vendor=request.user.vendor_account)
    except ObjectDoesNotExist:
        messages.error(request, "Ödeme hesabınız bulunmuyor!")
        return redirect("vendorSatici")
    return render(request, "vendorWallet.html", {"wallet":wallet,"transactions":VendorTransaction.objects.filter(vendor=request.user.vendor_account)})

