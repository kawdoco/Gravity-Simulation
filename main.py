"""
main.py

Entry point. Builds a scenario (solar system or a random cluster) and
runs the animation. Command-line flags let you turn on Barnes-Hut,
set the collision behavior, or load/save a scenario as JSON.

Examples:
    python main.py
    python main.py --scenario cluster --bodies 300 --barnes-hut
    python main.py --restitution 0.8
    python main.py --load my_scenario.json
"""
import argparse
import math
import random

from vector import Vector3D
from body import Star, Planet, CelestialBody
from simulation import Simulation
from visualizer import Visualizer
from integrator import EulerIntegrator, VerletIntegrator
from constants import G


def build_solar_system():
    sim = Simulation()
    sun = Star("Sun", mass=1.989e30, radius=6.9e8,
               position=Vector3D(0, 0, 0), velocity=Vector3D(0, 0, 0), color="#FFF4D6")
    sim.add_body(sun)

    # name, mass (kg), distance from sun (m), orbital speed (m/s), color
    # Colors approximate each planet's real observed hue rather than
    # generic named crayons (e.g. Venus is a pale cream, not orange).
    planet_data = [
        ("Mercury", 3.285e23, 5.79e10, 47400, "#9C9490"),
        ("Venus",   4.867e24, 1.082e11, 35020, "#E8D6A8"),
        ("Earth",   5.972e24, 1.496e11, 29780, "#4E7CB0"),
        ("Mars",    6.39e23,  2.279e11, 24070, "#B8552E"),
    ]
    for name, mass, distance, speed, color in planet_data:
        position = Vector3D(distance, 0, 0)
        velocity = Vector3D(0, speed, 0)  # perpendicular to position -> roughly circular orbit
        sim.add_body(Planet(name, mass, radius=CelestialBody.radius_from_mass(mass, density=5000),
                             position=position, velocity=velocity, color=color))
    return sim


def build_random_cluster(n=200, seed=None):
    """A compact cluster of many bodies - meant to demo Barnes-Hut and
    collisions, not real astronomy. Units are still SI (kg, m, m/s)."""
    rng = random.Random(seed)
    sim = Simulation()

    center_mass = 8e24
    sim.add_body(Star("Core", center_mass, CelestialBody.radius_from_mass(center_mass, 4000),
                       Vector3D(0, 0, 0), Vector3D(0, 0, 0), "#FFF4D6"))

    # A small palette of realistic rock/ice tones so a crowded cluster
    # reads as many distinct sunlit bodies instead of one indistinct
    # smear - real asteroid/rubble fields aren't uniformly white.
    rock_palette = ["#B7AFA3", "#9C9490", "#A89A82", "#8E8B86", "#C2B49B"]

    for i in range(n):
        r = rng.uniform(2e9, 3e10)
        theta = rng.uniform(0, 2 * math.pi)
        phi = rng.uniform(-0.3, 0.3)  # keep the cluster roughly disk-shaped
        position = Vector3D(r * math.cos(theta), r * math.sin(theta), r * math.sin(phi))

        # rough circular-orbit speed around the central mass, for a mildly stable start
        speed = (G * center_mass / r) ** 0.5 * rng.uniform(0.8, 1.1)
        tangent = Vector3D(-position.y, position.x, 0).normalized()
        velocity = tangent * speed

        mass = rng.uniform(1e20, 5e22)
        sim.add_body(Planet(f"B{i}", mass, CelestialBody.radius_from_mass(mass, density=3000),
                             position, velocity, color=rng.choice(rock_palette)))
    return sim


def main():
    parser = argparse.ArgumentParser(description="OOP gravity simulation")
    parser.add_argument("--scenario", choices=["solar", "cluster"], default="solar")
    parser.add_argument("--bodies", type=int, default=80, help="body count for --scenario cluster")
    parser.add_argument("--barnes-hut", action="store_true", help="use Barnes-Hut force approximation")
    parser.add_argument("--theta", type=float, default=0.5, help="Barnes-Hut accuracy/speed tradeoff")
    parser.add_argument("--restitution", type=float, default=0.0,
                         help="0 = merge on collision, 1 = fully elastic bounce")
    parser.add_argument("--integrator", choices=["verlet", "euler"], default="verlet",
                         help="verlet conserves energy much better; euler is cheaper and simpler")
    parser.add_argument("--load", type=str, default=None, help="load a scenario from a JSON file")
    parser.add_argument("--save", type=str, default=None, help="save the scenario to JSON and exit")
    parser.add_argument("--view-au", type=float, default=None,
                         help="initial view radius, in AU (default: 3 for solar, 0.25 for cluster)")
    args = parser.parse_args()
    integrator = EulerIntegrator() if args.integrator == "euler" else VerletIntegrator()

    if args.load:
        sim = Simulation(use_barnes_hut=args.barnes_hut, theta=args.theta,
                          restitution=args.restitution, integrator=integrator)
        sim.load_state(args.load)
    elif args.scenario == "cluster":
        sim = build_random_cluster(n=args.bodies)
        sim.use_barnes_hut = args.barnes_hut
        sim.theta = args.theta
        sim.restitution = args.restitution
        sim.integrator = integrator
    else:
        sim = build_solar_system()
        sim.use_barnes_hut = args.barnes_hut
        sim.theta = args.theta
        sim.restitution = args.restitution
        sim.integrator = integrator

    if args.barnes_hut and len(sim.bodies) < sim.barnes_hut_threshold:
        print(f"Note: with {len(sim.bodies)} bodies, direct calculation is actually faster "
              f"than Barnes-Hut in pure Python (measured crossover is ~{sim.barnes_hut_threshold} "
              f"bodies) - Simulation will use direct calculation regardless of --barnes-hut here.")

    if args.save:
        sim.save_state(args.save)
        print(f"Saved {len(sim.bodies)} bodies to {args.save}")
        return

    if args.scenario == "cluster":
        dt, steps_per_frame = 600, 1              # smaller timestep, one step/frame -> stays smooth
        view_au = args.view_au if args.view_au is not None else 0.25
    else:
        dt, steps_per_frame = 6 * 3600, 4
        view_au = args.view_au if args.view_au is not None else 3.0

    viz = Visualizer(sim, steps_per_frame=steps_per_frame, dt=dt, view_radius_au=view_au)
    viz.run()


if __name__ == "__main__":
    main()
