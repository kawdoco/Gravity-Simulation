"""main.py - entry point. No arguments -> in-app menu; any flag -> CLI path."""
import argparse
import math
import random
import sys

from vector import Vector3D
from body import Star, Planet, CelestialBody
from simulation import Simulation
from rendering import Visualizer
from integrator import EulerIntegrator, VerletIntegrator, RK4Integrator
from constants import G, AU


def build_solar_system():
    sim = Simulation()
    sun = Star("Sun", mass=1.989e30, radius=6.9e8,
               position=Vector3D(0, 0, 0), velocity=Vector3D(0, 0, 0), color="#FFF4D6")
    sim.add_body(sun)

    # name, mass (kg), distance from sun (m), orbital speed (m/s), color
    
    planet_data = [
        ("Mercury", 3.285e23, 5.79e10, 47400, "#9C9490"),
        ("Venus",   4.867e24, 1.082e11, 35020, "#E8D6A8"),
        ("Earth",   5.972e24, 1.496e11, 29780, "#4E7CB0"),
        ("Mars",    6.39e23,  2.279e11, 24070, "#B8552E"),
    ]
    for name, mass, distance, speed, color in planet_data:
        position = Vector3D(distance, 0, 0)
        velocity = Vector3D(0, speed, 0)  
        sim.add_body(Planet(name, mass, radius=CelestialBody.radius_from_mass(mass, density=5000),
                             position=position, velocity=velocity, color=color))


    outer_planet_data = [
        ("Jupiter", 1.898e27, 3.5904e11, 19228, 6.991e7, "#C9A876", False),
        ("Saturn",  5.683e26, 4.9368e11, 16398, 5.823e7, "#E3C99A", True),
        ("Uranus",  8.681e25, 6.2832e11, 14535, 2.536e7, "#9FD4D6", False),
        ("Neptune", 1.024e26, 7.6296e11, 13190, 2.462e7, "#4E6FE0", False),
    ]
    for name, mass, distance, speed, radius, color, has_ring in outer_planet_data:
        position = Vector3D(distance, 0, 0)
        velocity = Vector3D(0, speed, 0)
        sim.add_body(Planet(name, mass, radius=radius, position=position, velocity=velocity,
                             color=color, has_ring=has_ring))
    return sim


def build_three_body():
    """The classic "figure-eight" three-body solution (Moore 1993) -
    three equal masses chasing each other around one shared path
    forever. Given in normalized units (G=1, mass=1); scaled here
    into the simulation's real kg/m/s units."""
    mass = 2e30           # ~1 solar mass, per body
    length_scale = AU
    time_scale = (length_scale ** 3 / (G * mass)) ** 0.5
    velocity_scale = length_scale / time_scale

    # Moore's dimensionless initial conditions for the figure-eight.
    pos_a = Vector3D(0.97000436 * length_scale, -0.24308753 * length_scale, 0)
    pos_b = Vector3D(-0.97000436 * length_scale, 0.24308753 * length_scale, 0)
    pos_c = Vector3D(0, 0, 0)
    vel_c = Vector3D(-0.93240737 * velocity_scale, -0.86473146 * velocity_scale, 0)
    vel_a = vel_b = Vector3D(-vel_c.x / 2, -vel_c.y / 2, 0)

    sim = Simulation()
    # Planet, not Star - only Planet instances get a drawn trail
   
    sim.add_body(Planet("A", mass=mass, radius=6.9e8, position=pos_a, velocity=vel_a, color="#FF6B6B"))
    sim.add_body(Planet("B", mass=mass, radius=6.9e8, position=pos_b, velocity=vel_b, color="#6BCBFF"))
    sim.add_body(Planet("C", mass=mass, radius=6.9e8, position=pos_c, velocity=vel_c, color="#FFD76B"))
    return sim


def build_gravity_assist():
    mass_sun = 1.989e30
    mass_jupiter = 1.898e27
    jupiter_orbit_radius = 7.786e11
    jupiter_speed = (G * mass_sun / jupiter_orbit_radius) ** 0.5

    sim = Simulation()
    sim.add_body(Star("Sun", mass=mass_sun, radius=6.9e8,
                       position=Vector3D(0, 0, 0), velocity=Vector3D(0, 0, 0), color="#FFF4D6"))
    sim.add_body(Planet("Jupiter", mass=mass_jupiter, radius=6.991e7,
                         position=Vector3D(jupiter_orbit_radius, 0, 0),
                         velocity=Vector3D(0, jupiter_speed, 0), color="#C9A876"))

    launch_position = Vector3D(1.5 * AU, -2.0 * AU, 0)
    launch_speed = (G * mass_sun / launch_position.magnitude()) ** 0.5 * 1.3
    launch_angle = math.radians(34.0)
    launch_velocity = Vector3D(launch_speed * math.cos(launch_angle),
                                launch_speed * math.sin(launch_angle), 0)
    sim.add_body(Planet("Voyager", mass=1e3, radius=5, position=launch_position,
                         velocity=launch_velocity, color="#E0E0E0"))
    return sim


