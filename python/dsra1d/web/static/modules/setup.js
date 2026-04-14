/**
 * GeoWave v2 — Module setup
 * Binds htm to React.createElement and re-exports as `html`
 */
import React, { useState, useEffect, useCallback, useRef } from "../vendor/react.mjs";
import { createRoot } from "../vendor/react-dom-client.mjs";
import htm from "../vendor/htm.mjs";

const html = htm.bind(React.createElement);

export { html, React, useState, useEffect, useCallback, useRef, createRoot };
