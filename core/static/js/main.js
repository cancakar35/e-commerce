function formatDisplayPrice(price) {
    var parts = price.toString().split(".");
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return parts.join(",");
}

function checkPhoneNumber(phone) {
    let re = /^(((\+)?(90)|0)[-| ]?)?((\d{3})[-| ]?(\d{3})[-| ]?(\d{2})[-| ]?(\d{2}))$/;
    return re.test(phone);
}

function checkURL(url) {
    let re = /^(http(s)?:\/\/.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)$/;
    return re.test(url);
}

function addToCart(token, product, amount, vendor, specs) {
    $.ajax({
        type: 'POST',
        url: '/cart/add',
        data: {
            product_id: product,
            quantity: amount,
            vendor: vendor,
            productspecs: JSON.stringify(specs),
            csrfmiddlewaretoken: token
        },
        success: function (json) {
            if (json.status == "success"){
                alert("Sepete Eklendi (" + json.quantity + ")");
            }
            else{
                alert("Yeterli Stok Yok");
            }
        } ,
        error: function (xhr, errmsg, err) {}
    });
}

const forceNumericInput = (event) => {
    if (!((event.key >= 0 && event.key <= 9) || (event.key == "Backspace"))) {
        event.preventDefault();
    }
}

const isNumericPhoneInput = (event) => {
	const key = event.key;
	return ((key >= 0 && key <= 9) || key == "+" || key == "(" || key == ")" || key == "-");
};

const isModifierKey = (event) => {
	const key = event.key;
	return (key == "Shift" || key === "Control" || key === "Enter") ||
		(key === "Backspace" || key === "Tab" || key === "Space" || key === "Delete") ||
		(key == "ArrowLeft" || key == "ArrowRight" || key == "Home" || key == "End") ||
		(
			(event.ctrlKey === true || event.metaKey === true) &&
			(key === "a" || key === "c" || key === "v" || key === "x" || key === "z")
		)
};

const enforceFormat = (event) => {
	if(!isNumericPhoneInput(event) && !isModifierKey(event)){
		event.preventDefault();
	}
};

function cc_expires_format(string) {
    return string.replace(
        /[^0-9]/g, ''
    ).replace(
        /^([2-9])$/g, '0$1'
    ).replace(
        /^(1{1})([3-9]{1})$/g, '0$1/$2'
    ).replace(
        /^0{1,}/g, '0'
    ).replace(
        /^([0-1]{1}[0-9]{1})([0-9]{1,2}).*/g, '$1/$2'
    );
}
