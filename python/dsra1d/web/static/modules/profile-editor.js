/**
 * GeoWave v2 — Soil Profile Editor
 * DEEPSOIL-style layer table with reference curve selector and calibration preview
 */
import { html, useState, useCallback, useEffect } from "./setup.js";
import { ChartCard, MultiSeriesChart, SoilProfilePlot } from "./charts.js";
import {
  fmt, defaultLayer, computeGmax,
  MATERIAL_TYPES, REFERENCE_CURVES, deepClone,
  normalizeMaterialParams, referenceCurveGroup,
  referenceCurvesForGroup, supportsCurveFitting,
  supportsReductionFormulation,
} from "./utils.js";
import * as api from "./api.js";

export function ProfileEditor({ wizard, setWizard }) {
  const layers = wizard.layers || [];
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [editorTab, setEditorTab] = useState("layer_properties");
  const [referenceGroup, setReferenceGroup] = useState("sand");
  const [calibPreview, setCalibPreview] = useState(null);
  const [profileDiagnostics, setProfileDiagnostics] = useState([]);
  const [refCurveData, setRefCurveData] = useState(null);
  const [setResult, setSetResult] = useState(null);
  const [autoFmax, setAutoFmax] = useState(25);
  const [autoPPW, setAutoPPW] = useState(10);
  const [autoMinDz, setAutoMinDz] = useState(0.5);
  const [autoMaxSub, setAutoMaxSub] = useState(20);
  const [savedMaterials, setSavedMaterials] = useState([]);
  const [materialLibraryName, setMaterialLibraryName] = useState("");
  const [setPreset, setSetPreset] = useState("reference");

  const SET_PRESETS = [
    { id: "very_small", label: "Very Small", strain: 1e-4 },
    { id: "small", label: "Small", strain: 1e-3 },
    { id: "reference", label: "Reference", strain: 1e-2 },
    { id: "strong", label: "Strong", strain: 5e-2 },
    { id: "extreme", label: "Extreme", strain: 1e-1 },
  ];

  function toApiLayer(layer, index = 0) {
    return {
      name: layer.name || `Layer ${index + 1}`,
      thickness_m: layer.thickness || layer.thickness_m || 5.0,
      vs_m_s: layer.vs || layer.vs_m_s || 150.0,
      unit_weight_kN_m3: layer.unit_weight || layer.unit_weight_kN_m3 || 18.0,
      material: layer.material || "mkz",
      reference_curve: layer.reference_curve || null,
      fit_stale: Boolean(layer.fit_stale),
      material_params: layer.material_params || {},
      calibration: layer.calibration || undefined,
    };
  }

  function mutateLayer(idx, mutator) {
    setWizard(prev => {
      const newLayers = deepClone(prev.layers || []);
      if (!newLayers[idx]) return prev;
      mutator(newLayers[idx], newLayers);
      return { ...prev, layers: newLayers };
    });
  }

  function updateLayers(newLayers) {
    setWizard(prev => ({ ...prev, layers: newLayers }));
  }

  function loadSavedMaterialsFromStorage() {
    try {
      if (typeof window === "undefined" || !window.localStorage) return [];
      const raw = window.localStorage.getItem("geowave.materialLibrary");
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  function persistSavedMaterials(nextMaterials) {
    try {
      if (typeof window === "undefined" || !window.localStorage) return;
      window.localStorage.setItem("geowave.materialLibrary", JSON.stringify(nextMaterials));
    } catch {
      // Ignore storage quota / browser privacy failures.
    }
  }

  function updateWaterTableDepth(rawValue) {
    if (rawValue === "" || rawValue == null) {
      setWizard(prev => ({ ...prev, water_table_depth_m: null }));
      return;
    }
    const parsed = parseFloat(rawValue);
    setWizard(prev => ({
      ...prev,
      water_table_depth_m: Number.isFinite(parsed) && parsed >= 0 ? parsed : null,
    }));
  }

  function inferLastLayerBedrockSeed(sourceLayers = layers) {
    const lastLayer = sourceLayers[sourceLayers.length - 1] || {};
    return {
      name: `${lastLayer.name || "Bottom layer"} halfspace`,
      vs_m_s: Number(lastLayer.vs || lastLayer.vs_m_s || 760),
      unit_weight_kN_m3: Number(lastLayer.unit_weight || lastLayer.unit_weight_kN_m3 || 20),
      damping_ratio: 0.0,
    };
  }

  function updateBedrock(field, value) {
    setWizard(prev => {
      const seed = inferLastLayerBedrockSeed(prev.layers || []);
      const current = prev.bedrock && typeof prev.bedrock === "object"
        ? { ...seed, ...prev.bedrock }
        : seed;
      current[field] = value;
      return { ...prev, bedrock: current };
    });
  }

  function copyLastLayerToBedrock() {
    setWizard(prev => ({ ...prev, bedrock: inferLastLayerBedrockSeed(prev.layers || []) }));
  }

  function resetBedrockToLastLayer() {
    setWizard(prev => ({ ...prev, bedrock: null }));
  }

  function autoSublayer() {
    // DEEPSOIL-style: split each layer into sublayers based on wavelength criterion
    // target_dz = Vs / (points_per_wavelength * f_max), capped at min_dz and max_sublayers
    const newLayers = [];
    for (const l of layers) {
      const vs = l.vs_m_s || l.vs || 150;
      const thick = l.thickness_m || l.thickness || 5;
      const targetDz = Math.max(vs / (autoPPW * autoFmax), autoMinDz);
      const nSub = Math.min(Math.max(Math.ceil(thick / targetDz), 1), autoMaxSub);
      const subThick = thick / nSub;
      for (let j = 0; j < nSub; j++) {
        newLayers.push({
          ...deepClone(l),
          name: (l.name || "Layer") + (nSub > 1 ? `_${j + 1}` : ""),
          thickness: subThick,
          thickness_m: subThick,
        });
      }
    }
    updateLayers(newLayers);
    setSelectedIdx(0);
  }

  function addLayer() {
    const materialType = wizard.default_material_type || "gqh";
    const newLayers = [...layers, defaultLayer(layers.length, materialType)];
    updateLayers(newLayers);
    setSelectedIdx(newLayers.length - 1);
  }

  function removeLayer(idx) {
    if (layers.length <= 1) return;
    const newLayers = layers.filter((_, i) => i !== idx);
    updateLayers(newLayers);
    if (selectedIdx >= newLayers.length) setSelectedIdx(newLayers.length - 1);
  }

  function copyLayer(idx) {
    const clone = deepClone(layers[idx]);
    clone.name = (clone.name || "Layer") + " (copy)";
    const newLayers = [...layers.slice(0, idx + 1), clone, ...layers.slice(idx + 1)];
    updateLayers(newLayers);
    setSelectedIdx(idx + 1);
  }

  function moveLayerUp(idx) {
    if (idx <= 0) return;
    const newLayers = [...layers];
    [newLayers[idx - 1], newLayers[idx]] = [newLayers[idx], newLayers[idx - 1]];
    updateLayers(newLayers);
    setSelectedIdx(idx - 1);
  }

  function moveLayerDown(idx) {
    if (idx >= layers.length - 1) return;
    const newLayers = [...layers];
    [newLayers[idx], newLayers[idx + 1]] = [newLayers[idx + 1], newLayers[idx]];
    updateLayers(newLayers);
    setSelectedIdx(idx + 1);
  }

  function exportLayersCSV() {
    const header = "name,thickness_m,vs_m_s,unit_weight_kN_m3,material,gamma_ref,damping_min,damping_max";
    const rows = layers.map(l => {
      const mp = l.material_params || {};
      return [
        l.name || "Layer", l.thickness || l.thickness_m || 5, l.vs || l.vs_m_s || 150,
        l.unit_weight || l.unit_weight_kN_m3 || 18, l.material || "mkz",
        mp.gamma_ref || 0.035, mp.damping_min || 0.01, mp.damping_max || 0.15,
      ].join(",");
    });
    const csv = [header, ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "soil_profile.csv";
    document.body.appendChild(a); a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function importLayersCSV(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const lines = reader.result.split("\n").filter(l => l.trim());
      if (lines.length < 2) return;
      const headers = lines[0].split(",").map(h => h.trim().toLowerCase());
      const imported = [];
      for (let i = 1; i < lines.length; i++) {
        const vals = lines[i].split(",").map(v => v.trim());
        const get = (key) => vals[headers.indexOf(key)] || "";
        const materialType = (get("material") || wizard.default_material_type || "gqh").toLowerCase();
        const layer = defaultLayer(i - 1, materialType);
        layer.name = get("name") || `Layer ${i}`;
        layer.thickness = parseFloat(get("thickness_m")) || 5;
        layer.vs = parseFloat(get("vs_m_s") || get("vs")) || 150;
        layer.unit_weight = parseFloat(get("unit_weight_kn_m3") || get("unit_weight")) || 18;
        layer.material = materialType;
        layer.material_params = normalizeMaterialParams(
          materialType,
          {
            ...layer.material_params,
            gamma_ref: parseFloat(get("gamma_ref")) || layer.material_params.gamma_ref,
            damping_min: parseFloat(get("damping_min")) || layer.material_params.damping_min,
            damping_max: parseFloat(get("damping_max")) || layer.material_params.damping_max,
            gmax: computeGmax(layer.vs, layer.unit_weight),
          },
          layer.vs,
          layer.unit_weight,
        );
        imported.push(layer);
      }
      if (imported.length > 0) {
        updateLayers(imported);
        setSelectedIdx(0);
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  }

  function updateLayer(idx, field, value) {
    mutateLayer(idx, (layer) => {
      const keys = field.split(".");
      let obj = layer;
      for (let i = 0; i < keys.length - 1; i++) {
        if (!obj[keys[i]]) obj[keys[i]] = {};
        obj = obj[keys[i]];
      }
      obj[keys[keys.length - 1]] = value;

      if (field === "material") {
        const nextMaterial = value || "gqh";
        layer.material = nextMaterial;
        layer.material_params = normalizeMaterialParams(
          nextMaterial,
          layer.material_params || {},
          layer.vs || 150,
          layer.unit_weight || 18,
        );
        if (!supportsCurveFitting(nextMaterial)) {
          layer.reference_curve = null;
          layer.calibration = null;
          layer.fit_stale = false;
        }
        return;
      }

      if (field === "vs" || field === "unit_weight") {
        layer.material_params = normalizeMaterialParams(
          layer.material || "gqh",
          layer.material_params || {},
          layer.vs || 150,
          layer.unit_weight || 18,
        );
      }

      if (field === "reference_curve") {
        layer.reference_curve = value || null;
        layer.fit_stale = Boolean(value);
      }

      if (field.startsWith("calibration.")) {
        layer.fit_stale = true;
      }

      if (
        layer.calibration
        && ["material_params.reload_factor", "material_params.mrdf_p1", "material_params.mrdf_p2", "material_params.mrdf_p3"].includes(field)
      ) {
        if (field === "material_params.reload_factor") {
          layer.calibration.reload_factor = value;
        }
        layer.fit_stale = true;
      }
    });

    if (
      field === "material"
      || field === "reference_curve"
      || field === "vs"
      || field === "unit_weight"
      || field.startsWith("calibration.")
      || field.startsWith("material_params.")
    ) {
      setCalibPreview(null);
    }
  }

  function estimateMeanStress(idx) {
    let stress = 0;
    for (let i = 0; i < layers.length; i++) {
      const layer = layers[i] || {};
      const thickness = layer.thickness || layer.thickness_m || 0;
      const unitWeight = layer.unit_weight || layer.unit_weight_kN_m3 || 18;
      if (i < idx) stress += thickness * unitWeight;
      if (i === idx) {
        stress += 0.5 * thickness * unitWeight;
        break;
      }
    }
    return Math.max(stress, 1);
  }

  function darendeliDefaults(layer, idx) {
    return {
      source: "darendeli",
      plasticity_index: layer?.calibration?.plasticity_index ?? layer?.plasticity_index ?? 0,
      ocr: layer?.calibration?.ocr ?? 1,
      mean_effective_stress_kpa: layer?.calibration?.mean_effective_stress_kpa ?? estimateMeanStress(idx),
      k0: layer?.calibration?.k0 ?? 0.5,
      frequency_hz: layer?.calibration?.frequency_hz ?? 1,
      num_cycles: layer?.calibration?.num_cycles ?? 10,
      strain_min: layer?.calibration?.strain_min ?? 1e-6,
      strain_max: layer?.calibration?.strain_max ?? 1e-1,
      fit_strain_min: layer?.calibration?.fit_strain_min ?? 1e-6,
      fit_strain_max: layer?.calibration?.fit_strain_max ?? 5e-4,
      target_strength_kpa: layer?.calibration?.target_strength_kpa ?? layer?.material_params?.tau_max ?? null,
      target_strength_ratio: layer?.calibration?.target_strength_ratio ?? 0.95,
      target_strength_strain: layer?.calibration?.target_strength_strain ?? 0.1,
      n_points: layer?.calibration?.n_points ?? 60,
      reload_factor: layer?.calibration?.reload_factor ?? (layer?.material === "gqh" ? 1.6 : 2.0),
      fit_procedure: layer?.calibration?.fit_procedure ?? "MR",
      fit_limits: layer?.calibration?.fit_limits ?? {
        mr_min_strain: null,
        mr_max_strain: null,
        damping_min_strain: null,
        damping_max_strain: null,
        min_strength_pct: 95,
        fix_theta3: null,
      },
      auto_refit_on_reference_change: layer?.calibration?.auto_refit_on_reference_change ?? true,
    };
  }

  function enableDarendeliCalibration(idx) {
    updateLayer(idx, "calibration", darendeliDefaults(layers[idx], idx));
    updateLayer(idx, "reference_curve", "darendeli");
    updateLayer(idx, "fit_stale", true);
  }

  const loadRefCurve = useCallback(async (curveType, pi = 0) => {
    if (!curveType || curveType === "darendeli") {
      setRefCurveData(null);
      return;
    }
    try {
      const data = await api.fetchReferenceCurves(curveType, pi);
      setRefCurveData(data);
    } catch (e) { console.error(e); }
  }, []);

  function ensureCalibration(idx, curveType) {
    const layer = layers[idx];
    if (!layer || !supportsCurveFitting(layer.material || "gqh")) return;
    if (layer.calibration) return;
    mutateLayer(idx, (draft) => {
      draft.calibration = darendeliDefaults(draft, idx);
      draft.reference_curve = curveType || draft.reference_curve || "darendeli";
      draft.fit_stale = Boolean(draft.reference_curve);
    });
  }

  function changeReferenceCurve(idx, nextCurve) {
    const curveValue = nextCurve || null;
    const group = curveValue ? referenceCurveGroup(curveValue) : referenceGroup;
    setReferenceGroup(group);
    ensureCalibration(idx, curveValue);
    mutateLayer(idx, (layer) => {
      layer.reference_curve = curveValue;
      layer.fit_stale = Boolean(curveValue);
    });
    setCalibPreview(null);
    if (curveValue) {
      const pi = layers[idx]?.calibration?.plasticity_index ?? layers[idx]?.plasticity_index ?? 0;
      loadRefCurve(curveValue, pi);
    } else {
      setRefCurveData(null);
    }
  }

  const loadCalibPreview = useCallback(async (layer) => {
    try {
      const data = await api.fetchCalibrationPreview({
        layer: toApiLayer(layer, selectedIdx),
        layers: layers.map((l, idx) => toApiLayer(l, idx)),
        layer_index: selectedIdx,
        water_table_depth_m: wizard.water_table_depth_m ?? null,
      });
      setCalibPreview(data);
      return data;
    } catch (e) { console.error("Calibration preview:", e); }
    return null;
  }, [selectedIdx, layers, wizard.water_table_depth_m]);

  const refitAndApply = useCallback(async (layer) => {
    const preview = await loadCalibPreview(layer);
    if (!preview) return;
    const dampingRmse = Number(preview.damping_rmse);
    if (Number.isFinite(dampingRmse) && dampingRmse > 0.40) {
      setCalibPreview(preview);
      return;
    }
    const fitted = preview.calibrated_material_params || {};
    if (!Object.keys(fitted).length) return;
    const merged = {
      ...(layers[selectedIdx]?.material_params || {}),
      ...fitted,
    };
    updateLayer(selectedIdx, "material_params", merged);
    updateLayer(selectedIdx, "fit_stale", false);
    setCalibPreview({ ...preview, material_params: merged, fit_stale: false });
  }, [layers, loadCalibPreview, selectedIdx]);

  useEffect(() => {
    setSavedMaterials(loadSavedMaterialsFromStorage());
  }, []);

  useEffect(() => {
    const current = layers[selectedIdx];
    if (!current) return;
    setReferenceGroup(referenceCurveGroup(current.reference_curve));
  }, [layers, selectedIdx]);

  useEffect(() => {
    const current = layers[selectedIdx];
    setMaterialLibraryName(current?.name || "");
  }, [layers, selectedIdx]);

  useEffect(() => {
    const current = layers[selectedIdx];
    if (!current?.reference_curve || current.reference_curve === "darendeli") {
      setRefCurveData(null);
      return;
    }
    const pi = current.calibration?.plasticity_index ?? current.plasticity_index ?? 0;
    loadRefCurve(current.reference_curve, pi);
  }, [layers, selectedIdx, loadRefCurve]);

  useEffect(() => {
    let active = true;
    const body = {
      water_table_depth_m: wizard.water_table_depth_m ?? null,
      layers: layers.map((layer, idx) => toApiLayer(layer, idx)),
    };
    api.fetchProfileDiagnostics(body)
      .then((resp) => {
        if (active) setProfileDiagnostics(resp?.layers || []);
      })
      .catch(() => {
        if (active) setProfileDiagnostics([]);
      });
    return () => {
      active = false;
    };
  }, [layers, wizard.water_table_depth_m]);

  const runSET = useCallback(async (layer, strainAmp) => {
    try {
      const mp = layer.material_params || {};
      const params = {
        material: layer.material || "mkz",
        strain_amplitude: strainAmp,
        gmax: mp.gmax || 100000,
        gamma_ref: mp.gamma_ref || 0.001,
        damping_min: mp.damping_min || 0.01,
        damping_max: mp.damping_max || 0.15,
        reload_factor: mp.reload_factor || 2.0,
        g_reduction_min: mp.g_reduction_min || 0.0,
        a1: mp.a1 || 1.0, a2: mp.a2 || 0.0, m: mp.m || 1.0,
      };
      if (mp.tau_max != null) params.tau_max = mp.tau_max;
      if (mp.theta1 != null) params.theta1 = mp.theta1;
      if (mp.theta2 != null) params.theta2 = mp.theta2;
      if (mp.theta3 != null) params.theta3 = mp.theta3;
      if (mp.theta4 != null) params.theta4 = mp.theta4;
      if (mp.theta5 != null) params.theta5 = mp.theta5;
      const data = await api.runSingleElementTest(params);
      setSetResult(data);
    } catch (e) { console.error(e); }
  }, []);

  function saveSelectedMaterialToLibrary() {
    const selLayer = layers[selectedIdx];
    if (!selLayer) return;
    const name = (materialLibraryName || selLayer.name || `Layer ${selectedIdx + 1}`).trim();
    if (!name) return;
    const record = {
      id: `${name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${Date.now()}`,
      name,
      material: selLayer.material || "mkz",
      reference_curve: selLayer.reference_curve || null,
      material_params: deepClone(selLayer.material_params || {}),
      calibration: deepClone(selLayer.calibration || null),
    };
    const next = [
      record,
      ...savedMaterials.filter(item => item.name !== name),
    ];
    setSavedMaterials(next);
    persistSavedMaterials(next);
    setMaterialLibraryName(name);
  }

  function applySavedMaterialToLayer(record) {
    if (!record || !layers[selectedIdx]) return;
    mutateLayer(selectedIdx, (layer) => {
      const materialType = record.material || "mkz";
      layer.material = materialType;
      layer.reference_curve = record.reference_curve || null;
      layer.material_params = normalizeMaterialParams(
        materialType,
        deepClone(record.material_params || {}),
        layer.vs || 150,
        layer.unit_weight || 18,
      );
      layer.calibration = deepClone(record.calibration || null);
      layer.fit_stale = false;
    });
    setCalibPreview(null);
  }

  function deleteSavedMaterial(recordId) {
    const next = savedMaterials.filter(item => item.id !== recordId);
    setSavedMaterials(next);
    persistSavedMaterials(next);
  }

  function runSelectedSetPreset() {
    const preset = SET_PRESETS.find(item => item.id === setPreset) || SET_PRESETS[2];
    if (sel) runSET(sel, preset.strain);
  }

  const sel = layers[selectedIdx] || null;
  const diagSel = profileDiagnostics[selectedIdx] || null;
  const isBottomLayer = selectedIdx === layers.length - 1;
  const motionInputType = wizard.motion_input_type || "within";
  const boundaryCondition = wizard.boundary_condition || "rigid";
  const boundaryIsElastic = boundaryCondition === "elastic_halfspace";
  const explicitBedrock = wizard.bedrock || null;
  const implicitBedrock = inferLastLayerBedrockSeed(layers);
  const effectiveBedrock = explicitBedrock || implicitBedrock;
  const bedrockSourceLabel = explicitBedrock ? "Explicit bedrock" : "Using last layer";
  const lastLayer = layers[layers.length - 1] || null;
  const lastLayerImpedance = lastLayer
    ? ((Number(lastLayer.unit_weight || lastLayer.unit_weight_kN_m3 || 0) / 9.81) * Number(lastLayer.vs || lastLayer.vs_m_s || 0))
    : null;
  const bedrockImpedance = effectiveBedrock
    ? ((Number(effectiveBedrock.unit_weight_kN_m3 || 0) / 9.81) * Number(effectiveBedrock.vs_m_s || 0))
    : null;
  const bedrockImpedanceRatio = (
    Number.isFinite(lastLayerImpedance)
    && Number.isFinite(bedrockImpedance)
    && lastLayerImpedance > 0
  ) ? (bedrockImpedance / lastLayerImpedance) : null;
  const isCalibratable = supportsCurveFitting(sel?.material || "");
  const supportsReduction = supportsReductionFormulation(sel?.material || "");
  const selectedMaterialDef = MATERIAL_TYPES.find(material => material.value === (sel?.material || "mkz")) || MATERIAL_TYPES[0];
  const referenceMeta = REFERENCE_CURVES.find(curve => curve.value === sel?.reference_curve) || null;
  const groupedReferenceCurves = referenceCurvesForGroup(referenceGroup);
  const referenceNeedsPI = referenceMeta?.needsPI === true;
  const previewDampingGuard = calibPreview?.damping_rmse != null && calibPreview.damping_rmse > 0.40;
  const canApplyFit = Boolean(sel?.calibration) && !previewDampingGuard;
  const fitLimitsOpen = previewDampingGuard;
  const fitProcedureLabel =
    sel?.calibration?.fit_procedure === "MRD"
      ? "MRD"
      : sel?.calibration?.fit_procedure === "DC"
        ? "DC"
        : "MR";
  const fitStatusTone = sel?.fit_stale ? " metric-card-warn" : " metric-card-good";
  const modulusTone = calibPreview?.modulus_rmse == null
    ? ""
    : calibPreview.modulus_rmse > 0.15
      ? " metric-card-warn"
      : " metric-card-good";
  const dampingTone = calibPreview?.damping_rmse == null
    ? ""
    : calibPreview.damping_rmse > 0.40
      ? " metric-card-danger"
      : calibPreview.damping_rmse > 0.08
        ? " metric-card-warn"
        : " metric-card-good";
  const strengthTarget = Math.max(
    (sel?.calibration?.target_strength_ratio ?? 0.95),
    ((sel?.calibration?.fit_limits?.min_strength_pct ?? 95) / 100),
  );
  const strengthTone = calibPreview?.strength_ratio_achieved == null
    ? ""
    : calibPreview.strength_ratio_achieved < strengthTarget
      ? " metric-card-warn"
      : " metric-card-good";
  const setPresetMeta = SET_PRESETS.find(item => item.id === setPreset) || SET_PRESETS[2];
  const advancedColumns = [
    { key: "name", label: "Layer Name", editable: true, width: 132, kind: "text" },
    { key: "thickness", label: "Thickness (m)", editable: true, width: 94, kind: "numeric" },
    { key: "unit_weight", label: "Unit Weight (kN/m³)", editable: true, width: 116, kind: "numeric" },
    { key: "vs", label: "Vs (m/s)", editable: true, width: 86, kind: "numeric" },
    { key: "material", label: "Soil Model", editable: true, type: "select", width: 98, kind: "select" },
    { key: "reference_curve", label: "Reference Curve", editable: true, type: "reference", width: 190, kind: "reference" },
    { key: "diag.small_strain_damping_ratio", label: "Dmin (%)", editable: false, format: (v) => fmt((v || 0) * 100, 3), width: 84, kind: "numeric" },
    { key: "diag.implied_strength_kpa", label: "Imp. Strength (kPa)", editable: false, format: (v) => fmt(v, 2), width: 108, kind: "numeric" },
    { key: "diag.normalized_implied_strength", label: "Norm. Strength", editable: false, format: (v) => fmt(v, 3), width: 104, kind: "numeric" },
    { key: "material_params.gamma_ref", label: "Gamma Ref", editable: true, width: 96, kind: "numeric" },
    { key: "material_params.tau_max", label: "Tau Max", editable: true, width: 88, kind: "numeric" },
    { key: "material_params.theta1", label: "Theta1", editable: true, width: 92, kind: "numeric" },
    { key: "material_params.theta2", label: "Theta2", editable: true, width: 92, kind: "numeric" },
    { key: "material_params.theta3", label: "Theta3", editable: true, width: 92, kind: "numeric" },
    { key: "material_params.theta4", label: "Theta4", editable: true, width: 92, kind: "numeric" },
    { key: "material_params.theta5", label: "Theta5", editable: true, width: 92, kind: "numeric" },
    { key: "material_params.reload_factor", label: "Reload", editable: true, width: 78, kind: "numeric" },
    { key: "material_params.mrdf_p1", label: "P1", editable: true, width: 72, kind: "numeric" },
    { key: "material_params.mrdf_p2", label: "P2", editable: true, width: 72, kind: "numeric" },
    { key: "material_params.mrdf_p3", label: "P3", editable: true, width: 72, kind: "numeric" },
  ];

  return html`
    <div className="profile-editor-full">
      <div className="row" style=${{ gap: "0.6rem", alignItems: "end", marginBottom: "0.4rem" }}>
        <div className="field" style=${{ maxWidth: "220px" }}>
          <label htmlFor="profile-water-table-depth">Water Table Depth (m)</label>
          <input id="profile-water-table-depth" type="number" step="0.1" min="0"
            value=${wizard.water_table_depth_m ?? ""}
            placeholder="Dry profile"
            onInput=${e => updateWaterTableDepth(e.target.value)} />
        </div>
        <span className="muted" style=${{ fontSize: "0.72rem" }}>
          Leave empty for dry profile (no pore pressure correction in Step 2 preview).
        </span>
      </div>
      <!-- Soil Profile Plot (DEEPSOIL-style) -->
      <${SoilProfilePlot} layers=${layers} diagnostics=${profileDiagnostics} />

      <div className="profile-editor">
      <!-- Layer Table -->
      <div className="layer-table-container">
        <div className="layer-table-header">
          <h4>Soil Layers (${layers.length})</h4>
          <div style=${{ display: "flex", gap: "0.35rem" }}>
            <button type="button" className="btn btn-sm" onClick=${addLayer}>+ Add</button>
            <button type="button" className="btn btn-sm" onClick=${exportLayersCSV} title="Export layers to CSV">Export</button>
            <label className="btn btn-sm" style=${{ cursor: "pointer", margin: 0 }} title="Import layers from CSV">
              Import
              <input type="file" accept=".csv,.txt" aria-label="Import layers from CSV" onChange=${importLayersCSV}
                style=${{ display: "none" }} />
            </label>
          </div>
        </div>
        <details className="auto-profile-details">
          <summary>Auto Sublayering</summary>
          <div className="row" style=${{ gap: "0.4rem", marginTop: "0.4rem", fontSize: "0.75rem" }}>
            <div className="field">
              <label htmlFor="profile-auto-fmax">f_max (Hz)</label>
              <input id="profile-auto-fmax" type="number" min="1" max="100" value=${autoFmax}
                onInput=${e => setAutoFmax(parseFloat(e.target.value) || 25)} />
            </div>
            <div className="field">
              <label htmlFor="profile-auto-ppw">Pts/λ</label>
              <input id="profile-auto-ppw" type="number" min="3" max="30" value=${autoPPW}
                onInput=${e => setAutoPPW(parseInt(e.target.value) || 10)} />
            </div>
            <div className="field">
              <label htmlFor="profile-auto-min-dz">Min dz (m)</label>
              <input id="profile-auto-min-dz" type="number" step="0.1" min="0.1" max="5" value=${autoMinDz}
                onInput=${e => setAutoMinDz(parseFloat(e.target.value) || 0.5)} />
            </div>
            <div className="field">
              <label htmlFor="profile-auto-max-sub">Max sub</label>
              <input id="profile-auto-max-sub" type="number" min="1" max="50" value=${autoMaxSub}
                onInput=${e => setAutoMaxSub(parseInt(e.target.value) || 20)} />
            </div>
          </div>
          <button type="button" className="btn btn-sm btn-accent" style=${{ marginTop: "0.4rem" }}
            onClick=${autoSublayer}>Apply Auto Sublayering</button>
        </details>
        <table className="tbl layer-table">
          <thead>
            <tr>
              <th>#</th><th>Thickness (m)</th><th>Vs (m/s)</th>
              <th>Unit Wt</th><th>Material</th><th></th>
            </tr>
          </thead>
          <tbody>
            ${layers.map((l, i) => html`
              <tr key=${i} className=${i === selectedIdx ? "selected" : ""}
                tabIndex="0"
                aria-selected=${i === selectedIdx ? "true" : "false"}
                onKeyDown=${e => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setSelectedIdx(i);
                  }
                }}
                onClick=${() => setSelectedIdx(i)}>
                <td>
                  <div className="layer-index-cell">
                    <span>${i + 1}</span>
                    ${l.fit_stale ? html`<span className="fit-state-badge">Refit</span>` : null}
                  </div>
                </td>
                <td><input type="number" step="0.5" aria-label=${`Layer ${i + 1} thickness in meters`} value=${l.thickness}
                  onClick=${e => e.stopPropagation()}
                  onInput=${e => updateLayer(i, "thickness", parseFloat(e.target.value) || 1)} /></td>
                <td><input type="number" step="10" aria-label=${`Layer ${i + 1} shear-wave velocity`} value=${l.vs}
                  onClick=${e => e.stopPropagation()}
                  onInput=${e => updateLayer(i, "vs", parseFloat(e.target.value) || 100)} /></td>
                <td><input type="number" step="0.5" aria-label=${`Layer ${i + 1} unit weight`} value=${l.unit_weight}
                  onClick=${e => e.stopPropagation()}
                  onInput=${e => updateLayer(i, "unit_weight", parseFloat(e.target.value) || 16)} /></td>
                <td>
                  <select aria-label=${`Layer ${i + 1} material`} value=${l.material || "mkz"}
                    onClick=${e => e.stopPropagation()}
                    onChange=${e => updateLayer(i, "material", e.target.value)}>
                    ${MATERIAL_TYPES.map(m => html`<option key=${m.value} value=${m.value}>${m.value.toUpperCase()}</option>`)}
                  </select>
                </td>
                <td className="layer-actions">
                  <button type="button" className="btn-icon" aria-label=${`Move layer ${i + 1} up`} title="Move up" onClick=${e => { e.stopPropagation(); moveLayerUp(i); }} disabled=${i === 0}>↑</button>
                  <button type="button" className="btn-icon" aria-label=${`Move layer ${i + 1} down`} title="Move down" onClick=${e => { e.stopPropagation(); moveLayerDown(i); }} disabled=${i === layers.length - 1}>↓</button>
                  <button type="button" className="btn-icon" aria-label=${`Duplicate layer ${i + 1}`} title="Duplicate" onClick=${e => { e.stopPropagation(); copyLayer(i); }}>⧉</button>
                  <button type="button" className="btn-icon" aria-label=${`Remove layer ${i + 1}`} title="Remove" onClick=${e => { e.stopPropagation(); removeLayer(i); }}>✕</button>
                </td>
              </tr>
            `)}
          </tbody>
        </table>
      </div>

      <!-- Layer Properties Panel -->
      ${sel ? html`
        <div className="layer-properties">
          <div style=${{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
            <div style=${{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <h4 style=${{ margin: 0 }}>Layer ${selectedIdx + 1} Properties</h4>
              ${sel.fit_stale ? html`<span className="fit-state-badge fit-state-badge-active">Needs Refit</span>` : null}
            </div>
            <div className="tab-row" style=${{ margin: 0 }}>
              <button
                type="button"
                className=${"tab-btn" + (editorTab === "layer_properties" ? " active" : "")}
                onClick=${() => setEditorTab("layer_properties")}>
                Layer Properties
              </button>
              <button
                type="button"
                className=${"tab-btn" + (editorTab === "advanced_table" ? " active" : "")}
                onClick=${() => setEditorTab("advanced_table")}>
                Advanced Table View
              </button>
            </div>
          </div>

          ${editorTab === "advanced_table" ? html`
            <div>
              <div className="metric-row" style=${{ marginBottom: "0.5rem" }}>
                <div className="metric-card"><span>Selected Layer</span><b>${sel.name || `Layer ${selectedIdx + 1}`}</b></div>
                <div className="metric-card"><span>Soil Model</span><b>${(sel.material || "mkz").toUpperCase()}</b></div>
                ${diagSel ? html`<div className="metric-card"><span>Implied Strength</span><b>${fmt(diagSel.implied_strength_kpa, 2)} kPa</b></div>` : null}
                ${diagSel ? html`<div className="metric-card"><span>Dmin</span><b>${fmt((diagSel.small_strain_damping_ratio || 0) * 100, 3)}%</b></div>` : null}
              </div>
              <div className="advanced-table-shell">
                <table className="tbl advanced-table" style=${{ minWidth: "1900px" }}>
                  <colgroup>
                    <col style=${{ width: "44px" }} />
                    ${advancedColumns.map(col => html`<col key=${`col-${col.key}`} style=${{ width: `${col.width || 90}px` }} />`)}
                  </colgroup>
                  <thead>
                    <tr>
                      <th className="advanced-table-sticky advanced-table-index">#</th>
                      ${advancedColumns.map(col => html`<th key=${col.key} className=${`advanced-table-head advanced-table-head-${col.kind || "numeric"}`}>${col.label}</th>`)}
                    </tr>
                  </thead>
                  <tbody>
                    ${layers.map((layer, layerIdx) => {
                      const diag = profileDiagnostics[layerIdx] || {};
                      return html`
                        <tr key=${`advanced-row-${layerIdx}`} className=${layerIdx === selectedIdx ? "selected" : ""} onClick=${() => setSelectedIdx(layerIdx)}>
                          <td className="advanced-table-sticky advanced-table-index">${layerIdx + 1}</td>
                          ${advancedColumns.map(col => {
                            const parts = col.key.split(".");
                            let rawValue;
                            if (parts[0] === "diag") {
                              rawValue = diag[parts.slice(1).join(".")] ?? diag[parts[1]];
                            } else {
                              rawValue = parts.reduce((acc, key) => (acc == null ? undefined : acc[key]), layer);
                            }
                            const cellClass = `advanced-table-cell advanced-table-cell-${col.kind || "numeric"}`;
                            if (!col.editable) {
                              return html`<td key=${`${layerIdx}-${col.key}`} className=${cellClass} title=${col.format ? col.format(rawValue) : fmt(rawValue, 3)}>${col.format ? col.format(rawValue) : fmt(rawValue, 3)}</td>`;
                            }
                            if (col.type === "select") {
                              return html`
                                <td key=${`${layerIdx}-${col.key}`} className=${cellClass}>
                                  <select value=${rawValue || "mkz"} onClick=${e => e.stopPropagation()} onChange=${e => updateLayer(layerIdx, col.key, e.target.value)}>
                                    ${MATERIAL_TYPES.map(m => html`<option key=${m.value} value=${m.value}>${m.value.toUpperCase()}</option>`)}
                                  </select>
                                </td>
                              `;
                            }
                            if (col.type === "reference") {
                              return html`
                                <td key=${`${layerIdx}-${col.key}`} className=${cellClass}>
                                  <select value=${rawValue || ""} onClick=${e => e.stopPropagation()} onChange=${e => {
                                    updateLayer(layerIdx, "reference_curve", e.target.value || null);
                                    updateLayer(layerIdx, "fit_stale", true);
                                  }}>
                                    <option value="">—</option>
                                    ${REFERENCE_CURVES.map(rc => html`<option key=${rc.value} value=${rc.value}>${rc.label}</option>`)}
                                  </select>
                                </td>
                              `;
                            }
                            return html`
                              <td key=${`${layerIdx}-${col.key}`} className=${cellClass}>
                                <input
                                  type=${col.key === "name" ? "text" : "number"}
                                  step=${col.key === "name" ? undefined : "any"}
                                  value=${rawValue ?? ""}
                                  onClick=${e => e.stopPropagation()}
                                  onInput=${e => {
                                    if (col.key === "name") {
                                      updateLayer(layerIdx, col.key, e.target.value);
                                      return;
                                    }
                                    const nextValue = parseFloat(e.target.value);
                                    updateLayer(layerIdx, col.key, Number.isFinite(nextValue) ? nextValue : null);
                                  }}
                                />
                              </td>
                            `;
                          })}
                        </tr>
                      `;
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          ` : html`

            <div className="profile-stage profile-stage-hero">
              <div className="section-head">
                <h5>Basic Soil Properties</h5>
                <p>Base geometry, stiffness and the currently active constitutive model for this layer.</p>
              </div>
              <div className="profile-stage-grid profile-stage-grid-3">
                <div className="field">
                  <label htmlFor="profile-layer-name">Layer Name</label>
                  <input id="profile-layer-name" type="text" value=${sel.name || ""} onInput=${e => updateLayer(selectedIdx, "name", e.target.value)} />
                </div>
                <div className="field">
                  <label htmlFor="profile-layer-material">Soil Model</label>
                  <select id="profile-layer-material" value=${sel.material || "mkz"} onChange=${e => updateLayer(selectedIdx, "material", e.target.value)}>
                    ${MATERIAL_TYPES.map(material => html`<option key=${material.value} value=${material.value}>${material.label}</option>`)}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="profile-layer-thickness">Thickness (m)</label>
                  <input id="profile-layer-thickness" type="number" step="0.1" min="0.1" value=${sel.thickness ?? ""} onInput=${e => updateLayer(selectedIdx, "thickness", parseFloat(e.target.value) || 0.1)} />
                </div>
                <div className="field">
                  <label htmlFor="profile-layer-unit-weight">Unit Weight (kN/m³)</label>
                  <input id="profile-layer-unit-weight" type="number" step="0.1" min="1" value=${sel.unit_weight ?? ""} onInput=${e => updateLayer(selectedIdx, "unit_weight", parseFloat(e.target.value) || 1)} />
                </div>
                <div className="field">
                  <label htmlFor="profile-layer-vs">Shear Wave Velocity (m/s)</label>
                  <input id="profile-layer-vs" type="number" step="1" min="1" value=${sel.vs ?? ""} onInput=${e => updateLayer(selectedIdx, "vs", parseFloat(e.target.value) || 1)} />
                </div>
                <div className="field">
                  <label htmlFor="profile-layer-default-model">Model Family</label>
                  <input id="profile-layer-default-model" type="text" value=${selectedMaterialDef.label} disabled />
                </div>
              </div>
              <div className="metric-row compact">
                <div className="metric-card compact"><span>Gmax</span><b>${fmt(computeGmax(sel.vs || 0, sel.unit_weight || 0), 0)}</b></div>
                <div className="metric-card compact"><span>Eff. Stress Mid (kPa)</span><b>${fmt(diagSel?.sigma_v_eff_mid_kpa ?? estimateMeanStress(selectedIdx), 2)}</b></div>
                <div className="metric-card compact"><span>Small-Strain Damping</span><b>${fmt(((diagSel?.small_strain_damping_ratio ?? sel.material_params?.damping_min ?? 0) || 0) * 100, 3)}%</b></div>
                <div className="metric-card compact"><span>Implied Strength</span><b>${fmt(diagSel?.implied_strength_kpa, 2)} kPa</b></div>
                <div className="metric-card compact"><span>Friction Angle</span><b>${fmt(diagSel?.implied_friction_angle_deg, 2)}°</b></div>
              </div>
            </div>

            ${isBottomLayer ? html`
              <section className="profile-stage">
                <div className="section-head">
                  <h5>Bedrock / Halfspace</h5>
                  <p>Base condition and halfspace impedance used below the last soil layer.</p>
                </div>
                <div className="profile-stage-grid profile-stage-grid-3">
                  <div className="field profile-stage-span-2">
                    <label>Forward Analysis Base</label>
                    <div className="tab-row compact bedrock-toggle-row">
                      <button
                        type="button"
                        className=${"tab-btn" + (boundaryIsElastic ? " active" : "")}
                        onClick=${() => setWizard(prev => ({ ...prev, boundary_condition: "elastic_halfspace" }))}>
                        Elastic Halfspace
                      </button>
                      <button
                        type="button"
                        className=${"tab-btn" + (!boundaryIsElastic ? " active" : "")}
                        onClick=${() => setWizard(prev => ({ ...prev, boundary_condition: "rigid" }))}>
                        Rigid Base
                      </button>
                    </div>
                  </div>
                  <div className="saved-material-shell bedrock-info-shell">
                    <div className="saved-material-meta">Motion / boundary guidance</div>
                    <p className="muted">
                      ${motionInputType === "outcrop"
                        ? "Outcrop motion is usually paired with Elastic Halfspace."
                        : "Within motion is usually paired with Rigid Base."}
                    </p>
                  </div>
                  ${boundaryIsElastic ? html`
                    <div className="field">
                      <label htmlFor="profile-bedrock-name">Bedrock Name</label>
                      <input
                        id="profile-bedrock-name"
                        type="text"
                        value=${effectiveBedrock?.name || "Bedrock"}
                        onInput=${e => updateBedrock("name", e.target.value || "Bedrock")}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="profile-bedrock-vs">Bedrock Vs (m/s)</label>
                      <input
                        id="profile-bedrock-vs"
                        type="number"
                        step="1"
                        min="1"
                        value=${effectiveBedrock?.vs_m_s ?? ""}
                        onInput=${e => {
                          const nextValue = parseFloat(e.target.value);
                          updateBedrock("vs_m_s", Number.isFinite(nextValue) && nextValue > 0 ? nextValue : implicitBedrock.vs_m_s);
                        }}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="profile-bedrock-unit-weight">Bedrock Unit Weight (kN/m³)</label>
                      <input
                        id="profile-bedrock-unit-weight"
                        type="number"
                        step="0.1"
                        min="1"
                        value=${effectiveBedrock?.unit_weight_kN_m3 ?? ""}
                        onInput=${e => {
                          const nextValue = parseFloat(e.target.value);
                          updateBedrock("unit_weight_kN_m3", Number.isFinite(nextValue) && nextValue > 0 ? nextValue : implicitBedrock.unit_weight_kN_m3);
                        }}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="profile-bedrock-damping">Bedrock Damping Ratio (0.02 = 2%)</label>
                      <input
                        id="profile-bedrock-damping"
                        type="number"
                        step="0.001"
                        min="0"
                        max="0.5"
                        value=${effectiveBedrock?.damping_ratio ?? 0}
                        onInput=${e => {
                          const nextValue = parseFloat(e.target.value);
                          updateBedrock(
                            "damping_ratio",
                            Number.isFinite(nextValue) && nextValue >= 0
                              ? Math.min(nextValue, 0.5)
                              : 0.0,
                          );
                        }}
                      />
                    </div>
                  ` : html`
                    <div className="stage-empty profile-stage-span-4">
                      <p className="muted">Rigid Base uses the recorded motion directly at the base. Separate halfspace impedance properties are ignored in this mode.</p>
                    </div>
                  `}
                </div>
                <div className="metric-row compact">
                  <div className="metric-card compact"><span>Boundary</span><b>${boundaryIsElastic ? "Elastic Halfspace" : "Rigid Base"}</b></div>
                  <div className="metric-card compact"><span>Motion Input</span><b>${motionInputType === "outcrop" ? "Outcrop" : "Within"}</b></div>
                  <div className="metric-card compact"><span>Bedrock Source</span><b>${bedrockSourceLabel}</b></div>
                  <div className="metric-card compact"><span>Bedrock Vs</span><b>${fmt(effectiveBedrock?.vs_m_s, 1)} m/s</b></div>
                  ${boundaryIsElastic ? html`<div className="metric-card compact"><span>Bedrock Damping</span><b>${fmt((Number(effectiveBedrock?.damping_ratio || 0) * 100), 2)}%</b></div>` : null}
                  ${bedrockImpedanceRatio != null ? html`<div className="metric-card compact"><span>Impedance Ratio</span><b>${fmt(bedrockImpedanceRatio, 3)}</b></div>` : null}
                </div>
                ${boundaryIsElastic ? html`
                  <div className="calibration-actions">
                    <button type="button" className="btn btn-sm" onClick=${copyLastLayerToBedrock}>Copy Last Layer To Bedrock</button>
                    <button type="button" className="btn btn-sm" disabled=${!explicitBedrock} onClick=${resetBedrockToLastLayer}>Use Last Layer Values</button>
                  </div>
                  <p className="muted section-footnote">DeepSoil v7.1 notes that bedrock damping ratio has no effect in time-domain analyses. GeoWave stores the value for parity/reference, but current time-domain solvers use halfspace impedance from Vs and unit weight only.</p>
                ` : null}
              </section>
            ` : null}

            <section className="profile-stage">
              <div className="section-head">
                <h5>Reference Curve</h5>
                <p>Select the target family first, then pick the curve used as the fitting target.</p>
              </div>
              <div className="tab-row compact">
                ${["sand", "clay"].map(group => html`
                  <button
                    key=${group}
                    type="button"
                    className=${"tab-btn" + (referenceGroup === group ? " active" : "")}
                    onClick=${() => {
                      setReferenceGroup(group);
                      const firstCurve = referenceCurvesForGroup(group)[0]?.value || "";
                      if (!sel.reference_curve || referenceCurveGroup(sel.reference_curve) !== group) {
                        changeReferenceCurve(selectedIdx, firstCurve);
                      }
                    }}>
                    ${group === "sand" ? "Sand" : "Clay"}
                  </button>
                `)}
              </div>
              <div className="profile-stage-grid profile-stage-grid-3">
                <div className="field profile-stage-span-2">
                  <label htmlFor="profile-reference-curve">Reference Curve</label>
                  <select id="profile-reference-curve" value=${sel.reference_curve || ""} onChange=${e => changeReferenceCurve(selectedIdx, e.target.value)}>
                    <option value="">Select curve</option>
                    ${groupedReferenceCurves.map(curve => html`<option key=${curve.value} value=${curve.value}>${curve.label}</option>`)}
                  </select>
                </div>
                ${referenceMeta?.needsPI ? html`
                  <div className="field">
                    <label htmlFor="profile-plasticity-index">Plasticity Index (PI)</label>
                    <input
                      id="profile-plasticity-index"
                      type="number"
                      min="0"
                      max="200"
                      value=${sel.calibration?.plasticity_index ?? (sel.plasticity_index || 0)}
                      onInput=${e => {
                        const nextPi = parseInt(e.target.value, 10) || 0;
                        updateLayer(selectedIdx, "plasticity_index", nextPi);
                        if (sel.calibration) updateLayer(selectedIdx, "calibration.plasticity_index", nextPi);
                        if (sel.reference_curve) loadRefCurve(sel.reference_curve, nextPi);
                      }}
                    />
                  </div>
                ` : null}
              </div>
              <p className="muted section-footnote">
                ${referenceMeta
                  ? referenceMeta.value === "darendeli"
                    ? "Darendeli is used as a generated clay reference curve and fitting target."
                    : `${referenceMeta.label} is loaded as the external target curve for modulus and damping parity.`
                  : "Choose a reference curve before running preview or refit."}
              </p>
            </section>

            <section className="profile-stage">
              <div className="section-head">
                <h5>Curve Fitting</h5>
                <p>Fit the selected reference curve, inspect parity, then apply calibrated parameters to the active layer.</p>
              </div>
              ${isCalibratable ? html`
                ${sel.calibration ? html`
                  <div className="fit-status-strip metric-row compact">
                    <div className=${"metric-card compact" + fitStatusTone}><span>Status</span><b>${sel.fit_stale ? "Needs Refit" : "Ready"}</b></div>
                    <div className="metric-card compact"><span>Procedure</span><b>${fitProcedureLabel}</b></div>
                    <div className="metric-card compact"><span>Curve Points</span><b>${sel.calibration.n_points ?? 60}</b></div>
                    <div className="metric-card compact"><span>Auto Refit</span><b>${sel.calibration.auto_refit_on_reference_change !== false ? "On" : "Off"}</b></div>
                  </div>

                  <div className="fit-workbench">
                    <div className="fit-pane">
                      <div className="fit-pane-head">
                        <h6>Reference Context</h6>
                        <p>Stress state and source curve definition for the active layer.</p>
                      </div>
                      <div className="profile-stage-grid profile-stage-grid-4 fit-compact-grid">
                        ${referenceNeedsPI ? html`
                          <div className="field">
                            <label htmlFor="profile-calibration-pi">PI</label>
                            <input id="profile-calibration-pi" type="number" min="0" max="200" value=${sel.calibration.plasticity_index ?? 0} onInput=${e => { updateLayer(selectedIdx, "calibration.plasticity_index", parseFloat(e.target.value) || 0); updateLayer(selectedIdx, "fit_stale", true); }} />
                          </div>
                        ` : null}
                        <div className="field">
                          <label htmlFor="profile-calibration-ocr">OCR</label>
                          <input id="profile-calibration-ocr" type="number" min="0.1" step="0.1" value=${sel.calibration.ocr ?? 1} onInput=${e => { updateLayer(selectedIdx, "calibration.ocr", parseFloat(e.target.value) || 1); updateLayer(selectedIdx, "fit_stale", true); }} />
                        </div>
                        <div className="field">
                          <label htmlFor="profile-calibration-k0">K0</label>
                          <input id="profile-calibration-k0" type="number" min="0" step="0.05" value=${sel.calibration.k0 ?? 0.5} onInput=${e => { updateLayer(selectedIdx, "calibration.k0", parseFloat(e.target.value) || 0); updateLayer(selectedIdx, "fit_stale", true); }} />
                        </div>
                        <div className="field">
                          <label htmlFor="profile-calibration-stress">Mean Eff. Stress (kPa)</label>
                          <input id="profile-calibration-stress" type="number" min="1" step="1" value=${sel.calibration.mean_effective_stress_kpa ?? estimateMeanStress(selectedIdx)} onInput=${e => { const nextStress = parseFloat(e.target.value); updateLayer(selectedIdx, "calibration.mean_effective_stress_kpa", Number.isFinite(nextStress) && nextStress > 0 ? nextStress : null); updateLayer(selectedIdx, "fit_stale", true); }} />
                        </div>
                        <div className="field">
                          <label htmlFor="profile-calibration-frequency">Frequency (Hz)</label>
                          <input id="profile-calibration-frequency" type="number" min="0.1" step="0.1" value=${sel.calibration.frequency_hz ?? 1} onInput=${e => { updateLayer(selectedIdx, "calibration.frequency_hz", parseFloat(e.target.value) || 1); updateLayer(selectedIdx, "fit_stale", true); }} />
                        </div>
                        <div className="field">
                          <label htmlFor="profile-calibration-cycles">Cycles</label>
                          <input id="profile-calibration-cycles" type="number" min="1" step="1" value=${sel.calibration.num_cycles ?? 10} onInput=${e => { updateLayer(selectedIdx, "calibration.num_cycles", parseFloat(e.target.value) || 10); updateLayer(selectedIdx, "fit_stale", true); }} />
                        </div>
                        <div className="field">
                          <label htmlFor="profile-calibration-strain-min">Curve Strain Min</label>
                          <input id="profile-calibration-strain-min" type="number" step="any" min="1e-8" value=${sel.calibration.strain_min ?? 1e-6} onInput=${e => { updateLayer(selectedIdx, "calibration.strain_min", parseFloat(e.target.value) || 1e-6); updateLayer(selectedIdx, "fit_stale", true); }} />
                        </div>
                        <div className="field">
                          <label htmlFor="profile-calibration-strain-max">Curve Strain Max</label>
                          <input id="profile-calibration-strain-max" type="number" step="any" min="1e-6" value=${sel.calibration.strain_max ?? 1e-1} onInput=${e => { updateLayer(selectedIdx, "calibration.strain_max", parseFloat(e.target.value) || 1e-1); updateLayer(selectedIdx, "fit_stale", true); }} />
                        </div>
                        <div className="field">
                          <label htmlFor="profile-calibration-npoints">Curve Points</label>
                          <input id="profile-calibration-npoints" type="number" min="12" max="400" step="1" value=${sel.calibration.n_points ?? 60} onInput=${e => { updateLayer(selectedIdx, "calibration.n_points", parseInt(e.target.value, 10) || 60); updateLayer(selectedIdx, "fit_stale", true); }} />
                        </div>
                      </div>
                    </div>

                    <div className="fit-pane fit-pane-accent">
                      <div className="fit-pane-head">
                        <h6>Fit Setup</h6>
                        <p>Procedure, fitting window, and shear-strength anchor used by preview.</p>
                      </div>
                      <div className="fit-setup-topline">
                        <div className="field">
                          <label htmlFor="profile-calibration-fit-procedure">Fit Procedure</label>
                          <select id="profile-calibration-fit-procedure" value=${sel.calibration.fit_procedure || "MR"} onChange=${e => { updateLayer(selectedIdx, "calibration.fit_procedure", e.target.value || "MR"); updateLayer(selectedIdx, "fit_stale", true); }}>
                            <option value="MR">MR (Modulus + strength)</option>
                            <option value="MRD">MRD (Modulus + damping + strength)</option>
                            <option value="DC">DC (Damping + strength)</option>
                          </select>
                        </div>
                        <label className="fit-checkbox-card" htmlFor="profile-calibration-auto-refit">
                          <span className="fit-checkbox-copy">
                            <span className="fit-checkbox-label">Auto Refit</span>
                            <small>On curve change</small>
                          </span>
                          <input id="profile-calibration-auto-refit" type="checkbox" checked=${sel.calibration.auto_refit_on_reference_change !== false} onChange=${e => updateLayer(selectedIdx, "calibration.auto_refit_on_reference_change", !!e.target.checked)} />
                        </label>
                        <div className="field">
                          <label htmlFor="profile-calibration-fit-min-strength">Min Strength (%)</label>
                          <input id="profile-calibration-fit-min-strength" type="number" min="1" max="100" step="1" value=${sel.calibration.fit_limits?.min_strength_pct ?? 95} onInput=${e => { const v = parseFloat(e.target.value); updateLayer(selectedIdx, "calibration.fit_limits.min_strength_pct", Number.isFinite(v) ? v : 95); updateLayer(selectedIdx, "fit_stale", true); }} />
                        </div>
                      </div>
                      <div className="profile-stage-grid profile-stage-grid-4 fit-compact-grid fit-setup-grid">
                        <div className="field">
                          <label htmlFor="profile-calibration-fit-strain-min">Fit Strain Min</label>
                          <input id="profile-calibration-fit-strain-min" type="number" step="any" min="1e-8" value=${sel.calibration.fit_strain_min ?? 1e-6} onInput=${e => { updateLayer(selectedIdx, "calibration.fit_strain_min", parseFloat(e.target.value) || 1e-6); updateLayer(selectedIdx, "fit_stale", true); }} />
                        </div>
                        <div className="field">
                          <label htmlFor="profile-calibration-fit-strain-max">Fit Strain Max</label>
                          <input id="profile-calibration-fit-strain-max" type="number" step="any" min="1e-6" value=${sel.calibration.fit_strain_max ?? 5e-4} onInput=${e => { updateLayer(selectedIdx, "calibration.fit_strain_max", parseFloat(e.target.value) || 5e-4); updateLayer(selectedIdx, "fit_stale", true); }} />
                        </div>
                        ${sel.material === "gqh" ? html`
                          <div className="field">
                            <label htmlFor="profile-calibration-target-strength">Target Shear Strength (kPa)</label>
                            <input id="profile-calibration-target-strength" type="number" min="1" step="1" value=${sel.calibration.target_strength_kpa ?? sel.material_params?.tau_max ?? ""} onInput=${e => { const nextVal = parseFloat(e.target.value); updateLayer(selectedIdx, "calibration.target_strength_kpa", Number.isFinite(nextVal) && nextVal > 0 ? nextVal : null); updateLayer(selectedIdx, "fit_stale", true); }} />
                          </div>
                          <div className="field">
                            <label htmlFor="profile-calibration-target-ratio">Target Strength Ratio</label>
                            <input id="profile-calibration-target-ratio" type="number" min="0.1" max="1" step="0.01" value=${sel.calibration.target_strength_ratio ?? 0.95} onInput=${e => { updateLayer(selectedIdx, "calibration.target_strength_ratio", parseFloat(e.target.value) || 0.95); updateLayer(selectedIdx, "fit_stale", true); }} />
                          </div>
                          <div className="field">
                            <label htmlFor="profile-calibration-target-strain">Target Strength Strain</label>
                            <input id="profile-calibration-target-strain" type="number" min="1e-4" step="0.01" value=${sel.calibration.target_strength_strain ?? 0.1} onInput=${e => { updateLayer(selectedIdx, "calibration.target_strength_strain", parseFloat(e.target.value) || 0.1); updateLayer(selectedIdx, "fit_stale", true); }} />
                          </div>
                        ` : null}
                      </div>
                    </div>
                  </div>

                  <details open=${fitLimitsOpen} className="fit-limits-panel">
                    <summary>Fitting Limits</summary>
                    <div className="profile-stage-grid profile-stage-grid-4 fit-compact-grid fit-limit-grid">
                      <div className="field">
                        <label htmlFor="profile-calibration-fit-mr-min">MR Min Strain</label>
                        <input id="profile-calibration-fit-mr-min" type="number" step="any" min="1e-8" value=${sel.calibration.fit_limits?.mr_min_strain ?? ""} placeholder=${String(sel.calibration.fit_strain_min ?? 1e-6)} onInput=${e => { const v = parseFloat(e.target.value); updateLayer(selectedIdx, "calibration.fit_limits.mr_min_strain", Number.isFinite(v) && v > 0 ? v : null); updateLayer(selectedIdx, "fit_stale", true); }} />
                      </div>
                      <div className="field">
                        <label htmlFor="profile-calibration-fit-mr-max">MR Max Strain</label>
                        <input id="profile-calibration-fit-mr-max" type="number" step="any" min="1e-8" value=${sel.calibration.fit_limits?.mr_max_strain ?? ""} placeholder=${String(sel.calibration.fit_strain_max ?? 5e-4)} onInput=${e => { const v = parseFloat(e.target.value); updateLayer(selectedIdx, "calibration.fit_limits.mr_max_strain", Number.isFinite(v) && v > 0 ? v : null); updateLayer(selectedIdx, "fit_stale", true); }} />
                      </div>
                      <div className="field">
                        <label htmlFor="profile-calibration-fit-theta3">Fix Theta3</label>
                        <input id="profile-calibration-fit-theta3" type="number" step="any" min="0.0001" value=${sel.calibration.fit_limits?.fix_theta3 ?? ""} placeholder="auto" onInput=${e => { const v = parseFloat(e.target.value); updateLayer(selectedIdx, "calibration.fit_limits.fix_theta3", Number.isFinite(v) && v > 0 ? v : null); updateLayer(selectedIdx, "fit_stale", true); }} />
                      </div>
                      <div className="field">
                        <label htmlFor="profile-calibration-fit-damp-min">Damping Min Strain</label>
                        <input id="profile-calibration-fit-damp-min" type="number" step="any" min="1e-8" value=${sel.calibration.fit_limits?.damping_min_strain ?? ""} placeholder=${String(sel.calibration.fit_strain_min ?? 1e-6)} onInput=${e => { const v = parseFloat(e.target.value); updateLayer(selectedIdx, "calibration.fit_limits.damping_min_strain", Number.isFinite(v) && v > 0 ? v : null); updateLayer(selectedIdx, "fit_stale", true); }} />
                      </div>
                      <div className="field">
                        <label htmlFor="profile-calibration-fit-damp-max">Damping Max Strain</label>
                        <input id="profile-calibration-fit-damp-max" type="number" step="any" min="1e-8" value=${sel.calibration.fit_limits?.damping_max_strain ?? ""} placeholder=${String(sel.calibration.fit_strain_max ?? 5e-4)} onInput=${e => { const v = parseFloat(e.target.value); updateLayer(selectedIdx, "calibration.fit_limits.damping_max_strain", Number.isFinite(v) && v > 0 ? v : null); updateLayer(selectedIdx, "fit_stale", true); }} />
                      </div>
                      <div className="field">
                        <label htmlFor="profile-calibration-reload">Reload Factor</label>
                        <input id="profile-calibration-reload" type="number" min="0.1" step="0.1" value=${sel.calibration.reload_factor ?? (sel.material === "gqh" ? 1.6 : 2.0)} onInput=${e => { updateLayer(selectedIdx, "calibration.reload_factor", parseFloat(e.target.value) || (sel.material === "gqh" ? 1.6 : 2.0)); updateLayer(selectedIdx, "fit_stale", true); }} />
                      </div>
                    </div>
                  </details>

                  ${previewDampingGuard ? html`
                    <div className="error-banner fit-warning-banner">
                      Final MRDF damping still deviates from the selected target. Tighten the damping window or switch fit procedure before applying.
                      ${calibPreview?.damping_rmse != null ? html` Current damping RMSE: <b>${fmt(calibPreview.damping_rmse, 3)}</b>.` : null}
                    </div>
                  ` : null}
                  <div className="calibration-actions fit-actions">
                    <button type="button" className="btn btn-sm" onClick=${() => loadCalibPreview(sel)}>Preview Curves</button>
                    <button type="button" className="btn btn-sm btn-accent" disabled=${!canApplyFit} title="Re-fit selected reference curve and apply fitted parameters" onClick=${() => refitAndApply(sel)}>Refit & Apply</button>
                    <button type="button" className="btn btn-sm" onClick=${() => { updateLayer(selectedIdx, "calibration", null); updateLayer(selectedIdx, "fit_stale", false); }}>Clear Fit</button>
                  </div>
                ` : html`
                  <div className="stage-empty">
                    <p className="muted">Enable curve fitting to map the selected reference curve into a GeoWave ${selectedMaterialDef.value.toUpperCase()} backbone.</p>
                    <button type="button" className="btn btn-sm btn-accent" onClick=${() => enableDarendeliCalibration(selectedIdx)}>Enable Curve Fit</button>
                  </div>
                `}
              ` : html`
                <div className="stage-empty">
                  <p className="muted">Elastic layers skip reference-curve fitting. Step 2 preview is limited to direct elastic properties.</p>
                </div>
              `}

              ${calibPreview ? html`
                <div className="preview-shell fit-preview-shell">
                  <div className="fit-preview-head">
                    <div>
                      <h6>Preview Curves</h6>
                      <p>Preview uses the final MRDF damping curve, not the intermediate damping proxy.</p>
                    </div>
                    ${calibPreview.fit_stale ? html`<span className="fit-preview-badge">Refit required</span>` : null}
                  </div>
                  ${calibPreview.fit_stale ? html`<p className="error-text" style=${{ marginBottom: "0.4rem" }}>Reference curve or calibration inputs changed. Refit is required before using fitted parameters.</p>` : null}
                  ${calibPreview.damping_rmse != null && calibPreview.damping_rmse > 0.40 ? html`<p className="error-text" style=${{ marginBottom: "0.4rem" }}>Damping mismatch is high (log-RMSE ${fmt(calibPreview.damping_rmse, 3)}). Review fit procedure and limits.</p>` : null}
                  <div className="metric-row compact fit-preview-metrics">
                    ${calibPreview.fit_procedure ? html`<div className="metric-card compact"><span>Fit Procedure</span><b>${calibPreview.fit_procedure}</b></div>` : null}
                    ${calibPreview.gqh_mode ? html`<div className="metric-card compact"><span>GQ/H Mode</span><b>${calibPreview.gqh_mode}</b></div>` : null}
                    ${calibPreview.modulus_rmse != null ? html`<div className=${"metric-card compact" + modulusTone}><span>Modulus RMSE</span><b>${fmt(calibPreview.modulus_rmse, 3)}</b></div>` : null}
                    ${calibPreview.damping_rmse != null ? html`<div className=${"metric-card compact" + dampingTone}><span>Damping RMSE</span><b>${fmt(calibPreview.damping_rmse, 3)}</b></div>` : null}
                    ${calibPreview.strength_ratio_achieved != null ? html`<div className=${"metric-card compact" + strengthTone}><span>Strength Ratio</span><b>${fmt(calibPreview.strength_ratio_achieved, 3)}</b></div>` : null}
                    ${calibPreview.implied_strength_kpa != null ? html`<div className="metric-card compact"><span>Implied Strength</span><b>${fmt(calibPreview.implied_strength_kpa, 2)} kPa</b></div>` : null}
                    ${calibPreview.implied_friction_angle_deg != null ? html`<div className="metric-card compact"><span>Friction Angle</span><b>${fmt(calibPreview.implied_friction_angle_deg, 2)}°</b></div>` : null}
                  </div>
                  <div className="calib-charts fit-chart-grid">
                    <${MultiSeriesChart}
                      title="G/Gmax" logX=${true}
                      xLabel="Strain" yLabel="G/Gmax"
                      h=${220}
                      series=${[
                        calibPreview.target_available ? { x: calibPreview.strain, y: calibPreview.target_modulus_reduction, label: "Target", color: "#2980B9" } : null,
                        { x: calibPreview.strain, y: calibPreview.fitted_modulus_reduction, label: "Fitted", color: "#D35400" },
                        refCurveData ? { x: refCurveData.strain, y: refCurveData.modulus_reduction || refCurveData.g_gmax || [], label: "Reference", color: "#27AE60" } : null,
                      ].filter(Boolean)}
                    />
                    <${MultiSeriesChart}
                      title="Damping Ratio" logX=${true}
                      xLabel="Strain" yLabel="Damping (%)"
                      h=${220}
                      series=${[
                        calibPreview.target_available ? { x: calibPreview.strain, y: calibPreview.target_damping_ratio.map(v => v * 100), label: "Target", color: "#2980B9" } : null,
                        { x: calibPreview.strain, y: calibPreview.fitted_damping_ratio.map(v => v * 100), label: "Fitted", color: "#8E44AD" },
                        refCurveData ? { x: refCurveData.strain, y: (refCurveData.damping_ratio || refCurveData.damping || []).map(v => v * 100), label: "Reference", color: "#27AE60" } : null,
                      ].filter(Boolean)}
                    />
                  </div>
                </div>
              ` : null}
            </section>

            ${supportsReduction ? html`
              <section className="profile-stage">
                <div className="section-head">
                  <h5>Reduction Factor Formulation</h5>
                  <p>Unload-reload degradation controls stay explicit, but this minimal flow keeps only MRDF-UIUC active.</p>
                </div>
                <div className="profile-stage-grid profile-stage-grid-4">
                  <div className="field profile-stage-span-4">
                    <label htmlFor="profile-reduction-formulation">Formulation</label>
                    <select id="profile-reduction-formulation" value="mrdf_uiuc" disabled><option value="mrdf_uiuc">MRDF-UIUC</option></select>
                  </div>
                  <div className="field">
                    <label htmlFor="profile-reduction-reload">Reload Factor</label>
                    <input id="profile-reduction-reload" type="number" step="0.05" min="0.1" value=${sel.material_params?.reload_factor ?? ""} onInput=${e => updateLayer(selectedIdx, "material_params.reload_factor", parseFloat(e.target.value) || null)} />
                  </div>
                  <div className="field">
                    <label htmlFor="profile-reduction-p1">MRDF P1</label>
                    <input id="profile-reduction-p1" type="number" step="any" value=${sel.material_params?.mrdf_p1 ?? ""} onInput=${e => updateLayer(selectedIdx, "material_params.mrdf_p1", parseFloat(e.target.value) || null)} />
                  </div>
                  <div className="field">
                    <label htmlFor="profile-reduction-p2">MRDF P2</label>
                    <input id="profile-reduction-p2" type="number" step="any" value=${sel.material_params?.mrdf_p2 ?? ""} onInput=${e => updateLayer(selectedIdx, "material_params.mrdf_p2", parseFloat(e.target.value) || null)} />
                  </div>
                  <div className="field">
                    <label htmlFor="profile-reduction-p3">MRDF P3</label>
                    <input id="profile-reduction-p3" type="number" step="any" value=${sel.material_params?.mrdf_p3 ?? ""} onInput=${e => updateLayer(selectedIdx, "material_params.mrdf_p3", parseFloat(e.target.value) || null)} />
                  </div>
                </div>
                <details className="params-section params-section-subtle">
                  <summary>Manual Parameter Overrides</summary>
                  <div className="param-grid">
                    ${Object.entries(sel.material_params || {}).map(([key, val]) => html`
                      <div className="field" key=${key}>
                        <label htmlFor=${`profile-material-param-${key}`}>${key}</label>
                        <input id=${`profile-material-param-${key}`} type="number" step="any" value=${val} onInput=${e => updateLayer(selectedIdx, "material_params." + key, parseFloat(e.target.value))} />
                      </div>
                    `)}
                  </div>
                </details>
              </section>
            ` : null}

            <section className="profile-stage">
              <div className="section-head">
                <h5>Saved Materials / Single Element Test</h5>
                <p>Store reusable material sets locally and probe the current backbone with quick cyclic presets.</p>
              </div>
              <div className="profile-stage-grid profile-stage-grid-2">
                <div className="saved-material-shell">
                  <div className="row" style=${{ alignItems: "end" }}>
                    <div className="field" style=${{ flex: 1 }}>
                      <label htmlFor="profile-material-library-name">Save Material As</label>
                      <input id="profile-material-library-name" type="text" value=${materialLibraryName} placeholder=${sel.name || `Layer ${selectedIdx + 1}`} onInput=${e => setMaterialLibraryName(e.target.value)} />
                    </div>
                    <div className="field" style=${{ display: "flex", alignItems: "end" }}>
                      <button type="button" className="btn btn-sm" onClick=${saveSelectedMaterialToLibrary}>Save Material</button>
                    </div>
                  </div>
                  ${savedMaterials.length ? html`
                    <div className="saved-material-list">
                      ${savedMaterials.map(item => html`
                        <div key=${item.id} className="saved-material-row">
                          <div className="saved-material-name">
                            <div>${item.name}</div>
                            <div className="saved-material-meta">${(item.material || "mkz").toUpperCase()}${item.reference_curve ? ` • ${item.reference_curve}` : ""}</div>
                          </div>
                          <button type="button" className="btn btn-sm" onClick=${() => applySavedMaterialToLayer(item)}>Load</button>
                          <button type="button" className="btn btn-sm" onClick=${() => deleteSavedMaterial(item.id)}>Delete</button>
                        </div>
                      `)}
                    </div>
                  ` : html`<p className="muted section-footnote">No saved materials yet.</p>`}
                </div>

                <div className="saved-material-shell">
                  <div className="field">
                    <label htmlFor="profile-set-preset">Single Element Test Preset</label>
                    <select id="profile-set-preset" aria-label="Single element test preset" value=${setPreset} onChange=${e => setSetPreset(e.target.value)}>
                      ${SET_PRESETS.map(preset => html`<option key=${preset.id} value=${preset.id}>${preset.label} (${preset.strain})</option>`)}
                    </select>
                  </div>
                  <div className="metric-row compact" style=${{ marginBottom: "0.5rem" }}>
                    <div className="metric-card compact"><span>Preset</span><b>${setPresetMeta.label}</b></div>
                    <div className="metric-card compact"><span>Strain</span><b>${setPresetMeta.strain}</b></div>
                  </div>
                  <div className="calibration-actions">
                    <button type="button" className="btn btn-sm" disabled=${!isCalibratable} onClick=${runSelectedSetPreset}>Single Element Test</button>
                  </div>
                  ${!isCalibratable ? html`<p className="muted section-footnote">SET is only available for fitted MKZ and GQ/H layers.</p>` : null}
                </div>
              </div>

              ${setResult ? html`
                <div className="set-results">
                  <h5>Single Element Test</h5>
                  <div className="metric-row">
                    <div className="metric-card"><span>G/Gmax</span><b>${fmt(setResult.g_reduction, 4)}</b></div>
                    <div className="metric-card"><span>Masing D</span><b>${fmt(setResult.masing_damping_ratio, 4)}</b></div>
                    <div className="metric-card"><span>G_sec (kPa)</span><b>${fmt(setResult.secant_modulus, 0)}</b></div>
                    <div className="metric-card"><span>Peak Stress (kPa)</span><b>${fmt(setResult.peak_stress, 2)}</b></div>
                  </div>
                  <${ChartCard} title="Stress-Strain Loop" x=${setResult.loop_strain} y=${setResult.loop_stress} xLabel="Strain" yLabel="Stress (kPa)" color="#D35400" />
                </div>
              ` : null}
            </section>
          `}
        </div>
      ` : html`<div className="layer-properties"><p className="muted">Select a layer to edit.</p></div>`}
    </div>
    </div>
  `;
}
