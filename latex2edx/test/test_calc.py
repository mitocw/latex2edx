""""
Unit tests for calc.py
"""

import latex2edx.python_lib.calc.calc as calc
import numpy
import unittest

# numpy's default behavior when it evaluates a function outside its domain
# is to raise a warning (not an exception) which is then printed to STDOUT.
# To prevent this from polluting the output of the tests, configure numpy to
# ignore it instead.
# See http://docs.scipy.org/doc/numpy/reference/generated/numpy.seterr.html
numpy.seterr(all='ignore')  # Also: 'ignore', 'warn' (default), 'raise'


class TestEvaluator(unittest.TestCase):
    """
    Run tests for calc.evaluator
    Go through all functionalities as specifically as possible--
    work from number input to functions and complex expressions
    Also test custom variable substitutions (i.e.
      `evaluator({'x':3.0}, {}, '3*x')`
    gives 9.0) and more.
    """

    def test_trig_functions(self):
        """
        Test the trig functions provided in calc.py

        which are: sin, cos, tan, arccos, arcsin, arctan
        """

        angles = ['-pi/4', '0', 'pi/6', 'pi/5', '5*pi/4', '9*pi/4', '1 + j']
        sin_values = [-0.707, 0, 0.5, 0.588, -0.707, 0.707, 1.298 + 0.635j]
        cos_values = [0.707, 1, 0.866, 0.809, -0.707, 0.707, 0.834 - 0.989j]
        tan_values = [-1, 0, 0.577, 0.727, 1, 1, 0.272 + 1.084j]
        # Cannot test tan(pi/2) b/c pi/2 is a float and not precise...

        self.assert_function_values('sin', angles, sin_values)
        self.assert_function_values('cos', angles, cos_values)
        self.assert_function_values('tan', angles, tan_values)

        # Include those where the real part is between -pi/2 and pi/2
        arcsin_inputs = ['-0.707', '0', '0.5', '0.588', '1.298 + 0.635*j']
        arcsin_angles = [-0.785, 0, 0.524, 0.629, 1 + 1j]
        self.assert_function_values('arcsin', arcsin_inputs, arcsin_angles)
        # Rather than a complex number, numpy.arcsin gives nan
        self.assertTrue(numpy.isnan(calc.evaluator({}, {}, 'arcsin(-1.1)')))
        self.assertTrue(numpy.isnan(calc.evaluator({}, {}, 'arcsin(1.1)')))

        # Include those where the real part is between 0 and pi
        arccos_inputs = ['1', '0.866', '0.809', '0.834-0.989*j']
        arccos_angles = [0, 0.524, 0.628, 1 + 1j]
        self.assert_function_values('arccos', arccos_inputs, arccos_angles)
        self.assertTrue(numpy.isnan(calc.evaluator({}, {}, 'arccos(-1.1)')))
        self.assertTrue(numpy.isnan(calc.evaluator({}, {}, 'arccos(1.1)')))

        # Has the same range as arcsin
        arctan_inputs = ['-1', '0', '0.577', '0.727', '0.272 + 1.084*j']
        arctan_angles = arcsin_angles
        self.assert_function_values('arctan', arctan_inputs, arctan_angles)

    def test_reciprocal_trig_functions(self):
        """
        Test the reciprocal trig functions provided in calc.py

        which are: sec, csc, cot, arcsec, arccsc, arccot
        """
        angles = ['-pi/4', 'pi/6', 'pi/5', '5*pi/4', '9*pi/4', '1 + j']
        sec_values = [1.414, 1.155, 1.236, -1.414, 1.414, 0.498 + 0.591j]
        csc_values = [-1.414, 2, 1.701, -1.414, 1.414, 0.622 - 0.304j]
        cot_values = [-1, 1.732, 1.376, 1, 1, 0.218 - 0.868j]

        self.assert_function_values('sec', angles, sec_values)
        self.assert_function_values('csc', angles, csc_values)
        self.assert_function_values('cot', angles, cot_values)

        arcsec_inputs = ['1.1547', '1.2361', '2', '-2', '-1.4142', '0.4983+0.5911*j']
        arcsec_angles = [0.524, 0.628, 1.047, 2.094, 2.356, 1 + 1j]
        self.assert_function_values('arcsec', arcsec_inputs, arcsec_angles)

        arccsc_inputs = ['-1.1547', '-1.4142', '2', '1.7013', '1.1547', '0.6215-0.3039*j']
        arccsc_angles = [-1.047, -0.785, 0.524, 0.628, 1.047, 1 + 1j]
        self.assert_function_values('arccsc', arccsc_inputs, arccsc_angles)

        # Has the same range as arccsc
        arccot_inputs = ['-0.5774', '-1', '1.7321', '1.3764', '0.5774', '(0.2176-0.868*j)']
        arccot_angles = arccsc_angles
        self.assert_function_values('arccot', arccot_inputs, arccot_angles)

    def test_hyperbolic_functions(self):
        """
        Test the hyperbolic functions

        which are: sinh, cosh, tanh, sech, csch, coth
        """
        inputs = ['0', '0.5', '1', '2', '1+j']
        neg_inputs = ['0', '-0.5', '-1', '-2', '-1-j']
        negate = lambda x: [-k for k in x]

        # sinh is odd
        sinh_vals = [0, 0.521, 1.175, 3.627, 0.635 + 1.298j]
        self.assert_function_values('sinh', inputs, sinh_vals)
        self.assert_function_values('sinh', neg_inputs, negate(sinh_vals))

        # cosh is even - do not negate
        cosh_vals = [1, 1.128, 1.543, 3.762, 0.834 + 0.989j]
        self.assert_function_values('cosh', inputs, cosh_vals)
        self.assert_function_values('cosh', neg_inputs, cosh_vals)

        # tanh is odd
        tanh_vals = [0, 0.462, 0.762, 0.964, 1.084 + 0.272j]
        self.assert_function_values('tanh', inputs, tanh_vals)
        self.assert_function_values('tanh', neg_inputs, negate(tanh_vals))

        # sech is even - do not negate
        sech_vals = [1, 0.887, 0.648, 0.266, 0.498 - 0.591j]
        self.assert_function_values('sech', inputs, sech_vals)
        self.assert_function_values('sech', neg_inputs, sech_vals)

        # the following functions do not have 0 in their domain
        inputs = inputs[1:]
        neg_inputs = neg_inputs[1:]

        # csch is odd
        csch_vals = [1.919, 0.851, 0.276, 0.304 - 0.622j]
        self.assert_function_values('csch', inputs, csch_vals)
        self.assert_function_values('csch', neg_inputs, negate(csch_vals))

        # coth is odd
        coth_vals = [2.164, 1.313, 1.037, 0.868 - 0.218j]
        self.assert_function_values('coth', inputs, coth_vals)
        self.assert_function_values('coth', neg_inputs, negate(coth_vals))

    def test_hyperbolic_inverses(self):
        """
        Test the inverse hyperbolic functions

        which are of the form arc[X]h
        """
        results = [0, 0.5, 1, 2, 1 + 1j]

        sinh_vals = ['0', '0.5211', '1.1752', '3.6269', '0.635+1.2985*j']
        self.assert_function_values('arcsinh', sinh_vals, results)

        cosh_vals = ['1', '1.1276', '1.5431', '3.7622', '0.8337+0.9889*j']
        self.assert_function_values('arccosh', cosh_vals, results)

        tanh_vals = ['0', '0.4621', '0.7616', '0.964', '1.0839+0.2718*j']
        self.assert_function_values('arctanh', tanh_vals, results)

        sech_vals = ['1.0', '0.8868', '0.6481', '0.2658', '0.4983-0.5911*j']
        self.assert_function_values('arcsech', sech_vals, results)

        results = results[1:]
        csch_vals = ['1.919', '0.8509', '0.2757', '0.3039-0.6215*j']
        self.assert_function_values('arccsch', csch_vals, results)

        coth_vals = ['2.164', '1.313', '1.0373', '0.868-0.2176*j']
        self.assert_function_values('arccoth', coth_vals, results)

    def test_other_functions(self):
        """
        Test the non-trig functions provided in calc.py

        Specifically:
          sqrt, log10, log2, ln, abs,
          fact, factorial
        """

        # Test sqrt
        self.assert_function_values(
            'sqrt',
            [0, 1, 2, 1024],  # -1
            [0, 1, 1.414, 32]  # 1j
        )
        # sqrt(-1) is NAN not j (!!).

        # Test logs
        self.assert_function_values(
            'log10',
            [0.1, 1, 3.162, 1000000, '1+j'],
            [-1, 0, 0.5, 6, 0.151 + 0.341j]
        )
        self.assert_function_values(
            'log2',
            [0.5, 1, 1.414, 1024, '1+j'],
            [-1, 0, 0.5, 10, 0.5 + 1.133j]
        )
        self.assert_function_values(
            'ln',
            [0.368, 1, 1.649, 2.718, 42, '1+j'],
            [-1, 0, 0.5, 1, 3.738, 0.347 + 0.785j]
        )

        # Test abs
        self.assert_function_values('abs', [-1, 0, 1, 'j'], [1, 0, 1, 1])

        # Test factorial
        fact_inputs = [0, 1, 3, 7]
        fact_values = [1, 1, 6, 5040]
        self.assert_function_values('fact', fact_inputs, fact_values)
        self.assert_function_values('factorial', fact_inputs, fact_values)

        self.assertRaises(ValueError, calc.evaluator, {}, {}, "fact(-1)")
        self.assertRaises(ValueError, calc.evaluator, {}, {}, "fact(0.5)")
        self.assertRaises(ValueError, calc.evaluator, {}, {}, "factorial(-1)")
        self.assertRaises(ValueError, calc.evaluator, {}, {}, "factorial(0.5)")

    def test_constants(self):
        """
        Test the default constants provided in calc.py

        which are: j (complex number), e, pi, k, c, T, q
        """

        # Of the form ('expr', python value, tolerance (or None for exact))
        default_variables = [
            ('i', 1j, None),
            ('j', 1j, None),
            ('e', 2.7183, 1e-4),
            ('pi', 3.1416, 1e-4),
            ('k', 1.3806488e-23, 1e-26),  # Boltzmann constant (Joules/Kelvin)
            ('c', 2.998e8, 1e5),  # Light Speed in (m/s)
            ('T', 298.15, 0.01),  # Typical room temperature (Kelvin)
            ('q', 1.602176565e-19, 1e-22)  # Fund. Charge (Coulombs)
        ]
        for (variable, value, tolerance) in default_variables:
            fail_msg = "Failed on constant '{0}', not within bounds".format(
                variable
            )
            result = calc.evaluator({}, {}, variable)
            if tolerance is None:
                self.assertEqual(value, result, msg=fail_msg)
            else:
                self.assertAlmostEqual(
                    value, result,
                    delta=tolerance, msg=fail_msg
                )

    def test_complex_expression(self):
        """
        Calculate combinations of operators and default functions
        """

        self.assertAlmostEqual(
            calc.evaluator({}, {}, "(2^2+1.0)/sqrt(5e0)*5-1"),
            10.180,
            delta=1e-3
        )
        self.assertAlmostEqual(
            calc.evaluator({}, {}, "1+1/(1+1/(1+1/(1+1)))"),
            1.6,
            delta=1e-3
        )
        self.assertAlmostEqual(
            calc.evaluator({}, {}, "10||sin(7+5)"),
            -0.567, delta=0.01
        )
        self.assertAlmostEqual(
            calc.evaluator({}, {}, "sin(e)"),
            0.41, delta=0.01
        )
        self.assertAlmostEqual(
            calc.evaluator({}, {}, "k*T/q"),
            0.025, delta=1e-3
        )
        self.assertAlmostEqual(
            calc.evaluator({}, {}, "e^(j*pi)"),
            -1, delta=1e-5
        )

    def test_explicit_sci_notation(self):
        """
        Expressions like 1.6*10^-3 (not 1.6e-3) it should evaluate.
        """
        self.assertEqual(
            calc.evaluator({}, {}, "-1.6*10^-3"),
            -0.0016
        )
        self.assertEqual(
            calc.evaluator({}, {}, "-1.6*10^(-3)"),
            -0.0016
        )

        self.assertEqual(
            calc.evaluator({}, {}, "-1.6*10^3"),
            -1600
        )
        self.assertEqual(
            calc.evaluator({}, {}, "-1.6*10^(3)"),
            -1600
        )

    def test_simple_vars(self):
        """
        Substitution of variables into simple equations
        """
        variables = {'x': 9.72, 'y': 7.91, 'loooooong': 6.4}

        # Should not change value of constant
        # even with different numbers of variables...
        self.assertEqual(calc.evaluator({'x': 9.72}, {}, '13'), 13)
        self.assertEqual(calc.evaluator({'x': 9.72, 'y': 7.91}, {}, '13'), 13)
        self.assertEqual(calc.evaluator(variables, {}, '13'), 13)

        # Easy evaluation
        self.assertEqual(calc.evaluator(variables, {}, 'x'), 9.72)
        self.assertEqual(calc.evaluator(variables, {}, 'y'), 7.91)
        self.assertEqual(calc.evaluator(variables, {}, 'loooooong'), 6.4)

        # Test a simple equation
        self.assertAlmostEqual(
            calc.evaluator(variables, {}, '3*x-y'),
            21.25, delta=0.01  # = 3 * 9.72 - 7.91
        )
        self.assertAlmostEqual(
            calc.evaluator(variables, {}, 'x*y'),
            76.89, delta=0.01
        )

        self.assertEqual(calc.evaluator({'x': 9.72, 'y': 7.91}, {}, "13"), 13)
        self.assertEqual(calc.evaluator(variables, {}, "13"), 13)
        self.assertEqual(
            calc.evaluator(
                {'a': 2.2997471478310274, 'k': 9, 'm': 8, 'x': 0.6600949841121},
                {}, "5"
            ),
            5
        )

    def test_variable_case_sensitivity(self):
        """
        Test the case sensitivity flag and corresponding behavior
        """
        self.assertEqual(
            calc.evaluator({'R1': 2.0, 'R3': 4.0}, {}, "r1*r3"),
            8.0
        )

        variables = {'t': 1.0}
        self.assertEqual(calc.evaluator(variables, {}, "t"), 1.0)
        self.assertEqual(calc.evaluator(variables, {}, "T"), 1.0)
        self.assertEqual(
            calc.evaluator(variables, {}, "t", case_sensitive=True),
            1.0
        )
        # Recall 'T' is a default constant, with value 298.15
        self.assertAlmostEqual(
            calc.evaluator(variables, {}, "T", case_sensitive=True),
            298, delta=0.2
        )

    def test_simple_funcs(self):
        """
        Subsitution of custom functions
        """
        variables = {'x': 4.712}
        functions = {'id': lambda x: x}
        self.assertEqual(calc.evaluator({}, functions, 'id(2.81)'), 2.81)
        self.assertEqual(calc.evaluator({}, functions, 'id(2.81)'), 2.81)
        self.assertEqual(calc.evaluator(variables, functions, 'id(x)'), 4.712)

        functions.update({'f': numpy.sin})
        self.assertAlmostEqual(
            calc.evaluator(variables, functions, 'f(x)'),
            -1, delta=1e-3
        )

    def test_function_case_insensitive(self):
        """
        Test case insensitive evaluation

        Normal functions with some capitals should be fine
        """
        self.assertAlmostEqual(
            -0.28,
            calc.evaluator({}, {}, 'SiN(6)', case_sensitive=False),
            delta=1e-3
        )

    def test_function_case_sensitive(self):
        """
        Test case sensitive evaluation

        Incorrectly capitilized should fail
        Also, it should pick the correct version of a function.
        """
        with self.assertRaisesRegexp(calc.UndefinedVariable, 'SiN'):
            calc.evaluator({}, {}, 'SiN(6)', case_sensitive=True)

        # With case sensitive turned on, it should pick the right function
        functions = {'f': lambda x: x, 'F': lambda x: x + 1}
        self.assertEqual(
            6, calc.evaluator({}, functions, 'f(6)', case_sensitive=True)
        )
        self.assertEqual(
            7, calc.evaluator({}, functions, 'F(6)', case_sensitive=True)
        )

    def test_undefined_vars(self):
        """
        Check to see if the evaluator catches undefined variables
        """
        variables = {'R1': 2.0, 'R3': 4.0}

        with self.assertRaisesRegexp(calc.UndefinedVariable, 'QWSEKO'):
            calc.evaluator({}, {}, "5+7*QWSEKO")
        with self.assertRaisesRegexp(calc.UndefinedVariable, 'r2'):
            calc.evaluator({'r1': 5}, {}, "r1+r2")
        with self.assertRaisesRegexp(calc.UndefinedVariable, 'r1 r3'):
            calc.evaluator(variables, {}, "r1*r3", case_sensitive=True)

    def assert_function_values(self, fname, ins, outs, tolerance=1e-3):
        """
        Helper function to test many values at once

        Test the accuracy of evaluator's use of the function given by fname
        Specifically, the equality of `fname(ins[i])` against outs[i].
        This is used later to test a whole bunch of f(x) = y at a time
        """

        for (arg, val) in zip(ins, outs):
            input_str = "{0}({1})".format(fname, arg)
            result = calc.evaluator({}, {}, input_str)
            fail_msg = "Failed on function {0}: '{1}' was not {2}".format(
                fname, input_str, val
            )
            self.assertAlmostEqual(val, result, delta=tolerance, msg=fail_msg)
