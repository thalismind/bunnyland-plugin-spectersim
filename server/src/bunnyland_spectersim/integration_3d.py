"""Optional, lazily imported 3D appearance for specters and wards."""

from .components import SpectralMarkerComponent
from .rituals import WardComponent


def install_spectersim_3d(actor, context) -> None:
    if context.plugins is None or not context.plugins.enabled("bunnyland.3d"):
        return
    from bunnyland_3d import (
        EntityVisualContribution,
        EntityVisualRule,
        ModelAsset,
        ModelTransform,
        ParticleSystem3D,
        PrimitivePart3D,
        ProceduralModelSource,
        VisualEffectDefinition,
        VisualEffectParticleLayer,
        VisualEffectStateRule,
        VisualMaterial3D,
        VisualNodePatch,
        register_entity_visuals,
        register_models,
        register_particle_systems,
        register_visual_effect_state_rules,
        register_visual_effects,
    )

    owner = "bunnyland.spectersim"
    model_key = f"{owner}/ward"
    register_particle_systems(
        actor,
        owner,
        (
            ParticleSystem3D(
                f"{owner}/ward-aura",
                blending="additive",
                vertical_motion="drift",
                vertical_scale=0.12,
                lateral_wobble=0.06,
                pulse_amount=0.25,
                pulse_speed=1.8,
            ),
            ParticleSystem3D(
                f"{owner}/specter-aura",
                blending="additive",
                vertical_motion="drift",
                vertical_scale=0.16,
                lateral_wobble=0.12,
                pulse_amount=0.2,
                pulse_speed=2.1,
            ),
        ),
    )
    register_visual_effects(
        actor,
        owner,
        (
            VisualEffectDefinition(
                f"{owner}/ward-aura",
                particle_layers=(
                    VisualEffectParticleLayer(
                        f"{owner}/ward-aura",
                        count=18,
                        bounds=(0.7, 0.5, 0.7),
                        color="#cda8ff",
                        size=0.055,
                        speed=0.18,
                        opacity=0.65,
                    ),
                ),
            ),
            VisualEffectDefinition(
                f"{owner}/specter",
                particle_layers=(
                    VisualEffectParticleLayer(
                        f"{owner}/specter-aura",
                        count=26,
                        bounds=(0.8, 1.5, 0.8),
                        color="#b9f5ff",
                        size=0.07,
                        speed=0.2,
                        opacity=0.7,
                    ),
                    VisualEffectParticleLayer(
                        f"{owner}/specter-aura",
                        count=14,
                        bounds=(0.65, 1.3, 0.65),
                        color="#68d8c0",
                        size=0.045,
                        speed=0.15,
                        opacity=0.58,
                    ),
                ),
            ),
        ),
    )
    register_visual_effect_state_rules(
        actor,
        owner,
        (
            VisualEffectStateRule(
                f"{owner}/ward-state",
                WardComponent,
                lambda entity: entity.has_component(WardComponent),
                f"{owner}/ward-aura",
            ),
            VisualEffectStateRule(
                f"{owner}/specter-state",
                SpectralMarkerComponent,
                lambda entity: entity.has_component(SpectralMarkerComponent),
                f"{owner}/specter",
            ),
        ),
    )
    register_models(
        actor,
        owner,
        (
            ModelAsset(
                key=model_key,
                source=ProceduralModelSource(
                    parts=(
                        PrimitivePart3D(
                            "ring",
                            "torus",
                            radius=0.7,
                            tube_radius=0.035,
                            transform=ModelTransform(
                                rotation=(1.5708, 0, 0), translation=(0, 0.03, 0)
                            ),
                            material=VisualMaterial3D(color="#9e78d1", emissive="#553080"),
                            roles=("state-indicator", "damageable"),
                        ),
                        PrimitivePart3D(
                            "focus",
                            "sphere",
                            radius=0.09,
                            transform=ModelTransform(translation=(0, 0.1, 0)),
                            material=VisualMaterial3D(color="#d7c1ff", emissive="#7e4fbd"),
                            roles=("state-indicator",),
                        ),
                    ),
                    required_roles=("state-indicator",),
                ),
            ),
        ),
    )
    rules = [
        EntityVisualRule(
            key=f"{owner}/ward",
            predicate=lambda entity: entity.has_component(WardComponent),
            contribution=EntityVisualContribution(
                base_model_key=model_key,
            ),
        )
    ]
    for name, threshold, scale, emissive in (
        ("weak", 0.34, 0.65, "#48265f"),
        ("steady", 0.67, 0.85, "#7548a1"),
        ("strong", float("inf"), 1.1, "#b47cff"),
    ):
        lower = 0.0 if name == "weak" else 0.34 if name == "steady" else 0.67
        rules.append(
            EntityVisualRule(
                key=f"{owner}/ward-{name}",
                priority=20,
                predicate=lambda entity, lo=lower, hi=threshold: (
                    entity.has_component(WardComponent)
                    and lo <= entity.get_component(WardComponent).strength < hi
                ),
                contribution=EntityVisualContribution(
                    patches=(
                        VisualNodePatch(
                            "state-indicator",
                            semantic_role=True,
                            transform=ModelTransform(scale=scale),
                            emissive=emissive,
                        ),
                    )
                ),
            )
        )
    register_entity_visuals(actor, owner, rules)


__all__ = ["install_spectersim_3d"]
