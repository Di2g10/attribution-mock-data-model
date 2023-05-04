

def example(x: int) -> int:
    """
    Description of the function purpose goes here. This function does nothing but demonstrated how functions should be
    written
    :param x: input expected to be any integer
    :return: x expected to be an integer
    """
    x = x + 1
    return x


def _main():
    # example demonstrating function
    x = "Some input"
    print(f'input: {x} => {example(x)}')


if __name__ == '__main__':
    # To ensure this code is only run when this module is directly run. And now executed when module is imported
    _main()
