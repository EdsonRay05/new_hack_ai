from manim import *


def add_plain_axis_numbers(axes, x_vals, y_vals):
    numbers = VGroup()
    for val in x_vals:
        if val != 0:
            numbers.add(Text(str(val), font_size=16, color=GRAY_B).next_to(axes.c2p(val, 0), DOWN, buff=0.15))
    for val in y_vals:
        if val != 0:
            numbers.add(Text(str(val), font_size=16, color=GRAY_B).next_to(axes.c2p(0, val), LEFT, buff=0.15))
    return numbers


def f(x):
    return x**2


def antiderivative(x):
    return x**3 / 3


class GeneratedScene(Scene):
    def construct(self):
        lower = 0
        upper = 2
        dx = 0.5
        area = antiderivative(upper) - antiderivative(lower)
        x0 = upper
        y0 = f(x0)
        title = Text('An integral adds tiny areas', font_size=30).to_edge(UP, buff=0.35)
        axes = Axes(x_range=[0, 2.5, 0.5], y_range=[0, 5, 1], x_length=6.2, y_length=4.5,
                    tips=False, axis_config={'include_numbers': False})
        axis_labels = axes.get_axis_labels(x_label=Text('x', font_size=22), y_label=Text('y', font_size=22))
        axis_numbers = add_plain_axis_numbers(axes, [0.5, 1, 1.5, 2], [1, 2, 3, 4])
        equation = Text('Function:\nf(x) = x²', font_size=24, color=BLUE_C)
        bounds = Text(f'Bounds: {lower:g} ≤ x ≤ {upper:g}', font_size=24)
        readout = Text(f'Rectangle width:\nΔx = {dx:g}', font_size=24)
        label = Text('Left sums\nunderestimate area', font_size=24)
        info_panel = VGroup(equation, bounds, readout, label)
        info_panel.arrange(DOWN, aligned_edge=LEFT, buff=0.35)
        panel_border = SurroundingRectangle(info_panel, color=BLUE_D, buff=0.25, corner_radius=0.15)
        info_box = VGroup(panel_border, info_panel).next_to(axes, RIGHT, buff=0.65)
        axes_group = VGroup(axes, axis_labels, axis_numbers)
        canvas = VGroup(axes_group, info_box).move_to(ORIGIN).shift(DOWN * 0.25)
        curve = axes.plot(f, x_range=[lower, upper * 1.05], color=BLUE_C)
        point = Dot(axes.c2p(x0, y0), color=BLUE_C)
        guides = VGroup(DashedLine(axes.c2p(x0, y0), axes.c2p(x0, 0), color=GRAY_B, stroke_width=1, stroke_opacity=0.5),
                        DashedLine(axes.c2p(x0, y0), axes.c2p(0, y0), color=GRAY_B, stroke_width=1, stroke_opacity=0.5))
        rectangles = axes.get_riemann_rectangles(curve, x_range=[lower, upper], dx=dx,
                                                input_sample_type='left', fill_opacity=0.6)
        self.play(Write(title), Create(axes), Write(axis_labels), FadeIn(axis_numbers), run_time=1)
        self.play(Create(curve), FadeIn(info_panel), Create(panel_border), FadeIn(point), Create(guides), run_time=1.5)
        self.play(FadeIn(rectangles), run_time=1.5)
        for width in [0.25, 0.125, 0.0625]:
            refined = axes.get_riemann_rectangles(curve, x_range=[lower, upper], dx=width,
                                                  input_sample_type='left', fill_opacity=0.6)
            new_readout = Text(f'Rectangle width:\nΔx = {width:g}', font_size=24).move_to(readout, aligned_edge=LEFT)
            self.play(Transform(rectangles, refined), Transform(readout, new_readout), run_time=1.5)
        takeaway = Text(f'Exact area:\nA ≈ {area:.4g}', font_size=24, color=YELLOW).move_to(label, aligned_edge=LEFT)
        self.play(Transform(label, takeaway), run_time=1.5)
        self.wait(1.5)
