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


def magnitude(x, y):
    return np.sqrt(x**2 + y**2)


def direction(x, y):
    return np.arctan2(y, x) * 180 / PI


class GeneratedScene(Scene):
    def construct(self):
        ax = 3
        ay = 1
        bx = 1
        by = 2
        rx = ax + bx
        ry = ay + by
        resultant_magnitude = magnitude(rx, ry)
        angle = direction(rx, ry)
        title = Text('Add vectors by joining tip to tail', font_size=30).to_edge(UP, buff=0.35)
        axes = Axes(x_range=[-1, 6, 1], y_range=[-1, 5, 1], x_length=6.2, y_length=4.5,
                    tips=False, axis_config={'include_numbers': False})
        axis_labels = axes.get_axis_labels(x_label=Text('x', font_size=22), y_label=Text('y', font_size=22))
        axis_numbers = add_plain_axis_numbers(axes, [-1, 1, 2, 3, 4, 5, 6], [-1, 1, 2, 3, 4, 5])
        a_value = Text(f'A = ({ax:g}, {ay:g})', font_size=24, color=BLUE_C)
        b_value = Text(f'B = ({bx:g}, {by:g})', font_size=24, color=TEAL_C)
        result_value = Text('Resultant:\nA + B = ?', font_size=24, color=YELLOW)
        details = Text('Join tip to tail.\nThen add matching\ncomponents.', font_size=24)
        info_panel = VGroup(a_value, b_value, result_value, details)
        info_panel.arrange(DOWN, aligned_edge=LEFT, buff=0.35)
        panel_border = SurroundingRectangle(info_panel, color=BLUE_D, buff=0.25, corner_radius=0.15)
        info_box = VGroup(panel_border, info_panel).next_to(axes, RIGHT, buff=0.65)
        axes_group = VGroup(axes, axis_labels, axis_numbers)
        canvas = VGroup(axes_group, info_box).move_to(ORIGIN).shift(DOWN * 0.25)
        a = Arrow(axes.c2p(0, 0), axes.c2p(ax, ay), buff=0, color=BLUE_C)
        b = Arrow(axes.c2p(0, 0), axes.c2p(bx, by), buff=0, color=TEAL_C)
        moved = Arrow(axes.c2p(ax, ay), axes.c2p(rx, ry), buff=0, color=TEAL_C)
        result = Arrow(axes.c2p(0, 0), axes.c2p(rx, ry), buff=0, color=YELLOW)
        guides = VGroup(DashedLine(axes.c2p(rx, ry), axes.c2p(rx, 0), color=GRAY_B, stroke_width=1, stroke_opacity=0.5),
                        DashedLine(axes.c2p(rx, ry), axes.c2p(0, ry), color=GRAY_B, stroke_width=1, stroke_opacity=0.5))
        self.play(Write(title), Create(axes), Write(axis_labels), FadeIn(axis_numbers), run_time=1)
        self.play(GrowArrow(a), GrowArrow(b), FadeIn(info_panel), Create(panel_border), run_time=2)
        self.play(Transform(b, moved), run_time=2)
        self.play(GrowArrow(result), Create(guides), run_time=2)
        resultant = Text(f'Resultant:\nA + B = ({rx:.4g}, {ry:.4g})', font_size=24, color=YELLOW).move_to(result_value, aligned_edge=LEFT)
        takeaway = Text(f'Magnitude:\n|R| = {resultant_magnitude:.4g}\nAngle: θ ≈ {angle:.3g}°', font_size=24).move_to(details, aligned_edge=LEFT)
        self.play(Transform(result_value, resultant), Transform(details, takeaway), run_time=2)
        self.wait(1.5)
