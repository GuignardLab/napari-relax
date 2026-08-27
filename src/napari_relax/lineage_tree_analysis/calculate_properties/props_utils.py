from lineagetree import LineageTree
from collections.abc import Iterable, Callable



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
