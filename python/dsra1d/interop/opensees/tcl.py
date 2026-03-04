from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from dsra1d.config.models import BoundaryCondition, Layer, MaterialType, ProjectConfig


@dataclass(slots=True)
class LayerSlice:
    index: int
    name: str
    material: MaterialType
    z_top_m: float
    z_bot_m: float
    thickness_m: float
    n_sublayers: int
    dz_m: float


@dataclass(slots=True)
class ElementSlice:
    index: int
    layer_index: int
    layer_name: str
    material: MaterialType
    z_top_m: float
    z_bot_m: float
    dz_m: float


def build_layer_slices(
    config: ProjectConfig,
    points_per_wavelength: float = 10.0,
    min_dz_m: float = 0.25,
) -> list[LayerSlice]:
    f_max = float(config.analysis.f_max)
    z_top = 0.0
    slices: list[LayerSlice] = []

    for idx, layer in enumerate(config.profile.layers, start=1):
        target_dz = max(layer.vs_m_s / (points_per_wavelength * f_max), min_dz_m)
        n_sub = max(1, math.ceil(layer.thickness_m / target_dz))
        dz = layer.thickness_m / n_sub
        z_bot = z_top + layer.thickness_m
        slices.append(
            LayerSlice(
                index=idx,
                name=layer.name,
                material=layer.material,
                z_top_m=z_top,
                z_bot_m=z_bot,
                thickness_m=layer.thickness_m,
                n_sublayers=n_sub,
                dz_m=dz,
            )
        )
        z_top = z_bot

    return slices


def build_element_slices(layer_slices: list[LayerSlice]) -> list[ElementSlice]:
    elem_idx = 1
    element_slices: list[ElementSlice] = []
    for layer in layer_slices:
        z_cursor = layer.z_top_m
        for _ in range(layer.n_sublayers):
            z_top = z_cursor
            z_bot = z_cursor + layer.dz_m
            element_slices.append(
                ElementSlice(
                    index=elem_idx,
                    layer_index=layer.index,
                    layer_name=layer.name,
                    material=layer.material,
                    z_top_m=z_top,
                    z_bot_m=z_bot,
                    dz_m=layer.dz_m,
                )
            )
            z_cursor = z_bot
            elem_idx += 1
    return element_slices


