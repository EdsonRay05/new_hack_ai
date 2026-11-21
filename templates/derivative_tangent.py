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


def derivative(x):
    return 2 * x


class GeneratedScene(Scene):
    def construct(self):
        x0 = 2
        y0 = f(x0)
        slope = derivative(x0)
        intercept = y0 - slope * x0
        dx = 1.0
        secant_slope = (f(x0 + dx) - y0) / dx
        title = Text('A derivative is a limiting slope', font_size=30).to_edge(UP, buff=0.35)
        axes = Axes(x_range=[0, 4, 1], y_range=[-4, 12, 4], x_length=6.2, y_length=4.5,
                    tips=False, axis_config={'include_numbers': False})
        axis_labels = axes.get_axis_labels(x_label=Text('x', font_size=22), y_label=Text('y', font_size=22))
        axis_numbers = add_plain_axis_numbers(axes, [1, 2, 3, 4], [-4, 4, 8, 12])
        equation = Text('Function:\nf(x) = x²', font_size=24, color=BLUE_C)
        point_value = Text(f'Point: ({x0:g}, {y0:.4g})', font_size=24)
        label = Text(f'Δx = {dx:.2f}\nSlope = {secant_slope:.4g}', font_size=24)
        answer = Text(f'Tangent as Δx → 0:\ny = {slope:.4g}x {intercept:+.4g}', font_size=24, color=YELLOW)
        info_panel = VGroup(equation, point_value, label, answer)
        info_panel.arrange(DOWN, aligned_edge=LEFT, buff=0.35)
        panel_border = SurroundingRectangle(info_panel, color=BLUE_D, buff=0.25, corner_radius=0.15)
        info_box = VGroup(panel_border, info_panel).next_to(axes, RIGHT, buff=0.65)
        axes_group = VGroup(axes, axis_labels, axis_numbers)
        canvas = VGroup(axes_group, info_box).move_to(ORIGIN).shift(DOWN * 0.25)
        curve = axes.plot(f, x_range=[0, 3.4], color=BLUE_C)
        point = Dot(axes.c2p(x0, y0), color=YELLOW)
        guides = VGroup(DashedLine(axes.c2p(x0, y0), axes.c2p(x0, 0), color=GRAY_B, stroke_width=1, stroke_opacity=0.5),
                        DashedLine(axes.c2p(x0, y0), axes.c2p(0, y0), color=GRAY_B, stroke_width=1, stroke_opacity=0.5))
        second_point = Dot(axes.c2p(x0 + dx, f(x0 + dx)), color=TEAL_C)
        secant = Line(axes.c2p(x0 - 1.5, y0 - secant_slope * 1.5), axes.c2p(x0 + 1.5, y0 + secant_slope * 1.5), color=TEAL_C)
        point_label = Text(f'({x0:g}, {y0:.4g})', font_size=22).next_to(point, DOWN, buff=0.15)
        self.play(Write(title), Create(axes), Write(axis_labels), FadeIn(axis_numbers), run_time=1)
        self.play(Create(curve), FadeIn(info_panel), Create(panel_border), FadeIn(point), Create(guides), run_time=1.5)
        self.play(Create(secant), FadeIn(second_point), Write(point_label), run_time=1)
        for dx in [0.7, 0.4, 0.2, 0.05]:
            secant_slope = (f(x0 + dx) - y0) / dx
            new_line = Line(axes.c2p(x0 - 1.5, y0 - secant_slope * 1.5), axes.c2p(x0 + 1.5, y0 + secant_slope * 1.5), color=TEAL_C)
            new_label = Text(f'Δx = {dx:.2f}\nSlope = {secant_slope:.4g}', font_size=24).move_to(label, aligned_edge=LEFT)
            self.play(Transform(secant, new_line), Transform(label, new_label),
                      second_point.animate.move_to(axes.c2p(x0 + dx, f(x0 + dx))), run_time=1.25)
        tangent = Line(axes.c2p(x0 - 1.5, y0 - slope * 1.5), axes.c2p(x0 + 1.5, y0 + slope * 1.5), color=YELLOW)
        takeaway = Text(f'Δx → 0\nSlope → {slope:.4g}', font_size=24, color=YELLOW).move_to(label, aligned_edge=LEFT)
        self.play(Transform(secant, tangent), Transform(label, takeaway), FadeOut(second_point), run_time=1.5)
        self.wait(1.5)
