import sys
import random
from math import pi

from panda3d.core import NodePath
from panda3d.core import CardMaker
from panda3d.core import KeyboardButton

from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectSlider


current_twist = 0.0
max_twist = 30.0
twist_drift = 5.0
speed = 30.0
side_speed = 90.0
current_speed_factor = 0.25
min_speed_factor = 0.25
limit_break_speed = 2.3
accumulated_limit_break = 0.0
needed_limit_break = 5.0


ShowBase()
base.accept('escape', sys.exit)
speed_slider = DirectSlider(value=current_speed_factor, range=(min_speed_factor, limit_break_speed))
speed_slider['thumb_frameSize'] = (-0.02, 0.02, -0.02, 0.02)
speed_slider.set_pos(0, 0, -0.9)

class TunnelSegment:
    def __init__(self, rng, model):
        self.start_node = NodePath('segment-start')
        self.end_node = NodePath('segment-end')
        self.end_node.reparent_to(self.start_node)
        model.reparent_to(self.end_node)

        global current_twist
        current_twist += (rng.random()-0.5)*2.0 * twist_drift
        current_twist = max(-max_twist, current_twist)
        current_twist = min(max_twist, current_twist)

        self.radius = 300.0
        self.pitch = 1.5
        self.twist = current_twist

        self.end_node.set_pos(0, 0, self.radius)
        self.end_node.set_p(self.pitch)
        self.end_node.set_pos(self.end_node, 0, 0, -self.radius)
        self.end_node.set_r(self.twist)
        self.segment_length = 2.0 * pi *self.radius * self.pitch / 360.0

    def detach(self):
        self.start_node.detach_node()

    def attach(self, segment):
        self.start_node.reparent_to(segment.end_node)

    def place_ship(self, ship, ship_y, ship_r):
        ship.set_pos(self.start_node, 0, 0, 0)
        ship.set_hpr(self.start_node, 0, 0, 0)
        ship.set_z(ship, self.radius)
        ship.set_p(ship, self.pitch * ship_y / self.segment_length)
        ship.set_pos(ship, 0, 0, -self.radius)
        ship.set_r(ship_r)


ring_segment_maker = CardMaker('ring-segment-maker')
ring_segment_maker.set_frame(-0.4, 0.4, -1, 1)
def make_ring():
    center = NodePath('center')
    segments = 8
    radius = 1.0
    for idx in range(segments):
        if idx == 0:
            ring_segment_maker.set_color(0, 0, 1, 1)
        else:
            ring_segment_maker.set_color(0.8, 0.8, 0.8, 1)
        card = center.attach_new_node(ring_segment_maker.generate())
        card.set_r(360.0 * float(idx) / float(segments))
        card.set_p(card, -90)
        card.set_y(card, radius)

    center.flatten_strong()
    return center

rng = random.Random(1)
tunnel_segments = []
for idx in range(100):
    m = make_ring()
    tunnel_segments.append(TunnelSegment(rng, m))
    if idx > 0:
        tunnel_segments[-1].attach(tunnel_segments[-2])


ship_root = base.render.attach_new_node('tunnel-centered-node')
ship_root.reparent_to(tunnel_segments[0].start_node)
base.cam.reparent_to(ship_root)
base.cam.set_pos(0, -5, 0)
ship_model = base.loader.load_model('models/smiley')
ship_model.reparent_to(ship_root)
ship_model.set_pos(0, 0, -0.8)
ship_model.set_scale(0.2)

global current_y
current_y = 0.0
global current_r
current_r = 0.0


def change_speed(factor):
    global current_speed_factor
    current_speed_factor *= factor
    print(f"Current speed factor: {current_speed_factor:3.1f}")


def move_ship(task):
    global current_y
    global current_r
    global current_speed_factor

    # Recalculate forward progress and rotation.
    current_y += globalClock.dt * speed * current_speed_factor
    input_r = 0.0
    if base.mouseWatcherNode.is_button_down('arrow_left'):
        input_r -= 1.0
    if base.mouseWatcherNode.is_button_down('arrow_right'):
        input_r += 1.0
    input_r *= globalClock.dt * side_speed# * current_speed_factor
    current_r += input_r
    current_r %= 360.0

    # Put segments that we have passed at the back of the list.
    while current_y > tunnel_segments[0].segment_length:
        current_y -= tunnel_segments[0].segment_length
        current_r -= tunnel_segments[0].twist
        tunnel_segments[1].detach()
        tunnel_segments.append(tunnel_segments.pop(0))
        tunnel_segments[-1].attach(tunnel_segments[-2])
        ship_root.reparent_to(tunnel_segments[0].start_node)

    # Put the models into position.
    tunnel_segments[0].place_ship(ship_root, current_y, current_r)

    # Calculate how closely the current ship rotation matches the ideal line.
    ideal_twist = tunnel_segments[0].twist * (current_y / tunnel_segments[0].segment_length)
    ideal_twist %= 360.0
    difference_to_ideal = abs(ideal_twist - current_r)
    if difference_to_ideal > 180.0:
        difference_to_ideal = 360.0 - difference_to_ideal
    ideality = 1.0 - (difference_to_ideal / 180.0)

    # Adjust the speed factor
    if ideality > (14.5/16.0):
        current_speed_factor += globalClock.dt * 0.05
        speed_slider['thumb_frameColor'] = (0, 1, 0, 1)
        if current_speed_factor > limit_break_speed:
            global accumulated_limit_break
            accumulated_limit_break += globalClock.dt
            if accumulated_limit_break < needed_limit_break:
                speed_slider['frameColor'] = (0, 0, accumulated_limit_break / needed_limit_break, 1)
            else:
                speed_slider['frameColor'] = (1, 1, 1, 1)
            speed_slider['thumb_frameColor'] = (0, 0, 1, 1)
        current_speed_factor = min(limit_break_speed, current_speed_factor)
    elif ideality < 0.5:
        current_speed_factor -= globalClock.dt * 0.25
        current_speed_factor = max(min_speed_factor, current_speed_factor)
        speed_slider['thumb_frameColor'] = (1, 0, 0, 1)
    else:
        speed_slider['thumb_frameColor'] = (0.8, 0.8, 0.8, 1)

    speed_slider['value'] = current_speed_factor

    # We're done!
    return task.cont


base.task_mgr.add(move_ship)
base.run()
