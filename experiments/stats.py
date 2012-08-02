from math import fabs, exp, sqrt, log, pi

def flatten(iterable):
    for el in iterable:
        if isinstance(el, (list, tuple)):
            yield flatten(el)
        else:
            yield el

def mean(scores):
    scores = list(flatten(scores))
    try:
        return float(sum(scores)) / float(len(scores))
    except ZeroDivisionError:
        return float('NaN')

def isnan(value):
    try:
        from math import isnan
        return isnan(value)
    except ImportError:
        return isinstance(value, float) and value != value

def ss(inlist):
    """
    Squares each value in the passed list, adds up these squares and
    returns the result.
    
    Originally written by Gary Strangman.

    Usage:   lss(inlist)
    """
    ss = 0
    for item in inlist:
        ss = ss + item*item
    return ss

def var(inlist):
    """
    Returns the variance of the values in the passed list using N-1
    for the denominator (i.e., for estimating population variance).
    
    Originally written by Gary Strangman.
    
    Usage:   lvar(inlist)
    """
    n = len(inlist)
    if n <= 1:
        return 0.0
    mn = mean(inlist)
    deviations = [0]*len(inlist)
    for i in range(len(inlist)):
        deviations[i] = inlist[i] - mn
    return ss(deviations)/float(n-1)

def stdev(inlist):
    """
    Returns the standard deviation of the values in the passed list
    using N-1 in the denominator (i.e., to estimate population stdev).
    
    Originally written by Gary Strangman.
    
    Usage:   lstdev(inlist)
    """
    return sqrt(var(inlist))

def gammln(xx):
    """
    Returns the gamma function of xx.
        Gamma(z) = Integral(0,infinity) of t^(z-1)exp(-t) dt.
    (Adapted from: Numerical Recipies in C.)
    
    Originally written by Gary Strangman.
    
    Usage:   lgammln(xx)
    """
    coeff = [76.18009173, -86.50532033, 24.01409822, -1.231739516,
             0.120858003e-2, -0.536382e-5]
    x = xx - 1.0
    tmp = x + 5.5
    tmp = tmp - (x+0.5)*log(tmp)
    ser = 1.0
    for j in range(len(coeff)):
        x = x + 1
        ser = ser + coeff[j]/x
    return -tmp + log(2.50662827465*ser)

def betacf(a,b,x):
    """
    This function evaluates the continued fraction form of the incomplete
    Beta function, betai.  (Adapted from: Numerical Recipies in C.)
    
    Originally written by Gary Strangman.
    
    Usage:   lbetacf(a,b,x)
    """
    ITMAX = 200
    EPS = 3.0e-7

    bm = az = am = 1.0
    qab = a+b
    qap = a+1.0
    qam = a-1.0
    bz = 1.0-qab*x/qap
    for i in range(ITMAX+1):
        em = float(i+1)
        tem = em + em
        d = em*(b-em)*x/((qam+tem)*(a+tem))
        ap = az + d*am
        bp = bz+d*bm
        d = -(a+em)*(qab+em)*x/((qap+tem)*(a+tem))
        app = ap+d*az
        bpp = bp+d*bz
        aold = az
        am = ap/bpp
        bm = bp/bpp
        az = app/bpp
        bz = 1.0
        if (abs(az-aold)<(EPS*abs(az))):
            return az
    print 'a or b too big, or ITMAX too small in Betacf.'

def betai(a,b,x):
    """
    Returns the incomplete beta function:
    
        I-sub-x(a,b) = 1/B(a,b)*(Integral(0,x) of t^(a-1)(1-t)^(b-1) dt)
    
    where a,b>0 and B(a,b) = G(a)*G(b)/(G(a+b)) where G(a) is the gamma
    function of a.  The continued fraction formulation is implemented here,
    using the betacf function.  (Adapted from: Numerical Recipies in C.)
    
    Originally written by Gary Strangman.
    
    Usage:   lbetai(a,b,x)
    """
    if (x<0.0 or x>1.0):
        raise ValueError, 'Bad x in lbetai'
    if (x==0.0 or x==1.0):
        bt = 0.0
    else:
        bt = exp(gammln(a+b)-gammln(a)-gammln(b)+a*log(x)+b*
                      log(1.0-x))
    if (x<(a+1.0)/(a+b+2.0)):
        return bt*betacf(a,b,x)/float(a)
    else:
        return 1.0-bt*betacf(b,a,1.0-x)/float(b)

def ttest_ind(a, b):
    """
    Calculates the t-obtained T-test on TWO INDEPENDENT samples of
    scores a, and b. Returns t-value, and prob.
    
    Originally written by Gary Strangman.
    
    Usage:   lttest_ind(a,b)
    Returns: t-value, two-tailed prob
    """
    x1, x2 = mean(a), mean(b)
    v1, v2 = stdev(a)**2, stdev(b)**2
    n1, n2 = len(a), len(b)
    df = n1+n2-2
    try:
        svar = ((n1-1)*v1+(n2-1)*v2)/float(df)
    except ZeroDivisionError:
        return float('nan'), float('nan')
    try:
        t = (x1-x2)/sqrt(svar*(1.0/n1 + 1.0/n2))
    except ZeroDivisionError:
        t = 1.0
    prob = betai(0.5*df,0.5,df/(df+t*t))
    return t, prob

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
        if y >= (Z_MAX*0.5):
            x = 1.0
        elif (y < 1.0):
            w = y*y
            x = ((((((((0.000124818987 * w
                        -0.001075204047) * w +0.005198775019) * w
                      -0.019198292004) * w +0.059054035642) * w
                    -0.151968751364) * w +0.319152932694) * w
                  -0.531923007300) * w +0.797884560593) * y * 2.0
        else:
            y = y - 2.0
            x = (((((((((((((-0.000045255659 * y
                             +0.000152529290) * y -0.000019538132) * y
                           -0.000676904986) * y +0.001390604284) * y
                         -0.000794620820) * y -0.002034254874) * y
                       +0.006549791214) * y -0.010557625006) * y
                     +0.011630447319) * y -0.009279453341) * y
                   +0.005353579108) * y -0.002141268741) * y
                 +0.000535310849) * y +0.999936657524
    if z > 0.0:
        prob = ((x+1.0)*0.5)
    else:
        prob = ((1.0-x)*0.5)
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
    if df%2 == 0:
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
                s = s + ex(c*z-a-e)
                z = z + 1.0
            return s
        else:
            if even:
                e = 1.0
            else:
                e = 1.0 / sqrt(pi) / sqrt(a)
            c = 0.0
            while (z <= chisq):
                e = e * (a/float(z))
                c = c + e
                z = z + 1.0
            return (c*y+s)
    else:
        return s
