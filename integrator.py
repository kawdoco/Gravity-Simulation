"""integrator.py - ways to advance bodies forward in time."""
from abc import ABC, abstractmethod


class Integrator(ABC):  # Abstraction
    @abstractmethod  # Abstraction
    def step(self, bodies, compute_forces, dt):
        raise NotImplementedError


class EulerIntegrator(Integrator):  # Inheritance
    """Semi-implicit Euler - simple, but leaks energy over time."""

    def step(self, bodies, compute_forces, dt):  # Polymorphism
        forces = compute_forces(bodies)
        for body in bodies:
            body.apply_force(forces[body], dt)
            body.position = body.position + body.velocity * dt
            body.record_trail()


class VerletIntegrator(Integrator):  # Inheritance
    """Velocity Verlet - uses acceleration at both ends of the step:
        x(t+dt) = x(t) + v(t)*dt + 1/2 * a(t) * dt^2
        v(t+dt) = v(t) + 1/2 * (a(t) + a(t+dt)) * dt
    """

    def step(self, bodies, compute_forces, dt):  # Polymorphism
        forces_start = compute_forces(bodies)
        accel_start = {body: forces_start[body] / body.mass for body in bodies}

        for body in bodies:
            body.position = (body.position + body.velocity * dt
                              + accel_start[body] * (0.5 * dt * dt))

        forces_end = compute_forces(bodies)
        for body in bodies:
            accel_end = forces_end[body] / body.mass
            body.velocity = body.velocity + (accel_start[body] + accel_end) * (0.5 * dt)
            body.record_trail()


class RK4Integrator(Integrator):  # Inheritance
    """Classic 4th-order Runge-Kutta - 4 force evaluations per step
    (vs Verlet's 2), each at a different in-between state:
        k1 = derivative(state)                at t
        k2 = derivative(state + dt/2 * k1)    at t + dt/2
        k3 = derivative(state + dt/2 * k2)    at t + dt/2
        k4 = derivative(state + dt   * k3)    at t + dt
        state += dt/6 * (k1 + 2*k2 + 2*k3 + k4)
    Higher per-step accuracy than Verlet, but not symplectic - on a
    highly eccentric orbit it can actually drift worse over many
    orbits (see main.py --compare-integrators)."""

    def step(self, bodies, compute_forces, dt):  # Polymorphism
        start = {body: (body.position, body.velocity) for body in bodies}

        def accelerations(forces):
            return {body: forces[body] / body.mass for body in bodies}

        k1_v = {body: start[body][1] for body in bodies}
        k1_a = accelerations(compute_forces(bodies))

        for body in bodies:
            pos0, _ = start[body]
            body.position = pos0 + k1_v[body] * (dt / 2)
        k2_v = {body: start[body][1] + k1_a[body] * (dt / 2) for body in bodies}
        k2_a = accelerations(compute_forces(bodies))

        for body in bodies:
            pos0, _ = start[body]
            body.position = pos0 + k2_v[body] * (dt / 2)
        k3_v = {body: start[body][1] + k2_a[body] * (dt / 2) for body in bodies}
        k3_a = accelerations(compute_forces(bodies))

        for body in bodies:
            pos0, _ = start[body]
            body.position = pos0 + k3_v[body] * dt
        k4_v = {body: start[body][1] + k3_a[body] * dt for body in bodies}
        k4_a = accelerations(compute_forces(bodies))

        for body in bodies:
            pos0, vel0 = start[body]
            body.position = pos0 + (k1_v[body] + k2_v[body] * 2 + k3_v[body] * 2 + k4_v[body]) * (dt / 6)
            body.velocity = vel0 + (k1_a[body] + k2_a[body] * 2 + k3_a[body] * 2 + k4_a[body]) * (dt / 6)
            body.record_trail()
