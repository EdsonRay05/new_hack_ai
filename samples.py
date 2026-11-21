"""Explicitly labeled deterministic lessons; no AI calls or hidden fallback."""
import math

SAMPLES = {
    'derivative_tangent': {
        'title': 'When a secant becomes a tangent',
        'problem': 'For f(x) = x^2, explain why the derivative at x = 2 is 4.',
        'learning_question': 'How can two points reveal the slope at one point?',
        'steps': [
            'Fix one point at (2, 4). Place a second point at (2 + dx, (2 + dx)^2).',
            'The slope between them is ((2 + dx)^2 - 4) / dx = 4 + dx, for dx nonzero.',
            'As dx approaches zero, the secant approaches a tangent and its slope approaches 4.'
        ],
        'assumptions': ['The curve is f(x) = x^2; the fixed point is x = 2.'],
        'checks': ['Difference quotient at dx = 0.05: 4.05.', 'Analytic derivative: 2x; at x = 2, the slope is 4.'],
    },
    'integral_riemann': {
        'title': 'Small rectangles, one exact area',
        'problem': 'Explain the definite integral of f(x) = x^2 from x = 0 to x = 2 using left Riemann sums.',
        'learning_question': 'Why does adding rectangles approach the area under a curve?',
        'steps': [
            'Each rectangle approximates a thin strip of area: height multiplied by width.',
            'For this increasing curve, left endpoint rectangles underestimate the area. Narrower strips reduce the missing gaps.',
            'In the limit the sum equals the integral, [x^3 / 3] from 0 to 2 = 8/3, about 2.667 square units.'
        ],
        'assumptions': ['Use left endpoints and the interval [0, 2].'],
        'checks': ['Exact area: 8/3 square units.', 'Four left rectangles of width 0.5 sum to 1.75 square units.'],
    },
    'projectile_motion': {
        'title': 'Gravity changes only the vertical motion',
        'problem': 'A projectile starts at ground level with vx = 8 m/s and vy = 6 m/s. Explain its trajectory with g = 9.8 m/s^2.',
        'learning_question': 'Why does the path bend while horizontal speed stays constant?',
        'steps': [
            'Horizontal position is x = 8t. Without air resistance, horizontal velocity remains 8 m/s.',
            'Vertical position is y = 6t - 4.9t^2. Vertical velocity is 6 - 9.8t, reaching zero at the top.',
            'The projectile returns to ground after about 1.224 seconds, traveling about 9.796 meters horizontally.'
        ],
        'assumptions': ['No air resistance.', 'Constant g = 9.8 m/s^2.', 'Launch and landing are at the same height.'],
        'checks': ['Time of flight: 2(6)/9.8 = 1.22449 s.', 'Range: 8(12/9.8) = 9.79592 m.'],
    },
    'vector_addition': {
        'title': 'Two moves become one resultant',
        'problem': 'Add vectors A = (3, 1) and B = (1, 2). Find the resultant magnitude and angle.',
        'learning_question': 'Why can we slide a vector to add it tip to tail?',
        'steps': [
            'A vector specifies a displacement, so sliding its tail preserves its length and direction.',
            'Place B at the tip of A. The resultant runs from the first tail to the final tip: (3 + 1, 1 + 2) = (4, 3).',
            'Its magnitude is sqrt(4^2 + 3^2) = 5. Its angle from positive x is atan2(3, 4), about 36.9 degrees.'
        ],
        'assumptions': ['Both vectors use the same Cartesian basis and units.'],
        'checks': ['Magnitude: 5.', 'Angle: 36.8699 degrees.'],
    },
    'trig_unit_circle': {
        'title': 'A circle unfolds into waves',
        'problem': 'Explain how rotating around the unit circle traces sin(theta) and cos(theta) from 0 to 2pi.',
        'learning_question': 'Where do the shapes of sine and cosine come from?',
        'steps': [
            'On a unit circle, a point at angle theta has coordinates (cos(theta), sin(theta)).',
            'As the radius rotates counterclockwise, plot the vertical coordinate in teal and horizontal coordinate in orange against theta.',
            'After 2pi radians the point returns to its start. Both waves repeat, with cosine starting at 1 and sine at 0.'
        ],
        'assumptions': ['Angles are measured in radians counterclockwise from positive x.', 'Circle coordinates are unit values; the displayed circle is scaled to fit.'],
        'checks': ['At theta = pi/2: cos(theta) = 0 and sin(theta) = 1.', 'Both periods are 2pi radians.'],
    },
}

