def get_price_over_14_m3(usage: int) -> int | float:
    """
    Pass usage as liter
    :return price as int or float
    """
    # convert  liter to m3
    usage = usage / 1000
    if 0 < usage <= 5:
        return usage * 2824

    elif 5 < usage <= 10:
        return (usage * 4229) - 7025
    
    elif 10 < usage <= 14:
        return (usage * 5630) - 21035

    elif 14 < usage <= 21:
        return (usage * 16811) - 177569
    
    elif 21 < usage <= 28:
        return (usage * 25217) - 354085
    
    elif 28 < usage <= 42:
        return (usage * 50433) - 1060147

    elif 42 < usage <= 56:
        return (usage * 100866) - 3178333

    elif usage > 56:
        return (usage * 168110) - 6943997


def round_price(price: int) -> int:
    if price == 0:
        return 0

    if len(str(price)) <= 2:
        return 100

    else:
        # Delete last digit
        price //= 10
        if price % 10 >= 5:
            price //= 10
            price += 1
        else:
            price //= 10
        price *= 100
        return price
    