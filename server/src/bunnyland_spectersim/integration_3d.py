"""Optional, lazily imported 3D appearance for wards."""

from .rituals import WardComponent


def install_spectersim_3d(actor, context) -> None:
    if context.plugins is None or not context.plugins.enabled("bunnyland.3d"):
        return
    from bunnyland_3d import (
        EntityVisualContribution,
        EntityVisualRule,
        ModelAsset,
        ModelTransform,
        PrimitivePart3D,
        ProceduralModelSource,
        VisualMaterial3D,
        VisualNodePatch,
        register_entity_visuals,
        register_models,
    )

    owner = "bunnyland.spectersim"
    model_key = f"{owner}/ward"
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
            contribution=EntityVisualContribution(base_model_key=model_key),
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
                predicate=lambda entity, lo=lower, hi=threshold: entity.has_component(WardComponent)
                and lo <= entity.get_component(WardComponent).strength < hi,
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
