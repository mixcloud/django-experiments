def chi_square_p_value(matrix):
    """
    Accepts a matrix (an array of arrays, where each child array represents a row)
    
    Example from http://math.hws.edu/javamath/ryan/ChiSquare.html:
    
    Suppose you conducted a drug trial on a group of animals and you
    hypothesized that the animals receiving the drug would survive better than
    those that did not receive the drug. You conduct the study and collect the
    following data:
    
    Ho: The survival of the animals is independent of drug treatment.
    
    Ha: The survival of the animals is associated with drug treatment.
    
    In that case, your matrix should be:
    [
     [ Survivors in Test, Dead in Test ],
     [ Survivors in Control, Dead in Control ]
    ]
    
    Code adapted from http://codecomments.wordpress.com/2008/02/13/computing-chi-squared-p-value-from-contingency-table-in-python/
    """
    try:
        from scipy.stats import chisqprob
    except ImportError:
        from experiments.stats import chisqprob
    num_rows = len(matrix)
    num_columns = len(matrix[0])
    
    # Sanity checking
    if num_rows == 0:
        return None
    for row in matrix:
        if len(row) != num_columns:
            return None
    
    row_sums = []
    # for each row
    for row in matrix:
        # add up all the values in the row
        row_sums.append(sum(row))
    
    column_sums = []
    # for each column i
    for i in range(num_columns):
        column_sum = 0.0
        # get the i'th value from each row
        for row in matrix:
            column_sum += row[i]
        column_sums.append(column_sum)
    
    # the total sum could be calculated from either the rows or the columns
    # coerce to float to make subsequent division generate float results
    grand_total = float(sum(row_sums))
    
    if grand_total <= 0:
        return None, None
    
    observed_test_statistic = 0.0
    for i in range(num_rows):
        for j in range(num_columns):
            expected_value = (row_sums[i]/grand_total)*(column_sums[j]/grand_total)*grand_total
            if expected_value <= 0:
                return None, None
            observed_value = matrix[i][j]
            observed_test_statistic += ((observed_value - expected_value)**2) / expected_value
            # See https://bitbucket.org/akoha/django-lean/issue/16/g_test-formula-is-incorrect
            #observed_test_statistic += 2 * (observed_value*log(observed_value/expected_value))


    degrees_freedom = (num_columns - 1) * (num_rows - 1)
    
    p_value = chisqprob(observed_test_statistic, degrees_freedom)

    return observed_test_statistic, p_value