def build_random_cluster(n=200, seed=None):
    rng = random.Random(seed)
    sim = Simulation()

    center_mass = 8e24
    sim.add_body(Star("Core", center_mass, CelestialBody.radius_from_mass(center_mass, 4000),
                       Vector3D(0, 0, 0), Vector3D(0, 0, 0), "#FFF4D6"))

    rock_palette = ["#B7AFA3", "#9C9490", "#A89A82", "#8E8B86", "#C2B49B"]

    for i in range(n):
        r = rng.uniform(2e9, 3e10)
        theta = rng.uniform(0, 2 * math.pi)
        phi = rng.uniform(-0.3, 0.3)  # keep the cluster disk-shaped
        position = Vector3D(r * math.cos(theta), r * math.sin(theta), r * math.sin(phi))

       
        speed = (G * center_mass / r) ** 0.5 * rng.uniform(0.8, 1.1)
        tangent = Vector3D(-position.y, position.x, 0).normalized()
        velocity = tangent * speed

        mass = rng.uniform(1e20, 5e22)
        sim.add_body(Planet(f"B{i}", mass, CelestialBody.radius_from_mass(mass, density=3000),
                             position, velocity, color=rng.choice(rock_palette)))
    return sim


def _make_integrator(name):  # Polymorphism - picks which Integrator subclass to instantiate
    return {"euler": EulerIntegrator, "verlet": VerletIntegrator, "rk4": RK4Integrator}[name]()


def _total_energy(bodies):
    kinetic = sum(0.5 * b.mass * b.velocity.magnitude() ** 2 for b in bodies)
    potential = 0.0
    for i, a in enumerate(bodies):
        for b in bodies[i + 1:]:
            r = (a.position - b.position).magnitude()
            if r > 0:
                potential -= G * a.mass * b.mass / r
    return kinetic + potential


def compare_integrators(scenario, n_bodies=80, sim_days=2000, dt=None):
    base_dt, _, _ = _scenario_defaults(scenario)
    if dt is None:
        dt = base_dt * 2
    n_steps = int(sim_days * 86400 / dt)
    print(f"Comparing integrators: {scenario} scenario, {sim_days} simulated days "
          f"({n_steps} steps at dt={dt / 3600:.1f}h each - {dt / base_dt:.0f}x the normal "
          f"production step, deliberately coarsened to make the comparison visible)\n")

    rows = []
    for name in ("euler", "verlet", "rk4"):
        sim = _build_scenario(scenario, n_bodies=n_bodies)
        sim.integrator = _make_integrator(name)
        e0 = _total_energy(sim.bodies)
        for _ in range(n_steps):
            sim.step(dt)
        e1 = _total_energy(sim.bodies)
        drift_pct = 100 * (e1 - e0) / abs(e0) if e0 != 0 else float("nan")
        rows.append((name, e0, e1, drift_pct))

    name_w = max(len(n) for n, *_ in rows)
    for name, e0, e1, drift_pct in rows:
        print(f"  {name.capitalize():<{name_w + 1}} start={e0: .6e} J   end={e1: .6e} J   drift={drift_pct:+.4f}%")
    print("\nSmaller |drift| = better energy conservation over this run - the true physics")
    print("conserves this exactly, so any change is numerical error, not real dynamics.")
    print("RK4 costs ~4x Euler's force evaluations per step, Verlet ~2x (see integrator.py).")


def _build_scenario(scenario, n_bodies=80, seed=None):
    if scenario == "cluster":
        return build_random_cluster(n=n_bodies, seed=seed)
    if scenario == "three_body":
        return build_three_body()
    if scenario == "gravity_assist":
        return build_gravity_assist()
    return build_solar_system()


def _scenario_defaults(scenario):
    """dt, steps_per_frame, view_au per scenario - kept in one place
    so _launch and the CLI --spiral path can't disagree."""
    if scenario == "cluster":
        return 600, 1, 0.25
    if scenario == "three_body":
        return 10 * 3600, 4, 1.8  # ~880 steps per ~367-day figure-eight period
    if scenario == "gravity_assist":
        return 3 * 3600, 24, 6.0  # fine enough to resolve the close Jupiter flyby
    return 6 * 3600, 4, 5.6


