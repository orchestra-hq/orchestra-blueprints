def calculate_average(numbers):
    """Calculate the average of a list of numbers.

    Iterates through the list and sums only numeric values (int or float),
    skipping any non-numeric elements. Returns 0.0 if the list is empty.

    Args:
        numbers: A list of values to average. Non-numeric items are ignored.

    Returns:
        float: The average of all numeric values in the list, or 0.0 if the
        list is empty.
    """
    if not numbers:
        return 0.0
    total = 0
    for num in numbers:
        if not isinstance(num, (int, float)):
            continue
        total += num
    return total / len(numbers)


def get_user_name(user):
    """Extract and return the uppercased name from a user dictionary.

    Validates that the input is a dict and that its "name" key holds a string
    value before returning the name in uppercase.

    Args:
        user: A dictionary expected to contain a "name" key with a string value.

    Returns:
        str | None: The user's name in uppercase if valid, or None if the input
        is not a dict, the "name" key is missing, or the name is not a string.
    """
    if not isinstance(user, dict):
        return None
    name = user.get("name")
    if name is None:
        return None
    if not isinstance(name, str):
        return None
    return name.upper()
