from django.shortcuts import get_object_or_404
from itertools import groupby
from .models import Product

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get("cart")

        if not cart:
            cart = self.session["cart"] = {}
        
        self.cart = cart

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def __iter__(self):
        for item in self.cart.keys():
            self.cart[str(item)]['product'] = Product.objects.get(pk=self.cart[str(item)]['id'])
            self.cart[str(item)]['item_id'] = item
            
        for item in self.cart.values():
            item['total_price'] = item['product'].get_prdVendor(item["vendor"]).get_final_price() * item['quantity']
            yield item
    
    def add(self, product_id, quantity, vendor, **specs):
        item_id = str(product_id)
        if specs:
            item_id += "-" + "-".join(specs.values())
        
        if item_id not in self.cart:
            inv = get_object_or_404(Product, pk=product_id).get_prdVendor(vendor).inventory
            inv = inv["-".join(specs.values())] if specs else inv[""]
            if (quantity > int(inv)):
                return None
            self.cart[item_id] = {'id':product_id, 'quantity': quantity, 'vendor':vendor, 'specs':specs}

        else:
            if self.cart[item_id]['vendor'] == vendor:
                inv = get_object_or_404(Product, pk=product_id).get_prdVendor(vendor).inventory
                inv = inv["-".join(specs.values())] if specs else inv[""]
                if (self.cart[item_id]['quantity']+int(quantity) > int(inv)):
                    return None
                self.cart[item_id]['quantity'] += int(quantity)
            else:
                inv = get_object_or_404(Product, pk=product_id).get_prdVendor(vendor).inventory
                inv = inv["-".join(specs.values())] if specs else inv[""]
                if (quantity > int(inv)):
                    return None
                item_id += "-" + str(vendor).replace(" ", "")
                self.cart[item_id] = {'id':product_id, 'quantity': quantity, 'vendor':vendor, 'specs':specs}

        self.save()
        return self.cart[item_id]["quantity"]

    def update(self, item_id, quantity):
        item_id = str(item_id)

        if item_id in self.cart:
            inv = get_object_or_404(Product, pk=self.cart[item_id]['id']).get_prdVendor(self.cart[item_id]['vendor']).inventory
            inv = inv["-".join(self.cart[item_id]['specs'].values())] if self.cart[item_id]['specs'] else inv[""]
            if (quantity > int(inv)):
                return None
            self.cart[item_id]["quantity"] = int(quantity)
            self.save()
            return True
    
    def remove(self, item_id):
        item_id = str(item_id)
        if item_id in self.cart:
            del self.cart[item_id]
            self.save()

    def save(self):
        self.session["cart"] = self.cart
        self.session.modified = True
    
    def clear(self):
        del self.session["cart"]
        self.session.modified = True

    def get_total_cost(self):        
        return sum(item['quantity'] * get_object_or_404(Product, pk=item['id']).get_prdVendor(item["vendor"]).get_final_price() for item in self.cart.values())

    def get_new_total(self, item_id):
        return self.cart[item_id]['quantity']*get_object_or_404(Product, pk=self.cart[item_id]['id']).get_prdVendor(self.cart[item_id]["vendor"]).get_final_price()

    def get_items_vendor_group(self):
        for key, item in self.cart.items():
            item['product'] = Product.objects.get(pk=item['id'])
            item['item_id'] = key
            prdVendor = item['product'].get_prdVendor(item["vendor"])
            item['vendorName'] = prdVendor.vendor.CompanyName
            item['total_price'] =prdVendor.get_final_price() * item['quantity']
        item_list = {}
        for k,v in groupby(sorted(self.cart.values(), key=lambda k: k['vendor']), key=lambda k: k['vendor']):
            item_list[k] = list(v)
        return item_list

