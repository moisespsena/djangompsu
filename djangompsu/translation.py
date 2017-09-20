def concat(*args):
    a = []
    for av in args:
        if isinstance(av, (tuple, list)):
            a.extend(concat(*av))
        else:
            a.append(av)
    return a
