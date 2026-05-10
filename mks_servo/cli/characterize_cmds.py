"""mks-servo characterize subcommand."""
from __future__ import annotations
import click

from mks_servo.motor import Motor
from mks_servo.characterize import CharacterizationSuite


@click.command()
@click.argument("name_or_path")
@click.option("--suite", default="mvp",
              type=click.Choice(["mvp", "full"]),
              help="Test suite to run")
@click.option("--port", default=None, help="Serial port override")
@click.option("--update-profile", is_flag=True,
              help="Write characterization back into the profile (in-memory)")
@click.option("--save", is_flag=True,
              help="Save the YAML after updating (requires --update-profile)")
def characterize_cmd(name_or_path, suite, port, update_profile, save):
    """Run characterization tests against a motor and report results."""
    with Motor.from_profile(name_or_path, port=port) as m:
        s = CharacterizationSuite(m)
        if suite == "mvp":
            results = s.run_mvp()
        else:
            results = s.run_full()

        # Brief summary
        if results.p1 is not None:
            click.echo(f"P1 precision: sigma={results.p1.sigma_deg:.4f}°, "
                       f"peak={results.p1.peak_deg:.4f}°")
        if results.p3 is not None:
            for rpm, rms in zip(results.p3.rpm_samples,
                                results.p3.rms_error_deg):
                click.echo(f"P3 error @ {rpm:>5d} RPM: rms={rms:.4f}°")
        if results.p5 is not None:
            click.echo(f"P5 follow @ {results.p5.rpm} RPM: "
                       f"max={results.p5.max_follow_err_deg:.3f}°, "
                       f"rms={results.p5.rms_follow_err_deg:.3f}°")
        if results.s2 is not None:
            click.echo(f"S2 acceleration: target={results.s2.target_rpm}, "
                       f"max_observed={results.s2.max_observed_rpm} RPM")

        if update_profile:
            s.update_profile()
            click.echo("profile updated in-memory.")
            if save:
                m.profile.save()
                click.echo(f"profile saved to {m.profile.path}")
        elif save:
            click.echo("warning: --save without --update-profile has no effect",
                       err=True)
