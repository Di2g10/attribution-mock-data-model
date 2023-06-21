"""Contains some example code for the project."""


def example(x: int) -> int:
    """Add one to the input.

    :param x: input expected to be any integer
    :return: x expected to be an integer.
    """
    x = x + 1
    return x


def _main():
    # example demonstrating function
    x = "Some input"
    print(f"input: {x} => {example(x)}")


if __name__ == "__main__":
    # To ensure this code is only run when this module is directly run.
    # And not executed when module is imported
    _main()
