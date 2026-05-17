"""stdin helpers with EOF-safe reads and gettext-friendly errors."""

from asteroidpy.interface._intl import translate


def prompt_line(message: str) -> str:
    try:
        return input(message)
    except EOFError:
        print("\n" + translate("End of input (EOF); exiting."))
        raise SystemExit(0) from None


def get_integer(message: str) -> int:
    while True:
        try:
            return int(prompt_line(message).strip())
        except ValueError:
            print(translate("You must enter an integer."))


def get_float(message: str) -> float:
    while True:
        try:
            return float(prompt_line(message).strip())
        except ValueError:
            print(translate("You must enter a number."))


def prompt_int_in_range(prompt: str, low: int, high: int) -> int:
    while True:
        value = get_integer(prompt)
        if low <= value <= high:
            return value
        print(
            translate("Enter an integer between {low} and {high}.").format(
                low=low,
                high=high,
            )
        )
