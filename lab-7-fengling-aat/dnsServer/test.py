#!/usr/bin/python
import math
import re

f = open("dns_table.txt")
line = f.readline()
while(line):
    line = line[:len(line)-1]
    line = line.split(' ')
    print(line)
    line = f.readline()
f.close()

def cal(pointA,pointB):
    return (pointA[0]-pointB[0])**2 + (pointA[1]-pointB[1])**2
print(cal((4,3),(1,2)))

def match(str1,str2):
    if str1[0] != '*':
        return str1 == str2
    else:
        idx = str2.find('.')
        return str1[1:] == str2[idx:]

print(match('sda','sda'))
print(match('*.test','hhh.test'))

d = {1:2,3:4}
print(d[3])
print(4 in d.keys())

print("pass")

def match(str1,str2):
    temp1 = str1
    temp2 = str2
    if str1[len(str1)-1] == '.':
        temp1 = str1[:len(str1)-1]
    if str2[len(str2)-1] == '.':
        temp2 = str2[:len(str2)-1]
    print(temp1,temp2)
    if temp1[0] != '*':
        return temp1 == temp2
    else:
        idx = temp2.find('.')
        return temp1[1:] == temp2[idx:]

print(match('*.cncourse.org.',"test.cncourse.org"))
#print(re.search('test.cncourse.org.',"*.cncourse.org."))