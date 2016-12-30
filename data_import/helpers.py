def is_upc_valid(upc):
    # upc should be an int, or something that can cast to an int
    try:
        upc = int(upc)
    except:
        return False

    # upc should be 12 digits long
    return len(str(upc)) == 12
