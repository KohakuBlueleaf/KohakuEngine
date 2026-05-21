"""Hello-world script. Run with `python hello.py` or `kogine run hello.py`."""

name = "World"
greeting = "Hello"


def main(excited: bool = False) -> str:
    msg = f"{greeting}, {name}"
    if excited:
        msg += "!"
    print(msg)
    return msg


if __name__ == "__main__":
    main()
