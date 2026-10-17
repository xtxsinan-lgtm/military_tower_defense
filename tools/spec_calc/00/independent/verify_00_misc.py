import math
print("T12", 500/3.6, 1.5/60, 2*1200/3.6, 0.5*1*1000, 6.5*1000)
print("T13", math.ceil(6.000000000000001-1e-9), math.ceil(6.0000001-1e-9), math.floor(5.999999999999999+1e-9))
def brg(dx,dy):
    b=math.atan2(dx,dy)
    if b<0: b+=2*math.pi
    if b>=2*math.pi: b-=2*math.pi
    return b
print("T14", brg(0,10),brg(10,0),brg(0,-10),brg(-10,0),brg(10,10))
print("T34", 100+ 32768/65535*200, 100 + (300-100)*32768/65535)
