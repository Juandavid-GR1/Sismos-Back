def comparador_eventos(claveA, claveB):

    """
    Key comparator K=(P, M, I) for seismic events.
    It relies on the fact that Python natively compares tuples lexicographically;
    this function simply translates that result into the negative/zero/positive
    value expected by ArbolBST.
    """

    return (claveA > claveB) - (claveA < claveB)