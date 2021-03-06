from . qc_parser import QCParser
from . codegens import PythonCodegen, \
    MatlabCodegen, \
    C_Codegen, \
    PythonOperatorCodegen
from . helpers import profile, default_locals
from . exceptions import DCPError, QCMLException
from . ast.expressions import Variable
from . ast import NodeVisitor
import sys

PARSE, CANONICALIZE, CODEGEN, COMPLETE = range(4)

SUPPORTED_LANGUAGES = {
    "C": C_Codegen,
    "python": PythonCodegen,
    "operator": PythonOperatorCodegen,
    "matlab": MatlabCodegen
}

# TODO: add test cases for ensuring that errors are properly triggered in
# all cases
# TODO: what happens when the transformed code has offsets, etc?

class QCML(object):
    def __init__(self, debug = False):
        self.debug = debug
        self.state = PARSE

        self.program = None
        self.__codegen = None

        # keep track of the codegen language
        self.language = ""

    @property
    def prob2socp(self):
        return self.__codegen.prob2socp

    @property
    def socp2prob(self):
        return self.__codegen.socp2prob

    @profile
    def parse(self, text):
        """ Parse state enum.

            The parser moves from the EMPTY to the PARSED to the CANONICALIZED to
            the CODEGEN state.
        """
        self.program = QCParser().parse(text)
        if self.debug:
            self.program.show(buf=sys.stdout)

        if not self.program.is_dcp:
            # TODO: if debug, walk the tree and find the problem
            raise DCPError("QCML parse: The problem is not DCP compliant.")
        self.state = CANONICALIZE

    @profile
    def canonicalize(self):
        if self.state > CANONICALIZE: return
        if self.state is PARSE:
            raise QCMLException("QCML canonicalize: No problem currently parsed.")

        self.program.canonicalize()
        if self.debug:
            self.program.show(buf=sys.stdout)
        self.state = CODEGEN

    @property
    def dims(self):
        return self.program.dimensions

    @dims.setter
    def dims(self, dims):
        if self.state is PARSE:
            raise QCMLException("QCML set_dims: No problem currently parsed.")

        self.program.dimensions = dims

        if self.state is COMPLETE:
            self.state = CODEGEN

    @profile
    def codegen(self, language="python"):
        if self.state is COMPLETE:
            self.state = CODEGEN
        if self.state is PARSE:
            raise QCMLException("QCML codegen: No problem currently parsed.")
        if self.state is CANONICALIZE:
            raise QCMLException("QCML codegen: No problem currently canonicalized.")

        try:
            codegen_class = SUPPORTED_LANGUAGES[language]
        except KeyError:
            raise QCMLException("QCML codegen: Invalid code generator. Must be one of: ", SUPPORTED_LANGUAGES.keys())
        else:
            self.__codegen = codegen_class()
            self.__codegen.visit(self.program)

        # generate the prob2socp and socp2prob functions
        self.__codegen.codegen()

        if self.debug and hasattr(self.prob2socp, 'numbered_source'):
            print self.prob2socp.numbered_source
            print
            print self.socp2prob.numbered_source
            print

        self.state = COMPLETE
        self.language = language    # set our language

    @profile
    def save(self, name = "problem"):
        """
            Saves the generated code into a folder with name `name`.
        """
        if self.state is COMPLETE:
            self.__codegen.save(name)
        else:
            raise QCMLException("QCML save: No generated code to save.")

    @property
    def solver(self):
        if self.language != "python":
            raise QCMLException("QCML solver: Cannot execute code generated in %s" % self.language)
        if self.state is not COMPLETE:
            raise QCMLException("QCML solver: No python code currently generated.")

        try:
            import ecos
        except ImportError:
            raise ImportError("QCML solver: To generate a solver, requires ecos.")

        def solve_func(params, dims):
            data = self.prob2socp(params, dims)
            sol = ecos.solve(**data)
            result = self.socp2prob(sol['x'], sol['y'], sol['z'], dims)
            result['info'] = sol['info']

            # set the objective value
            multiplier = self.__codegen.objective_multiplier
            offset = self.__codegen.objective_offset
            if isinstance(offset, str):
                # in this case, offset is likely python *code*
                offset = eval(offset)
            result['objval'] = multiplier * sol['info']['pcost'] + offset
            return result
        return solve_func

    @default_locals
    def solve(self, params, dims = None):
        """
            .solve(locals())
            .solve(params, dims)

            Assumes all matrices and vectors are cvxopt matrices.
        """
        # TODO: what happens if we call solve after codegen(C)?
        if self.state is PARSE:
            raise QCMLException("QCML solve: No problem currently parsed.")
        local_dims = dims if dims else params
        self.canonicalize()
        self.codegen("python")

        return self.solver(params, local_dims)

    # @property
    # def offset_and_multiplier(self):
    #     """
    #         Gets the offset and multiplier (+1 or -1) for converting the
    #         solver objective value into the desired objective value.

    #         Usually, the desired objective is
    #             multipler * solver objval + offset

    #         Returns (offset, multiplier).
    #     """
    #     return (self.__codegen.objective_offset, self.__codegen.objective_multiplier)

    def printsource(self):
        print '\n\n'.join(self.__codegen.source)

    def prettyprintsource(self):
        print '\n\n'.join(self.__codegen.numbered_source)
