from lineagetree import LineageTree
from collections.abc import Iterable, Callable
import re


LINEAGETREE_RETURNS = {dict[int, float],dict[int, int], dict[int, float|int]}

def find_all_viable_methods(
    obj: object,
    returns: type | set[type] = LINEAGETREE_RETURNS,
) -> list[Callable]:
    funcs = []

    if isinstance(returns, type):
        returns = {returns}

    for method in dir(obj):
        func = getattr(obj, method)

        if not callable(func):
            continue

        annotations = getattr(func, "__annotations__", {})
        return_type = annotations.get("return")
        # print(method, return_type in returns)

        if isinstance(return_type, str):
            try:
                return_type = eval(
                    return_type,
                    {"LineageTree": LineageTree}
                )
            except (NameError, TypeError, SyntaxError):
                continue

        if return_type in returns:
            funcs.append(func)

    return funcs

def get_parameters_of_function(func: Callable):
    return {k:v for k,v in func.__annotations__.items() if k not in ["lT","return"] }


def get_parameter_doc(func, parameter: str) -> str | None:
    """Get the documentation for one parameter from a function's docstring.
    No idea how it works it's chatgpt code and I don't speak regex
    Practically it returns only the part of the docsting that is related to the parameter given"""
    doc = func.__doc__

    if not doc:
        return None

    pattern = rf"""
        ^\s*{re.escape(parameter)}\s*:\s*
        (.*?)
        (?=
            ^\s*\w[\w\s]*\s*:      # next parameter
            |^\s*Returns?\s*:      # Returns / Return
            |^\s*Returns?\s*$      # Returns / Return without :
            |\Z
        )
    """

    match = re.search(
        pattern,
        doc,
        re.MULTILINE | re.DOTALL | re.VERBOSE,
    )

    if not match:
        return None

    return match.group(1).strip()

def convert_to_title(name):
    return re.sub(r"_+", " ", name).title()