def _param(layer: Layer, key: str, default: float) -> float:
    raw = layer.material_params.get(key, default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _material_definition_lines(tag: int, layer: Layer, g_m_s2: float) -> list[str]:
    rho = max(layer.unit_weight_kn_m3 / g_m_s2, 1.0e-6)
    optional_tail = " ".join(f"{val:.12g}" for val in layer.material_optional_args)
    optional_suffix = f" {optional_tail}" if optional_tail else ""
    if layer.material == MaterialType.PM4SAND:
        dr = _param(layer, "Dr", 0.45)
        g0 = _param(layer, "G0", 600.0)
        hpo = _param(layer, "hpo", 0.53)
        return [
            f"# Layer {tag} PM4Sand calibration-ready block",
            (
                "nDMaterial PM4Sand "
                f"{tag} {dr:.6f} {g0:.6f} {hpo:.6f} {rho:.8f}{optional_suffix}"
            ),
        ]
    if layer.material == MaterialType.PM4SILT:
        su = _param(layer, "Su", 35.0)
        su_rat = _param(layer, "Su_Rat", 0.25)
        g_o = _param(layer, "G_o", 500.0)
        h_po = _param(layer, "h_po", 0.60)
        return [
            f"# Layer {tag} PM4Silt calibration-ready block",
            (
                "nDMaterial PM4Silt "
                f"{tag} {su:.6f} {su_rat:.6f} {g_o:.6f} {h_po:.6f} {rho:.8f}{optional_suffix}"
            ),
        ]

    nu = _param(layer, "nu", 0.30)
    shear_mod = rho * layer.vs_m_s * layer.vs_m_s
    young_mod = 2.0 * shear_mod * (1.0 + nu)
    return [
        f"# Layer {tag} Elastic fallback material",
        f"nDMaterial ElasticIsotropic {tag} {young_mod:.6f} {nu:.6f} {rho:.8f}",
    ]


def _format_float_list(values: list[float]) -> str:
    return " ".join(f"{val:.8f}" for val in values)


def _format_int_list(values: list[int]) -> str:
    return " ".join(str(val) for val in values)


def validate_tcl_script(script: str) -> None:
    if script.count("{") != script.count("}"):
        raise ValueError("Generated Tcl has unbalanced braces.")
    required_tokens = [
        "model BasicBuilder -ndm 2 -ndf 3",
        "set motion_file",
        "set output_dir",
        "nDMaterial",
        "element quadUP",
        "pattern UniformExcitation",
        "surface_acc.out",
        "pwp_ru.out",
    ]
    missing = [token for token in required_tokens if token not in script]
    if missing:
        raise ValueError(f"Generated Tcl missing required tokens: {missing}")


def render_tcl(config: ProjectConfig, motion_file: Path, output_dir: Path) -> str:
    dt = config.analysis.dt or (1.0 / (20.0 * config.analysis.f_max))
    g = 9.81
    column_width = config.opensees.column_width_m
    thickness = config.opensees.thickness_m
    fluid_bulk = config.opensees.fluid_bulk_modulus
    fluid_mass = config.opensees.fluid_mass_density
    h_perm = config.opensees.h_perm
    v_perm = config.opensees.v_perm
    gravity_steps = config.opensees.gravity_steps
    layer_slices = build_layer_slices(config)
    element_slices = build_element_slices(layer_slices)
    total_depth = sum(layer.thickness_m for layer in config.profile.layers)
    gamma_depth_sum = sum(
        layer.unit_weight_kn_m3 * layer.thickness_m
        for layer in config.profile.layers
    )
    avg_gamma = gamma_depth_sum / total_depth
    sigma_v_ref = max(avg_gamma * total_depth * 0.5, 1.0e-3)
    base_layer = config.profile.layers[-1]
    base_rho = max(base_layer.unit_weight_kn_m3 / g, 1.0e-6)
    base_vs = max(base_layer.vs_m_s, 1.0e-6)

    dz_list = _format_float_list([elem.dz_m for elem in element_slices])
    mat_list = _format_int_list([elem.layer_index for elem in element_slices])
    pm4_mat_tags = _format_int_list(
        [
            idx
            for idx, layer in enumerate(config.profile.layers, start=1)
            if layer.material in {MaterialType.PM4SAND, MaterialType.PM4SILT}
        ]
    )

    lines: list[str] = []
    lines.append("# Auto-generated by StrataWave")
    lines.append("# 1D SH-like u-p column assembly for PM4Sand/PM4Silt calibration-ready workflows")
    lines.append("wipe")
    lines.append("model BasicBuilder -ndm 2 -ndf 3")
    lines.append(f"set motion_file \"{motion_file.as_posix()}\"")
    lines.append(f"set output_dir \"{output_dir.as_posix()}\"")
    lines.append("file mkdir $output_dir")
    lines.append(f"set dt {dt:.8f}")
    lines.append(f"set colWidth {column_width:.8f}")
    lines.append(f"set thickness {thickness:.8f}")
    lines.append(f"set g {g:.8f}")
    lines.append(f"set fBulk {fluid_bulk:.8f}")
    lines.append(f"set fMass {fluid_mass:.8f}")
    lines.append(f"set hPermInput {h_perm:.8f}")
    lines.append(f"set vPermInput {v_perm:.8f}")
    lines.append("# Convert hydraulic conductivity (m/s) to quadUP permeability coefficient")
    lines.append("set permDen [expr {$g * $fMass}]")
    lines.append("if {$permDen <= 0.0} { set permDen 9.81 }")
    lines.append("set hPerm [expr {$hPermInput / $permDen}]")
    lines.append("set vPerm [expr {$vPermInput / $permDen}]")
    lines.append("# Use high permeability during gravity to avoid locked pore-pressure transients")
    lines.append("set hPermGrav 1.0")
    lines.append("set vPermGrav 1.0")
    lines.append(f"set sigmaVRef {sigma_v_ref:.8f}")
    lines.append(f"set nLayers {len(layer_slices)}")
    lines.append(f"set nElemY {len(element_slices)}")
    lines.append("set nNodeY [expr {$nElemY + 1}]")
    lines.append(f"set dzList {{{dz_list}}}")
    lines.append(f"set matByElem {{{mat_list}}}")
    lines.append(f"set pm4MatTags {{{pm4_mat_tags}}}")
    lines.append("")
    lines.append("# Material definitions")
    for idx, layer in enumerate(config.profile.layers, start=1):
        lines.extend(_material_definition_lines(idx, layer, g))
    lines.append("")
    lines.append("# Node assembly (2-node wide column for 1D emulation)")
    lines.append("set y 0.0")
    lines.append("set nodeL(1) 1001")
    lines.append("set nodeR(1) 2001")
    lines.append("node $nodeL(1) 0.0 $y")
    lines.append("node $nodeR(1) $colWidth $y")
    lines.append("for {set i 2} {$i <= $nNodeY} {incr i} {")
    lines.append("    set dz [lindex $dzList [expr {$i - 2}]]")
    lines.append("    set y [expr {$y - $dz}]")
    lines.append("    set nodeL($i) [expr {1000 + $i}]")
    lines.append("    set nodeR($i) [expr {2000 + $i}]")
    lines.append("    node $nodeL($i) 0.0 $y")
    lines.append("    node $nodeR($i) $colWidth $y")
    lines.append("}")
    lines.append("")
    lines.append("# Boundary conditions and 1D constraints")
    lines.append("for {set i 1} {$i <= $nNodeY} {incr i} {")
    lines.append("    equalDOF $nodeL($i) $nodeR($i) 1")
    lines.append("}")
    lines.append("for {set i 2} {$i < $nNodeY} {incr i} {")
    lines.append("    fix $nodeL($i) 0 1 0")
    lines.append("    fix $nodeR($i) 0 1 0")
    lines.append("}")
    lines.append("# Drained top boundary")
    lines.append("fix $nodeL(1) 0 1 1")
    lines.append("fix $nodeR(1) 0 1 1")
    if config.boundary_condition == BoundaryCondition.RIGID:
        lines.append("# Base boundary: rigid")
        lines.append("fix $nodeL($nNodeY) 1 1 1")
        lines.append("fix $nodeR($nNodeY) 1 1 1")
    else:
        lines.append("# Base boundary: elastic half-space (Lysmer dashpot in DOF-1)")
        lines.append("fix $nodeL($nNodeY) 0 1 1")
        lines.append("fix $nodeR($nNodeY) 0 1 1")
        lines.append("set dashL 900001")
        lines.append("set dashR 900002")
        lines.append("node $dashL 0.0 $y")
        lines.append("node $dashR $colWidth $y")
        lines.append("fix $dashL 1 1 1")
        lines.append("fix $dashR 1 1 1")
        lines.append(f"set baseRho {base_rho:.8f}")
        lines.append(f"set baseVs {base_vs:.8f}")
        lines.append("set dashpotC [expr {$baseRho * $baseVs * $colWidth * $thickness}]")
        lines.append("uniaxialMaterial Viscous 9001 $dashpotC 1.0")
        lines.append("element zeroLength 9001 $nodeL($nNodeY) $dashL -mat 9001 -dir 1")
        lines.append("element zeroLength 9002 $nodeR($nNodeY) $dashR -mat 9001 -dir 1")
    lines.append("")
    lines.append("# u-p elements")
    lines.append("set eleTag 1")
    lines.append("for {set e 1} {$e <= $nElemY} {incr e} {")
    lines.append("    set n1 $nodeL($e)")
    lines.append("    set n2 $nodeL([expr {$e + 1}])")
    lines.append("    set n3 $nodeR([expr {$e + 1}])")
    lines.append("    set n4 $nodeR($e)")
    lines.append("    set matTag [lindex $matByElem [expr {$e - 1}]]")
    lines.append(
        "    element quadUP $eleTag $n1 $n2 $n3 $n4 "
        "$thickness $matTag $fBulk $fMass $hPermGrav $vPermGrav 0.0 -$g"
    )
    lines.append("    incr eleTag")
    lines.append("}")
    lines.append("# Permeability parameter tags for post-gravity update")
    lines.append("set hPermParamTags {}")
    lines.append("set vPermParamTags {}")
    lines.append("set pTag 1")
    lines.append("for {set e 1} {$e <= $nElemY} {incr e} {")
    lines.append("    parameter $pTag element $e hPerm")
    lines.append("    lappend hPermParamTags $pTag")
    lines.append("    incr pTag")
    lines.append("    parameter $pTag element $e vPerm")
    lines.append("    lappend vPermParamTags $pTag")
    lines.append("    incr pTag")
    lines.append("}")
    lines.append("")
    lines.append("# Gravity stage")
    for idx in range(1, len(config.profile.layers) + 1):
        lines.append(f"updateMaterialStage -material {idx} -stage 0")
    lines.append("constraints Penalty 1.0e16 1.0e16")
    lines.append("numberer RCM")
    lines.append("system BandGeneral")
    lines.append("test NormDispIncr 1.0e-6 50 0")
    lines.append("algorithm Newton")
    lines.append("integrator Newmark 0.6 0.3025")
    lines.append("analysis Transient")
    lines.append(f"set okG [analyze {gravity_steps} $dt]")
    lines.append("if {$okG != 0} {")
    lines.append("    algorithm ModifiedNewton")
    lines.append("    test NormDispIncr 1.0e-5 80 0")
    lines.append(f"    set okG [analyze {max(gravity_steps * 2, 2)} [expr {{$dt / 2.0}}]]")
    lines.append("}")
    lines.append("if {$okG != 0} {")
    lines.append("    puts \"Gravity stage did not converge.\"")
    lines.append("    exit $okG")
    lines.append("}")
    lines.append("loadConst -time 0.0")
    lines.append("# Restore user-defined permeability for dynamic stage")
    lines.append("foreach pTag $hPermParamTags {")
    lines.append("    updateParameter $pTag $hPerm")
    lines.append("}")
    lines.append("foreach pTag $vPermParamTags {")
    lines.append("    updateParameter $pTag $vPerm")
    lines.append("}")
    lines.append("")
    lines.append("# Dynamic stage")
    for idx in range(1, len(config.profile.layers) + 1):
        lines.append(f"updateMaterialStage -material {idx} -stage 1")
    lines.append(
        "# PM4 requires FirstCall initialization after stage switch "
        "when defaults are stress-dependent"
    )
    lines.append("for {set e 1} {$e <= $nElemY} {incr e} {")
    lines.append("    set matTag [lindex $matByElem [expr {$e - 1}]]")
    lines.append("    if {[lsearch -exact $pm4MatTags $matTag] >= 0} {")
    lines.append("        setParameter -value 0 -ele $e FirstCall $matTag")
    lines.append("    }")
    lines.append("}")
    lines.append("timeSeries Path 1 -dt $dt -filePath $motion_file -factor 1.0")
    lines.append("pattern UniformExcitation 1 1 -accel 1")
    lines.append(
        "recorder Node -file \"$output_dir/surface_acc.out\" "
        "-time -node $nodeL(1) -dof 1 accel"
    )
    lines.append("set pwpNode $nodeL([expr {int(($nNodeY + 1) / 2)}])")
    lines.append("recorder Node -file \"$output_dir/pwp_raw.out\" -time -node $pwpNode -dof 3 disp")
    lines.append("set in [open $motion_file r]")
    lines.append("set raw [split [string trim [read $in]] \"\\n\"]")
    lines.append("close $in")
    lines.append("set nSteps [llength $raw]")
    lines.append("if {$nSteps < 2} { set nSteps 2 }")
    lines.append("constraints Penalty 1.0e16 1.0e16")
    lines.append("numberer RCM")
    lines.append("system BandGeneral")
    lines.append("test NormDispIncr 1.0e-5 50 0")
    lines.append("algorithm KrylovNewton")
    lines.append("integrator Newmark 0.6 0.3025")
    lines.append("analysis Transient")
    lines.append("set ok 0")
    lines.append("for {set i 1} {$i <= $nSteps} {incr i} {")
    lines.append("    set ok [analyze 1 $dt]")
    lines.append("    if {$ok != 0} {")
    lines.append("        algorithm ModifiedNewton")
    lines.append("        test NormDispIncr 1.0e-5 80 0")
    lines.append("        set ok [analyze 2 [expr {$dt / 2.0}]]")
    lines.append("        algorithm KrylovNewton")
    lines.append("        test NormDispIncr 1.0e-5 50 0")
    lines.append("    }")
    lines.append("    if {$ok != 0} { break }")
    lines.append("}")
    lines.append("if {$ok != 0} {")
    lines.append("    puts \"Dynamic analysis failed after fallback attempt.\"")
    lines.append("}")
    lines.append("")
    lines.append("# Convert pore-pressure record to approximate ru ratio")
    lines.append("if {[file exists \"$output_dir/pwp_raw.out\"]} {")
    lines.append("    set fin [open \"$output_dir/pwp_raw.out\" r]")
    lines.append("    set fout [open \"$output_dir/pwp_ru.out\" w]")
    lines.append("    while {[gets $fin line] >= 0} {")
    lines.append("        set v [string trim $line]")
    lines.append("        if {$v eq \"\"} { continue }")
    lines.append("        set t 0.0")
    lines.append("        set pwp 0.0")
    lines.append("        scan $v \"%f %f\" t pwp")
    lines.append("        set ru [expr {$pwp / $sigmaVRef}]")
    lines.append("        puts $fout \"$t $ru\"")
    lines.append("    }")
    lines.append("    close $fin")
    lines.append("    close $fout")
    lines.append("} else {")
    lines.append("    set fout [open \"$output_dir/pwp_ru.out\" w]")
    lines.append("    puts $fout \"0.0 0.0\"")
    lines.append("    puts $fout \"$dt 0.0\"")
    lines.append("    close $fout")
    lines.append("}")
    lines.append("if {![file exists \"$output_dir/surface_acc.out\"]} {")
    lines.append("    set fout [open \"$output_dir/surface_acc.out\" w]")
    lines.append("    puts $fout \"0.0\"")
    lines.append("    puts $fout \"0.0\"")
    lines.append("    close $fout")
    lines.append("}")
    lines.append("puts \"OpenSees run complete\"")
    lines.append("exit $ok")
    script = "\n".join(lines) + "\n"
    validate_tcl_script(script)
    return script

