import numpy as np
from . check_ecos import make_and_execute_ecos_solve


sum_lp = """
variable x(2)
minimize sum(2*x)
"""

sum_mat_lp = """
variable x(2)
parameter D(2,2)
minimize sum(D*x)
x >= 0
"""

sum_mat_lp_with_scale = """
variable x(2)
parameter D(2,2)
minimize sum(2*D*x)
x >= 0
"""


def python_parse_and_solve(prob):
    from .. qc_lang import QCML
    p = QCML(debug=True)
    p.parse(prob)
    D = np.eye(2)
    p.solve()
    return p

def C_parse_and_codegen(prob):
    from .. qc_lang import QCML
    p = QCML(debug=True)
    p.parse(prob)
    p.canonicalize()
    p.codegen("C")
    return p

def C_parse_and_solve(prob):
    p = C_parse_and_codegen(prob)
    p.save("test_problem")

    c_test_code = """
#include "test_problem.h"
#include "ecos.h"

int main(int argc, char **argv) {
    double Ddata[4] = {0.1,3.1};

    long Di[2] = {0,1};
    long Dj[2] = {0,1};

    qc_matrix D;

    D.v = Ddata; D.i = Di; D.j = Dj; D.nnz = 2;
    D.m = 2; D.n = 2;

    test_problem_params p;

    p.D = &D;

    qc_socp *data = qc_test_problem2socp(&p, NULL);

    // run ecos and solve it
    pwork *mywork = ECOS_setup(data->n, data->m, data->p,
        data->l, data->nsoc, data->q,
        data->Gx, data->Gp, data->Gi,
        data->Ax, data->Ap, data->Ai,
        data->c, data->h, data->b);

    if (mywork)
    {
        ECOS_solve(mywork);
        printf("Objective value at termination of C program is %f\\n", mywork->info->pcost);
        ECOS_cleanup(mywork, 0);
    }
    qc_socp_free(data);

    return 0;
}
"""
    objval = make_and_execute_ecos_solve("test_problem", c_test_code)
    assert objval == 0



def test_solves():
    yield python_parse_and_solve, sum_lp
    yield C_parse_and_codegen, sum_lp
    yield python_parse_and_solve, sum_mat_lp
    yield C_parse_and_codegen, sum_mat_lp
    yield C_parse_and_solve, sum_mat_lp
    yield python_parse_and_solve, sum_mat_lp_with_scale
    yield C_parse_and_codegen, sum_mat_lp_with_scale
    yield C_parse_and_solve, sum_mat_lp_with_scale
