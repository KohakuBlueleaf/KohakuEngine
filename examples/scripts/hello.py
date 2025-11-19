"""Simple hello world example script."""

name = "World"
greeting = "Hello"


def main(excited=False):
    """Print greeting message."""
    msg = f"{greeting}, {name}"
    if excited:
        msg += "!"
    print(msg)
    return msg


if __name__ == "__main__":
    main()
