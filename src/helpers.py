""" A collection of utility and helper functions for QCML.
"""
import qcml, time

def use(attr):
    """ Use decorator.

        @use(attr)
        def f(x):
            ...

        This decorator checks if x has the attribute "attr". If it does, it will
        call f(x.attr). Otherwise, it will call f(x).
    """
    def wrap(func):
        def wrapped(arg):
            if hasattr(arg, attr):
                return func(getattr(arg, attr))
            else:
                return func(arg)
        return wrapped
    return wrap

# TODO: potentially move this code into the expressions.leaf code; do this
# accounting when creating new Variables
def _create_varname():
    """ Creates a new, temporary variable name; begins with underscore.
    """
    name = '_t' + str(qcml.QCRewriter.varcount)
    qcml.QCRewriter.varcount += 1
    return name

def create_variable(shape):
    """ Create a new variable.
    """
    v = qcml.ast.expressions.Variable(_create_varname(), shape)
    qcml.QCRewriter.new_variables[v.value] = v
    return v

def profile(func):
    """ Decorator for profiling functions.
    """
    def wrap(*args, **kwargs):
        start = time.clock()
        result = func(*args, **kwargs)
        elapsed = time.clock() - start
        print func.__name__, "took", elapsed, "secs"
        return result
    return wrap

def default_locals(func):
    """ Decorator that uses the local namespace for the arguments of the
        wrapped function.
    """
    def wrap(self, *args, **kwargs):
        if args or kwargs:
            result = func(self, *args, **kwargs)
        else:
            # get the local calling frame
            # http://stackoverflow.com/questions/6618795/get-locals-from-calling-namespace-in-python
            import inspect
            frame = inspect.currentframe()
            try:
                params_and_dims = frame.f_back.f_locals
            finally:
                del frame

            result = func(self, params_and_dims, params_and_dims)
        return result
    return wrap