def _launch(sim, scenario, fullscreen, view_au=None, motion_mode="static", drift_already_applied=False):
    dt, steps_per_frame, default_view_au = _scenario_defaults(scenario)

    if sim.use_barnes_hut and len(sim.bodies) < sim.barnes_hut_threshold:
        print(f"Note: with {len(sim.bodies)} bodies, direct calculation is actually faster "
              f"than Barnes-Hut in pure Python (measured crossover is ~{sim.barnes_hut_threshold} "
              f"bodies) - Simulation will use direct calculation regardless of the setting here.")

    viz = Visualizer(sim, steps_per_frame=steps_per_frame, dt=dt,
                      view_radius_au=view_au if view_au is not None else default_view_au,
                      fullscreen=fullscreen, motion_mode=motion_mode,
                      drift_already_applied=drift_already_applied)
    viz.run()
    return not viz.quit_requested


def _run_from_menu():
    from menu import MainMenu
    while True:
        settings = MainMenu().run()
        if settings is None:
            return  # player quit from the menu itself

        integrator = _make_integrator(settings["integrator"])
        sim = _build_scenario(settings["scenario"], n_bodies=settings["bodies"])
        sim.use_barnes_hut = settings["barnes_hut"]
        sim.restitution = settings["collisions"]
        sim.integrator = integrator

        want_menu = _launch(sim, settings["scenario"], settings["fullscreen"],
                             motion_mode=settings["motion_mode"])
        if not want_menu:
            return  # closed the window from inside the simulation


def main():
    if len(sys.argv) == 1:
        _run_from_menu()
        return

    parser = argparse.ArgumentParser(description="OOP gravity simulation")
    parser.add_argument("--scenario", choices=["solar", "cluster", "three_body", "gravity_assist"],
                         default="solar")
    parser.add_argument("--bodies", type=int, default=80, help="body count for --scenario cluster")
    parser.add_argument("--barnes-hut", action="store_true", help="use Barnes-Hut force approximation")
    parser.add_argument("--theta", type=float, default=0.5, help="Barnes-Hut accuracy/speed tradeoff")
    parser.add_argument("--restitution", type=float, default=0.0,
                         help="0 = merge on collision, 1 = fully elastic bounce")
    parser.add_argument("--integrator", choices=["verlet", "euler", "rk4"], default="verlet",
                         help="verlet conserves energy much better than euler; rk4 is even more "
                              "accurate per step but costs 4x the force evaluations - see "
                              "--compare-integrators for a direct comparison")
    parser.add_argument("--compare-integrators", action="store_true",
                         help="run euler/verlet/rk4 on the same starting conditions and print "
                              "each one's energy drift, instead of launching the visualizer")
    parser.add_argument("--load", type=str, default=None, help="load a scenario from a JSON file")
    parser.add_argument("--save", type=str, default=None, help="save the scenario to JSON and exit")
    parser.add_argument("--view-au", type=float, default=None,
                         help="initial view radius, in AU (default: 5.6 for solar, 0.25 for cluster, "
                              "1.8 for three_body, 6.0 for gravity_assist)")
    parser.add_argument("--fullscreen", action="store_true", help="launch in fullscreen")
    parser.add_argument("--spiral", action="store_true",
                         help="spiral view: the whole system drifts through space "
                              "(see Simulation.apply_drift) instead of the classic fixed-star view")
    args = parser.parse_args()

    if args.compare_integrators:
        compare_integrators(args.scenario, n_bodies=args.bodies)
        return

    integrator = _make_integrator(args.integrator)

    if args.load:
        sim = Simulation(use_barnes_hut=args.barnes_hut, theta=args.theta,
                          restitution=args.restitution, integrator=integrator)
        sim.load_state(args.load)
    else:
        sim = _build_scenario(args.scenario, n_bodies=args.bodies)
        sim.use_barnes_hut = args.barnes_hut
        sim.theta = args.theta
        sim.restitution = args.restitution
        sim.integrator = integrator

    view_au = args.view_au if args.view_au is not None else _scenario_defaults(args.scenario)[2]
    drift_applied = False
    if args.spiral:
        # applied here, not left to Visualizer, so --spiral still works with --save
        sim.apply_drift(Visualizer.spiral_drift_vector(view_au))
        drift_applied = True

    if args.save:
        sim.save_state(args.save)
        print(f"Saved {len(sim.bodies)} bodies to {args.save}")
        return

    want_menu = _launch(sim, args.scenario, args.fullscreen, view_au=args.view_au,
                         motion_mode="spiral" if args.spiral else "static",
                         drift_already_applied=drift_applied)
    if want_menu:
        _run_from_menu()


if __name__ == "__main__":
    main()
