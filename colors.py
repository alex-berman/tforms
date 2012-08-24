import matplotlib.cm

def colors(n):
    return matplotlib.cm.get_cmap(name="jet", lut=n)(range(n))
