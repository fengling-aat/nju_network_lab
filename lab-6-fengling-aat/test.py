import time
localtime1 = time.asctime( time.localtime(time.time()))
print(localtime1)
x=0
for i in range(0,10000):
    x += 1
localtime2 = time.asctime( time.localtime(time.time()))
print(localtime2)
print(round(time.time(), 2))
