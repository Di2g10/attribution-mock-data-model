"""Basic quickstart including importing the internal tools package and showing expected structure of a project."""


def example_function(x: int) -> int:
    """Add one to the input.

    :param x: input expected to be any integer
    :return: x expected to be an integer.
    """
    return x + 1


if __name__ == "__main__":
    # To ensure this code is only run when this module is directly run.
    # And not executed when module is imported
    x = 1
    print(f"input: {x} => {example_function(x)}")
