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


def horizontal_position(t, initial_vx):
    return initial_vx * t


def height(t, initial_vy, gravity):
    return initial_vy * t - 0.5 * gravity * t**2


def vertical_velocity(t, initial_vy, gravity):
    return initial_vy - gravity * t


class GeneratedScene(Scene):
    def construct(self):
        initial_vx = 8
        initial_vy = 6
        gravity = 9.8
        t0 = 0
        flight_time = 2 * initial_vy / gravity
        horizontal_range = horizontal_position(flight_time, initial_vx)
        half_gravity = gravity / 2
        initial_vertical = vertical_velocity(t0, initial_vy, gravity)
        velocity_scale = 0.2
        title = Text('Projectile motion without air resistance', font_size=30).to_edge(UP, buff=0.35)
        axes = Axes(x_range=[0, 12, 2], y_range=[-1.5, 3, 1], x_length=6.2, y_length=4.5,
                    tips=False, axis_config={'include_numbers': False})
        axis_labels = axes.get_axis_labels(x_label=Text('x (m)', font_size=22), y_label=Text('y (m)', font_size=22))
        axis_numbers = add_plain_axis_numbers(axes, [2, 4, 6, 8, 10, 12], [-1, 1, 2, 3])
        launch = Text(f'vₓ = {initial_vx:.4g} m/s\nvᵧ({t0:g}) = {initial_vy:.4g} m/s\ng = {gravity:.4g} m/s²', font_size=22)
        formulas = Text(f'x = {initial_vx:.4g}t\ny = {initial_vy:.4g}t - {half_gravity:.4g}t²', font_size=22, color=BLUE_C)
        readout = Text(f't = {t0:.2f} s\nvᵧ = {initial_vertical:.2f} m/s', font_size=22)
        answer = Text(f'Flight ≈ {flight_time:.4g} s\nRange ≈ {horizontal_range:.4g} m', font_size=22, color=YELLOW)
        info_panel = VGroup(launch, formulas, readout, answer)
        info_panel.arrange(DOWN, aligned_edge=LEFT, buff=0.35)
        panel_border = SurroundingRectangle(info_panel, color=BLUE_D, buff=0.25, corner_radius=0.15)
        info_box = VGroup(panel_border, info_panel).next_to(axes, RIGHT, buff=0.65)
        axes_group = VGroup(axes, axis_labels, axis_numbers)
        canvas = VGroup(axes_group, info_box).move_to(ORIGIN).shift(DOWN * 0.25)
        path = VMobject(color=BLUE_C)
        points = [axes.c2p(horizontal_position(t, initial_vx), height(t, initial_vy, gravity)) for t in np.linspace(t0, flight_time, 60)]
        path.set_points_smoothly(points)
        ball = Dot(points[0], color=YELLOW)
        apex_time = initial_vy / gravity
        apex_x = horizontal_position(apex_time, initial_vx)
        apex_y = height(apex_time, initial_vy, gravity)
        guides = VGroup(DashedLine(axes.c2p(apex_x, apex_y), axes.c2p(apex_x, 0), color=GRAY_B, stroke_width=1, stroke_opacity=0.5),
                        DashedLine(axes.c2p(apex_x, apex_y), axes.c2p(0, apex_y), color=GRAY_B, stroke_width=1, stroke_opacity=0.5))
        vx = Arrow(axes.c2p(0, 0), axes.c2p(initial_vx * velocity_scale, 0), buff=0, color=TEAL_C)
        vy = Arrow(axes.c2p(0, 0), axes.c2p(0, initial_vertical * velocity_scale), buff=0, color=ORANGE)
        self.play(Write(title), Create(axes), Write(axis_labels), FadeIn(axis_numbers), run_time=1)
        self.play(Create(path), FadeIn(info_panel), Create(panel_border), FadeIn(ball), GrowArrow(vx), GrowArrow(vy), Create(guides), run_time=2)
        for t in [0.2, 0.4, 0.6, 0.8, 1.0, flight_time]:
            x = horizontal_position(t, initial_vx)
            y = height(t, initial_vy, gravity)
            vertical = vertical_velocity(t, initial_vy, gravity)
            new_vx = Arrow(axes.c2p(x, y), axes.c2p(x + initial_vx * velocity_scale, y), buff=0, color=TEAL_C)
            new_vy = Arrow(axes.c2p(x, y), axes.c2p(x, y + vertical * velocity_scale), buff=0, color=ORANGE)
            new_readout = Text(f't = {t:.2f} s\nvᵧ = {vertical:.2f} m/s', font_size=22).move_to(readout, aligned_edge=LEFT)
            self.play(ball.animate.move_to(axes.c2p(x, y)), Transform(vx, new_vx), Transform(vy, new_vy), Transform(readout, new_readout), run_time=1)
        self.play(Indicate(answer), run_time=1.5)
        self.wait(1.5)