WALKTHROUGHS = {
    'derivative_tangent': {
        'problem_title': 'Derivative of f(x) = x² at x = 2',
        'visual_intuition': 'Watch the teal point move toward the yellow point. The secant line pivots around the fixed point until it approaches the tangent, revealing the instantaneous slope.',
        'final_answer': 'Slope m = 4 | Tangent line: y = 4x - 4',
        'solution_steps': [
            ('Find the point of tangency',
             'Function evaluation: y₀ = f(x₀)',
             'We need a point on the tangent as well as its slope. Substituting the given x-value tells us exactly where the tangent meets the curve.',
             'Given f(x) = x² and x₀ = 2\ny₀ = f(2)\ny₀ = 2²\ny₀ = 2 · 2 = 4\nTherefore, the point is (2, 4).'),
            ('Find the instantaneous slope formula',
             'Power Rule: d/dx [a·xⁿ] = a·n·xⁿ⁻¹',
             'The derivative gives the slope at any point on this polynomial. The power rule applies directly because x² is a power of x.',
             "Start with f(x) = x²\nf'(x) = 1 · 2 · x²⁻¹\n2 - 1 = 1\nf'(x) = 2x¹\nTherefore, f'(x) = 2x."),
            ('Evaluate the derivative at x = 2',
             "Instantaneous slope: m = f'(x₀)",
             'The derivative is a function of x, so we still need to substitute our particular x-value. This gives the slope of this tangent rather than a general slope formula.',
             "We found f'(x) = 2x\nSubstitute x₀ = 2:\nm = f'(2)\nm = 2 · 2\nTherefore, m = 4."),
            ('Write and simplify the tangent equation',
             'Point-Slope Form: y - y₀ = m(x - x₀)',
             'We now know both a point and a slope, which is exactly what point-slope form needs. Expanding and isolating y makes the final line easy to read.',
             'y - y₀ = m(x - x₀)\ny - 4 = 4(x - 2)\ny - 4 = 4x - 8\nAdd 4 to both sides:\ny = 4x - 8 + 4\nTherefore, y = 4x - 4.'),
        ],
    },
    'integral_riemann': {
        'problem_title': 'Area under f(x) = x² from 0 to 2',
        'visual_intuition': 'Watch the rectangles get narrower and fill more of the space under the curve. Left-endpoint rectangles sit below this increasing curve, so their totals approach the area from below.',
        'final_answer': 'Area = 8/3 ≈ 2.667 square units',
        'solution_steps': [
            ('Find the width of each strip',
             'Equal strip width: Δx = (b - a)/n',
             'A curved region is easier to estimate as a sum of rectangles. Equal widths let us calculate each small area in the same way.',
             'Given a = 0, b = 2, n = 4\nΔx = (2 - 0)/4\nΔx = 2/4 = 0.5\nLeft endpoints: 0, 0.5, 1, 1.5'),
            ('Add the left-endpoint rectangle areas',
             'Left Riemann sum: Lₙ = Σ f(xᵢ)·Δx',
             'Each rectangle uses the curve height at its left endpoint. Since x² increases on this interval, these rectangle areas underestimate the curved region.',
             'L₄ = 0.5 · [f(0) + f(0.5) + f(1) + f(1.5)]\nL₄ = 0.5 · [0² + 0.5² + 1² + 1.5²]\nL₄ = 0.5 · [0 + 0.25 + 1 + 2.25]\nL₄ = 0.5 · 3.5\nL₄ = 1.75 square units'),
            ('Calculate the exact limiting area',
             'Fundamental Theorem: ∫ₐᵇ f(x) dx = F(b) - F(a)',
             'As the strips become arbitrarily narrow, the sum becomes a definite integral. An antiderivative lets us evaluate that exact area using just the two bounds.',
             'An antiderivative of x² is F(x) = x³/3\nF(2) = 2³/3 = 8/3\nF(0) = 0³/3 = 0\n∫₀² x² dx = F(2) - F(0)\nArea = 8/3 - 0 = 8/3\nArea ≈ 2.667 square units'),
        ],
    },
    'projectile_motion': {
        'problem_title': 'Projectile motion with vₓ = 8 m/s and vᵧ = 6 m/s',
        'visual_intuition': 'Follow the horizontal and vertical arrows attached to the projectile. The teal arrow keeps its length while the orange arrow shrinks, reverses, and grows as gravity changes the vertical velocity.',
        'final_answer': 'Flight time ≈ 1.224 s | Horizontal range ≈ 9.796 m',
        'solution_steps': [
            ('Write the position equations',
             'Constant acceleration: s = s₀ + v₀t + ½at²',
             'Without air resistance, horizontal acceleration is zero and vertical acceleration is -g. Applying the same rule separately in each direction keeps those effects clear.',
             'Horizontal: x₀ = 0, vₓ = 8 m/s, aₓ = 0\nx(t) = 0 + 8t + ½(0)t² = 8t\nVertical: y₀ = 0, vᵧ(0) = 6 m/s, aᵧ = -9.8 m/s²\ny(t) = 0 + 6t + ½(-9.8)t²\ny(t) = 6t - 4.9t²'),
            ('Solve for the landing time',
             'Ground-level landing condition: y(t) = 0',
             'The projectile lands when it returns to its starting height. There are two solutions: launch at t = 0 and the later time we want.',
             '0 = 6t - 4.9t²\nFactor out t:\n0 = t(6 - 4.9t)\nEither t = 0 or 6 - 4.9t = 0\nFor the landing: 4.9t = 6\nt = 6/4.9 = 12/9.8 s\nt ≈ 1.224 s'),
            ('Use the flight time to find the range',
             'Horizontal range: R = vₓ · t',
             'Both directions share the same flight time. Because horizontal speed is constant, multiplying it by the exact time gives the horizontal distance.',
             'R = 8 · (12/9.8)\nR = 96/9.8 m\nR ≈ 9.795918 m\nTherefore, R ≈ 9.796 m.'),
        ],
    },
    'vector_addition': {
        'problem_title': 'Add A = (3, 1) and B = (1, 2)',
        'visual_intuition': 'Watch B slide to the tip of A without rotating or stretching. The yellow resultant connects the starting point to the final endpoint, combining both displacements into one.',
        'final_answer': 'A + B = (4, 3) | Magnitude = 5 | θ ≈ 36.9°',
        'solution_steps': [
            ('Add the horizontal and vertical components',
             'Vector sum: R = (Aₓ + Bₓ, Aᵧ + Bᵧ)',
             'Components along the same axis describe compatible displacements, so we can add them directly. Keeping the two axes separate prevents mixing horizontal and vertical moves.',
             'A = (3, 1), B = (1, 2)\nRₓ = Aₓ + Bₓ = 3 + 1 = 4\nRᵧ = Aᵧ + Bᵧ = 1 + 2 = 3\nTherefore, R = (4, 3).'),
            ('Find the resultant magnitude',
             'Pythagorean magnitude: |R| = √(Rₓ² + Rᵧ²)',
             'The horizontal and vertical components form the perpendicular sides of a right triangle. The resultant is its hypotenuse, so the Pythagorean theorem gives its length.',
             '|R| = √(4² + 3²)\n4² = 16 and 3² = 9\n|R| = √(16 + 9)\n|R| = √25\nTherefore, |R| = 5.'),
            ('Calculate the direction',
             'Direction from positive x: θ = atan2(Rᵧ, Rₓ)',
             'We need an angle as well as a length to describe the resultant. Both components are positive, so the direction lies in the first quadrant.',
             'θ = atan2(3, 4)\nSince Rₓ > 0 and Rᵧ > 0, use the first quadrant.\n3/4 = 0.75\nθ = arctan(0.75)\nθ ≈ 36.8699°\nTherefore, θ ≈ 36.9°.'),
        ],
    },
    'trig_unit_circle': {
        'problem_title': 'See sin(θ) and cos(θ) on the unit circle',
        'visual_intuition': 'Watch the yellow radius rotate while the two coordinate traces grow. The orange wave records horizontal position and the teal wave records vertical position, turning circular motion into two repeating waves.',
        'final_answer': 'x = cos(θ), y = sin(θ) | Both repeat every 2π radians',
        'solution_steps': [
            ('Evaluate the starting coordinates',
             'Unit-circle coordinates: (x, y) = (cos(θ), sin(θ))',
             'Cosine and sine are defined by the horizontal and vertical coordinates on the unit circle. Starting at zero angle gives us a simple reference point for both functions.',
             'At θ = 0, the radius lies on positive x.\nx = cos(0) = 1\ny = sin(0) = 0\nTherefore, the starting point is (1, 0).'),
            ('Evaluate a quarter turn',
             'Quarter turn: θ = 2π/4 = π/2',
             'A quarter turn takes the point to the top of the unit circle. Reading its coordinates tells us the corresponding exact sine and cosine values.',
             'θ = 2π/4\nθ = π/2 radians = 90°\nThe unit-circle top point has x = 0 and y = 1.\nTherefore, cos(π/2) = 0\nAnd sin(π/2) = 1.'),
            ('Identify the repeating period',
             'Full-turn identities: sin(θ + 2π) = sin(θ); cos(θ + 2π) = cos(θ)',
             'Adding a full revolution returns the radius to the same point. Because its coordinates repeat, the sine and cosine values repeat too.',
             'One full turn is Δθ = 2π radians = 360°.\nAt θ = 2π: x = cos(2π) = 1 and y = sin(2π) = 0.\nThese are the same coordinates as at θ = 0.\nMore generally, adding 2π leaves both coordinates unchanged.\nTherefore, both functions have period 2π.'),
        ],
    },
}

