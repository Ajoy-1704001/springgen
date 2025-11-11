import sys
try:
    import pyfiglet
    from termcolor import colored
except ImportError:
    print("Please install required packages: pip install pyfiglet termcolor")
    sys.exit(1)


def print_banner():
    text = pyfiglet.figlet_format("SpringGen", font="slant")
    print(colored(text, "cyan"))
    print(colored("💡 Spring Boot CRUD Generator CLI\n", "yellow"))