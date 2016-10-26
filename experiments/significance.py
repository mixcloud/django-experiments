from experiments.stats import zprob, chisqprob


def mann_whitney(a_distribution, b_distribution, use_continuity=True):
    """Returns (u, p_value)"""
    MINIMUM_VALUES = 20

    all_values = sorted(set(list(a_distribution) + list(b_distribution)))

    count_so_far = 0
    a_rank_sum = 0
    b_rank_sum = 0
    a_count = 0
    b_count = 0

    variance_adjustment = 0

    for v in all_values:
        a_for_value = a_distribution.get(v, 0)
        b_for_value = b_distribution.get(v, 0)
        total_for_value = a_for_value + b_for_value
        average_rank = count_so_far + (1 + total_for_value) / 2.0

        a_rank_sum += average_rank * a_for_value
        b_rank_sum += average_rank * b_for_value
        a_count += a_for_value
        b_count += b_for_value
        count_so_far += total_for_value

        variance_adjustment += total_for_value ** 3 - total_for_value

    if a_count < MINIMUM_VALUES or b_count < MINIMUM_VALUES:
        return 0, None

    a_u = a_rank_sum - a_count * (a_count + 1) / 2.0
    b_u = b_rank_sum - b_count * (b_count + 1) / 2.0

    small_u = min(a_u, b_u)
    big_u = max(a_u, b_u)

    # These need adjusting for the huge number of ties we will have
    total_count = float(a_count + b_count)
    u_distribution_mean = a_count * b_count / 2.0
    u_distribution_sd = (
        (a_count * b_count / (total_count * (total_count - 1))) ** 0.5 *
        ((total_count ** 3 - total_count - variance_adjustment) / 12.0) ** 0.5)

    if u_distribution_sd == 0:
        return small_u, None

    if use_continuity:
        # normal approximation for prob calc with continuity correction
        z_score = abs((big_u - 0.5 - u_distribution_mean) / u_distribution_sd)
    else:
        # normal approximation for prob calc
        z_score = abs((big_u - u_distribution_mean) / u_distribution_sd)

    return small_u, 1 - zprob(z_score)


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
        num_rows = len(matrix)
        num_columns = len(matrix[0])
    except TypeError:
        return None

    if num_rows != num_columns:
        return None

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
            expected_value = (row_sums[i] / grand_total) * (column_sums[j] / grand_total) * grand_total
            if expected_value <= 0:
                return None, None
            observed_value = matrix[i][j]
            observed_test_statistic += ((observed_value - expected_value) ** 2) / expected_value
            # See https://bitbucket.org/akoha/django-lean/issue/16/g_test-formula-is-incorrect
            #observed_test_statistic += 2 * (observed_value*log(observed_value/expected_value))

    degrees_freedom = (num_columns - 1) * (num_rows - 1)

    p_value = chisqprob(observed_test_statistic, degrees_freedom)

    return observed_test_statistic, p_value