for sample_id, walkthrough in WALKTHROUGHS.items():
    sample = SAMPLES[sample_id]
    sample.update({key: value for key, value in walkthrough.items() if key != 'solution_steps'})
    sample['solution_steps'] = [dict(step_number=i, action_title=title, formula_used=formula,
                                   why_this_formula=why, detailed_walkthrough=work)
                               for i, (title, formula, why, work) in enumerate(walkthrough['solution_steps'], 1)]
    sample['problem'] = sample['problem'].replace('^2', '²').replace('theta', 'θ').replace('2pi', '2π')
    for key in ['assumptions', 'checks', 'steps']:
        sample[key] = [text.replace('^2', '²').replace('^3', '³').replace('theta', 'θ').replace('2pi', '2π')
                       for text in sample[key]]


def verify_sample_math():
    """Independent scalar checks of the claims in the known sample lessons."""
    dx = 0.05
    assert math.isclose(((2 + dx)**2 - 4) / dx, 4.05)
    assert math.isclose(sum((i * 0.5)**2 * 0.5 for i in range(4)), 1.75)
    assert math.isclose(2**3 / 3, 8/3)
    flight = 12 / 9.8
    assert math.isclose(6 * flight - 4.9 * flight**2, 0, abs_tol=1e-12)
    assert math.isclose(math.hypot(4, 3), 5)
    assert math.isclose(math.degrees(math.atan2(3, 4)), 36.86989764584402)
    assert math.isclose(math.sin(math.pi / 2), 1)
