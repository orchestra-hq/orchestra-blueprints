def calculate_average(numbers):
    if not numbers:
        raise ValueError("Cannot calculate average of an empty list")
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)


def get_user_name(user):
    name = user.get("name")
    if name is None:
        raise KeyError("User dict is missing the 'name' key")
    return name.upper()
