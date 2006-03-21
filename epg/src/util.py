
def cmp_channel(c1, c2):

    l1 = len(c1.tuner_id)
    l2 = len(c2.tuner_id)

    if l1 == 0:
        if l2 == 0:
            return 0
        else:
            return -1

    if l2 == 0:
        if l1 == 0:
            return 0
        else:
            return 1

    a = 0
    b = 0

    for t in c1.tuner_id:
        try:
            a = int(t)
            break
        except:
            if c1.tuner_id.index(t) < l1-1:
                # try next time
                continue
            else:
                break

    for t in c2.tuner_id:
        try:
            b = int(t)
            break
        except:
            if c2.tuner_id.index(t) < l2-1:
                # try next time
                continue
            else:
                break

    if a < b:
        return -1
    if a > b:
        return 1
    return 0
