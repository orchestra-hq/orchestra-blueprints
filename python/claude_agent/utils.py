def calculate_average(numbers):
    if not numbers:
        return 0
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)


def get_user_name(user):
    if not user or "name" not in user:
        return ""
    return user["name"].upper()
