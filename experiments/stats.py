from math import fabs, exp, sqrt, log, pi


def zprob(z):
    """
    Returns the area under the normal curve 'to the left of' the given z value.
    Thus, 
        for z<0, zprob(z) = 1-tail probability
        for z>0, 1.0-zprob(z) = 1-tail probability
        for any z, 2.0*(1.0-zprob(abs(z))) = 2-tail probability
    Originally adapted from Gary Perlman code by Gary Strangman.

    Usage:   zprob(z)
    """
    Z_MAX = 6.0    # maximum meaningful z-value
    if z == 0.0:
        x = 0.0
    else:
        y = 0.5 * fabs(z)
        if y >= (Z_MAX * 0.5):
            x = 1.0
        elif (y < 1.0):
            w = y * y
            x = ((((((((0.000124818987 * w
                        - 0.001075204047) * w + 0.005198775019) * w
                      - 0.019198292004) * w + 0.059054035642) * w
                    - 0.151968751364) * w + 0.319152932694) * w
                  - 0.531923007300) * w + 0.797884560593) * y * 2.0
        else:
            y = y - 2.0
            x = (((((((((((((-0.000045255659 * y
                             + 0.000152529290) * y - 0.000019538132) * y
                           - 0.000676904986) * y + 0.001390604284) * y
                         - 0.000794620820) * y - 0.002034254874) * y
                       + 0.006549791214) * y - 0.010557625006) * y
                     + 0.011630447319) * y - 0.009279453341) * y
                   + 0.005353579108) * y - 0.002141268741) * y
                 + 0.000535310849) * y + 0.999936657524
    if z > 0.0:
        prob = ((x + 1.0) * 0.5)
    else:
        prob = ((1.0 - x) * 0.5)
    return prob


def chisqprob(chisq, df):
    """
    Returns the (1-tailed) probability value associated with the provided
    chi-square value and df.  
    
    Originally adapted from Gary Perlman code by Gary Strangman.
    
    Usage:   chisqprob(chisq,df)
    """
    BIG = 20.0

    def ex(x):
        BIG = 20.0
        if x < -BIG:
            return 0.0
        else:
            return exp(x)

    if chisq <= 0 or df < 1:
        return 1.0

    a = 0.5 * chisq
    if df % 2 == 0:
        even = 1
    else:
        even = 0
    if df > 1:
        y = ex(-a)
    if even:
        s = y
    else:
        s = 2.0 * zprob(-sqrt(chisq))
    if (df > 2):
        chisq = 0.5 * (df - 1.0)
        if even:
            z = 1.0
        else:
            z = 0.5
        if a > BIG:
            if even:
                e = 0.0
            else:
                e = log(sqrt(pi))
            c = log(a)
            while (z <= chisq):
                e = log(z) + e
                s = s + ex(c * z - a - e)
                z = z + 1.0
            return s
        else:
            if even:
                e = 1.0
            else:
                e = 1.0 / sqrt(pi) / sqrt(a)
            c = 0.0
            while (z <= chisq):
                e = e * (a / float(z))
                c = c + e
                z = z + 1.0
            return (c * y + s)
    else:
        return s
