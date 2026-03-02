def calculate_average(numbers):
    if not numbers:
        raise ValueError("Cannot calculate average of an empty list")
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)


def get_user_name(user):
    if user is None:
        raise ValueError("user cannot be None")
    name = user.get("name")
    if name is None:
        raise ValueError("user dict must contain a 'name' key with a non-None value")
    return name.upper()
