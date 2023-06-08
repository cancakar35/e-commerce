from django import template


register = template.Library()

@register.filter
def formatDisplayPrice(price):
    parts = str(price).split(".")
    try:
        parts[0] = '{:,}'.format(int(parts[0])).replace(',','.')
    except:
        return None
    return ",".join(parts)

@register.filter
def getVendorOrderStatus(itemlist):
    for i in itemlist:
        if i.status != itemlist[0].status:
            return "BEKLİYOR"     
    status = itemlist[0].status
    if status == "3":
        return "Kargoya Verildi"
    elif status == "4":
        return "Teslim Edildi"
    elif status == "5":
        return "İade Edildi"
    elif status == "6":
        return "İPTAL EDİLDİ"
    return "BEKLİYOR"

@register.filter
def getOrderItemsNumStatus(itemlist):
    return list(itemlist.values_list("status", flat=True))

