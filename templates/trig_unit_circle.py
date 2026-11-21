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


def f(theta):
    return np.sin(theta)


def cosine_at(theta):
    return np.cos(theta)


class GeneratedScene(Scene):
    def construct(self):
        theta0 = 0
        initial_sine = f(theta0)
        initial_cosine = cosine_at(theta0)
        period_value = 2 * PI
        display_radius = 0.8
        guide_theta = PI / 2
        guide_y = f(guide_theta)
        title = Text('Sine and cosine are moving coordinates', font_size=30).to_edge(UP, buff=0.35)
        axes = Axes(x_range=[0, 7, 1], y_range=[-1.5, 4.5, 1.5], x_length=6.2, y_length=4.5,
                    tips=False, axis_config={'include_numbers': False})
        axis_labels = axes.get_axis_labels(x_label=Text('θ', font_size=22), y_label=Text('value', font_size=22))
        axis_numbers = add_plain_axis_numbers(axes, [1, 2, 3, 4, 5, 6], [-1, 1])
        circle = Circle(radius=display_radius, color=BLUE_C).move_to(axes.c2p(3.5, 3))
        identities = Text('Unit circle:\nx = cos(θ)\ny = sin(θ)', font_size=22)
        legend = VGroup(Text('cos(θ): x', font_size=22, color=ORANGE),
                        Text('sin(θ): y', font_size=22, color=TEAL_C)).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        readout = Text(f'θ = {theta0:.2f} rad\ncos(θ) = {initial_cosine:.2f}\nsin(θ) = {initial_sine:.2f}', font_size=22)
        period = Text(f'Period ≈ {period_value:.4g} rad', font_size=22, color=YELLOW)
        info_panel = VGroup(identities, legend, readout, period)
        info_panel.arrange(DOWN, aligned_edge=LEFT, buff=0.35)
        panel_border = SurroundingRectangle(info_panel, color=BLUE_D, buff=0.25, corner_radius=0.15)
        info_box = VGroup(panel_border, info_panel).next_to(axes, RIGHT, buff=0.65)
        axes_group = VGroup(axes, axis_labels, axis_numbers, circle)
        canvas = VGroup(axes_group, info_box).move_to(ORIGIN).shift(DOWN * 0.25)
        center = circle.get_center()
        initial_endpoint = center + np.array([display_radius * initial_cosine, display_radius * initial_sine, 0])
        radius = Line(center, initial_endpoint, color=YELLOW)
        point = Dot(initial_endpoint, color=YELLOW)
        sine = VMobject(color=TEAL_C)
        cosine = VMobject(color=ORANGE)
        sine_points = [axes.c2p(theta0, initial_sine)]
        cosine_points = [axes.c2p(theta0, initial_cosine)]
        guides = VGroup(DashedLine(axes.c2p(guide_theta, guide_y), axes.c2p(guide_theta, 0), color=GRAY_B, stroke_width=1, stroke_opacity=0.5),
                        DashedLine(axes.c2p(guide_theta, guide_y), axes.c2p(0, guide_y), color=GRAY_B, stroke_width=1, stroke_opacity=0.5))
        self.play(Write(title), Create(circle), Create(axes), Write(axis_labels), FadeIn(axis_numbers), FadeIn(info_panel), Create(panel_border), Create(guides), run_time=1.5)
        self.play(Create(radius), FadeIn(point), run_time=1)
        for theta in np.linspace(0.02, period_value, 32):
            sine_value = f(theta)
            cosine_value = cosine_at(theta)
            endpoint = center + np.array([display_radius * cosine_value, display_radius * sine_value, 0])
            sine_points.append(axes.c2p(theta, sine_value))
            cosine_points.append(axes.c2p(theta, cosine_value))
            new_sine = VMobject(color=TEAL_C).set_points_as_corners(sine_points)
            new_cosine = VMobject(color=ORANGE).set_points_as_corners(cosine_points)
            new_readout = Text(f'θ = {theta:.2f} rad\ncos(θ) = {cosine_value:.2f}\nsin(θ) = {sine_value:.2f}', font_size=22).move_to(readout, aligned_edge=LEFT)
            self.play(point.animate.move_to(endpoint),
                      Transform(radius, Line(center, endpoint, color=YELLOW)),
                      Transform(sine, new_sine), Transform(cosine, new_cosine), Transform(readout, new_readout), run_time=0.25)
        self.wait(1.5)
