def emojify(anylist):
    for i in range(len(anylist)):
        if anylist[i][1] == True:
            anylist[i][1] = '\U00002705'
        else:
            anylist[i][1] = '\U0000274c'
    return anylist


def tabify(anylist):
    sReturn = '\n'
    noOfColumn = 4
    length = (int(len(anylist)/noOfColumn))
    for i in range(length):
        for n in range(noOfColumn):
            sReturn += '{:4s}{:1}{:2}'.format(str(i+1+length*n)+'.', str(anylist[i+length*n][0]), str(anylist[i+length*n][1]))
        sReturn += '\n'
    sReturn += "105.{}{}".format(anylist[104][0], anylist[104][1])
    return sReturn


def getSolid(anylist):
    anylist = emojify(anylist)
    anylist = tabify(anylist)
    return anylist
#    ✅ = \U00002714
#    ❌ = \U0000274c
