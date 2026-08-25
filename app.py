from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import tempfile
from datetime import datetime
from pathlib import Path
from enum import Enum
from dataclasses import asdict, is_dataclass
import math
import json

app = Flask(__name__)
CORS(app)
sessions = {}

HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Item Analysis</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --paper: #F3F5F8;
            --panel: #FFFFFF;
            --ink: #16233E;
            --ink-soft: #5A6785;
            --ink-faint: #92A0BD;
            --line: #DEE4EF;
            --blueprint: #2C5F8A;
            --blueprint-dark: #1E4D74;
            --blueprint-tint: #E7EFF6;
            --green: #2F8F5B;
            --green-tint: #E3F3EA;
            --amber: #C9862B;
            --amber-tint: #FBF0DE;
            --rust: #BD5B34;
            --rust-tint: #FAEAE2;
            --red: #B23A32;
            --red-tint: #FAE7E5;
            --font-display: 'Space Grotesk', sans-serif;
            --font-body: 'IBM Plex Sans', sans-serif;
            --font-mono: 'IBM Plex Mono', monospace;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        @media (prefers-reduced-motion: reduce) {
            * { animation-duration: 0.001ms !important; transition-duration: 0.001ms !important; }
        }

        body {
            font-family: var(--font-body);
            background: var(--paper);
            color: var(--ink);
            min-height: 100vh;
            padding: 32px 20px;
            line-height: 1.5;
        }

        :focus-visible { outline: 2px solid var(--blueprint); outline-offset: 2px; }

        .container { max-width: 900px; margin: 0 auto; }

        /* ---------- Header ---------- */
        .header {
            background: var(--ink);
            background-image:
                linear-gradient(rgba(255,255,255,0.06) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.06) 1px, transparent 1px);
            background-size: 28px 28px;
            border-radius: 16px;
            color: #fff;
            padding: 40px 36px;
            position: relative;
            overflow: hidden;
        }
        .header::after {
            content: "";
            position: absolute;
            inset: 0;
            background: radial-gradient(circle at 85% 20%, rgba(44,95,138,0.55), transparent 60%);
            pointer-events: none;
        }
        .eyebrow {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-family: var(--font-mono);
            font-size: 11px;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: #AFC3DC;
            position: relative;
        }
        .eyebrow svg { flex-shrink: 0; }
        .header h1 {
            font-family: var(--font-display);
            font-weight: 700;
            font-size: 30px;
            letter-spacing: -0.01em;
            margin: 10px 0 8px;
            position: relative;
        }
        .header p {
            color: #C5D2E6;
            font-size: 14.5px;
            max-width: 46ch;
            position: relative;
        }

        /* ---------- Upload tray ---------- */
        .content { padding-top: 28px; }

        .upload-tray {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 28px;
        }
        .upload-tray h2 {
            font-family: var(--font-display);
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .upload-tray .sub {
            color: var(--ink-soft);
            font-size: 13.5px;
            margin-bottom: 20px;
        }

        .slots {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }
        @media (max-width: 620px) {
            .slots { grid-template-columns: 1fr; }
        }

        .slot {
            border: 1.5px dashed var(--line);
            border-radius: 12px;
            padding: 20px 16px;
            text-align: center;
            background: var(--paper);
            transition: border-color 0.15s, background 0.15s;
        }
        .slot.filled {
            border-style: solid;
            border-color: var(--green);
            background: var(--green-tint);
        }
        .slot-icon {
            width: 30px; height: 30px;
            margin: 0 auto 10px;
            color: var(--blueprint);
        }
        .slot.filled .slot-icon { color: var(--green); }
        .slot-title {
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 2px;
        }
        .slot-desc {
            font-size: 12px;
            color: var(--ink-soft);
            margin-bottom: 14px;
        }
        .file-input { display: none; }
        .file-label {
            display: inline-block;
            background: var(--blueprint);
            color: white;
            padding: 9px 18px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            font-size: 13px;
            transition: background 0.15s, transform 0.1s;
        }
        .file-label:hover { background: var(--blueprint-dark); }
        .file-label:active { transform: scale(0.98); }
        .file-name {
            font-family: var(--font-mono);
            color: var(--ink-soft);
            font-size: 12px;
            margin-top: 10px;
            word-break: break-all;
        }
        .slot.filled .file-name { color: var(--green); font-weight: 500; }

        .analyze-btn {
            display: block;
            width: 100%;
            background: var(--blueprint);
            color: white;
            border: none;
            padding: 14px 24px;
            border-radius: 10px;
            cursor: pointer;
            font-family: var(--font-display);
            font-size: 15px;
            font-weight: 600;
            margin-top: 20px;
            transition: background 0.15s, transform 0.1s;
        }
        .analyze-btn:hover:not(:disabled) { background: var(--blueprint-dark); }
        .analyze-btn:active:not(:disabled) { transform: scale(0.995); }
        .analyze-btn:disabled { background: #C7CEDB; cursor: not-allowed; }

        /* ---------- Status ---------- */
        .status {
            margin: 18px 0 0;
            padding: 13px 16px;
            border-radius: 10px;
            display: none;
            align-items: center;
            gap: 10px;
            font-weight: 500;
            font-size: 13.5px;
        }
        .status.show { display: flex; }
        .status.success { background: var(--green-tint); color: var(--green); }
        .status.error { background: var(--red-tint); color: var(--red); }
        .status.loading { background: var(--blueprint-tint); color: var(--blueprint-dark); }
        .spinner {
            width: 14px; height: 14px;
            border-radius: 50%;
            border: 2px solid rgba(44,95,138,0.25);
            border-top-color: var(--blueprint);
            animation: spin 0.7s linear infinite;
            flex-shrink: 0;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* ---------- Results ---------- */
        .results { margin-top: 36px; display: none; }
        .results.show { display: block; }

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 14px;
            margin-bottom: 28px;
        }
        .stat-card {
            background: var(--panel);
            border: 1px solid var(--line);
            border-top: 3px solid var(--blueprint);
            border-radius: 12px;
            padding: 16px 18px;
        }
        .stat-label {
            font-family: var(--font-mono);
            font-size: 10.5px;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--ink-soft);
            margin-bottom: 6px;
        }
        .stat-value {
            font-family: var(--font-mono);
            font-size: 30px;
            font-weight: 600;
            color: var(--ink);
        }

        .section-head {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 4px;
        }
        .section-head h3 {
            font-family: var(--font-display);
            font-size: 18px;
            font-weight: 600;
        }
        .section-note {
            color: var(--ink-soft);
            font-size: 12.5px;
            margin-bottom: 18px;
        }

        /* ---------- Item cards ---------- */
        .item-card {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 14px;
            margin-bottom: 12px;
            overflow: hidden;
        }
        .item-row {
            cursor: pointer;
            padding: 18px 20px;
        }
        .item-row-top {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 16px;
        }
        .toggle-icon {
            display: inline-block;
            color: var(--blueprint);
            font-size: 11px;
            transition: transform 0.15s;
            flex-shrink: 0;
        }
        .item-row.expanded .toggle-icon { transform: rotate(90deg); }
        .item-q {
            font-family: var(--font-display);
            font-weight: 600;
            font-size: 15.5px;
            flex-grow: 1;
        }

        .badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.03em;
            text-transform: uppercase;
        }
        .retain { background: var(--green-tint); color: var(--green); }
        .review { background: var(--amber-tint); color: var(--amber); }
        .revise { background: var(--rust-tint); color: var(--rust); }
        .discard { background: var(--red-tint); color: var(--red); }

        .gauge-group {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 22px;
            margin-bottom: 16px;
        }
        @media (max-width: 620px) {
            .gauge-group { grid-template-columns: 1fr; gap: 14px; }
        }
        .gauge-label {
            font-family: var(--font-mono);
            font-size: 10.5px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--ink-soft);
            display: flex;
            justify-content: space-between;
            margin-bottom: 6px;
        }
        .gauge-label b {
            font-family: var(--font-mono);
            color: var(--ink);
            font-weight: 600;
            font-size: 11.5px;
        }
        .gauge-track {
            position: relative;
            height: 8px;
            background: var(--line);
            border-radius: 5px;
            overflow: visible;
        }
        .gauge-fill {
            position: absolute;
            top: 0; left: 0; bottom: 0;
            border-radius: 5px;
        }
        .gauge-fill.good { background: var(--green); }
        .gauge-fill.mid { background: var(--amber); }
        .gauge-fill.poor { background: var(--red); }
        .gauge-needle {
            position: absolute;
            top: -3px;
            width: 2px;
            height: 14px;
            background: var(--ink);
            transform: translateX(-1px);
        }
        .gauge-zero {
            position: absolute;
            left: 50%; top: -2px;
            width: 1px; height: 12px;
            background: var(--ink-faint);
        }
        .gauge-scale {
            display: flex;
            justify-content: space-between;
            font-family: var(--font-mono);
            font-size: 9.5px;
            color: var(--ink-faint);
            margin-top: 4px;
        }

        .item-row-bottom {
            display: flex;
            align-items: center;
            gap: 24px;
            flex-wrap: wrap;
        }
        .mini-stat { display: flex; align-items: center; gap: 8px; }
        .mini-label {
            font-family: var(--font-mono);
            font-size: 10.5px;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: var(--ink-soft);
        }
        .mini-value {
            font-family: var(--font-mono);
            font-weight: 600;
            font-size: 13px;
        }
        .mini-value.good { color: var(--green); }
        .mini-value.mid { color: var(--amber); }
        .mini-value.poor { color: var(--red); }

        .nfd-badge {
            display: inline-block;
            background: var(--red-tint);
            color: var(--red);
            font-family: var(--font-mono);
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            margin-right: 4px;
        }
        .nfd-none { color: var(--green); font-weight: 600; font-size: 12.5px; }

        /* ---------- Expanded detail ---------- */
        .detail-row { display: none; }
        .detail-row.show { display: block; }
        .detail-wrap {
            padding: 4px 20px 22px;
            border-top: 1px solid var(--line);
            padding-top: 18px;
        }
        .detail-wrap h4 {
            font-family: var(--font-mono);
            font-size: 11px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--ink-soft);
            margin-bottom: 12px;
        }

        .dist-bar {
            display: flex;
            width: 100%;
            height: 30px;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid var(--line);
            margin-bottom: 14px;
        }
        .dist-seg {
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: var(--font-mono);
            font-size: 11.5px;
            font-weight: 600;
            color: white;
            min-width: 2px;
        }
        .dist-seg.correct { background: var(--green); }
        .dist-seg.ok { background: var(--blueprint); }
        .dist-seg.nfd { background: var(--red); opacity: 0.85; }
        .dist-seg.empty { background: var(--ink-faint); }

        .opt-legend {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 8px;
        }
        .opt-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            padding: 8px 12px;
            border-radius: 8px;
            background: var(--paper);
            font-size: 13px;
        }
        .opt-row.opt-correct { background: var(--green-tint); }
        .opt-row.opt-nfd { background: var(--red-tint); }
        .opt-letter { font-family: var(--font-mono); font-weight: 700; }
        .opt-meta { font-family: var(--font-mono); font-size: 12px; color: var(--ink-soft); }
        .opt-tag {
            font-size: 10px; font-weight: 700; letter-spacing: 0.03em;
            padding: 2px 7px; border-radius: 10px; color: white; text-transform: uppercase;
        }
        .opt-tag.correct { background: var(--green); }
        .opt-tag.nfd { background: var(--red); }
        .opt-tag.ok { background: var(--ink-faint); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="eyebrow">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/></svg>
                Item analysis instrument
            </span>
            <h1>Diagnose your assessment, question by question</h1>
            <p>Upload an answer key and student responses to get difficulty, discrimination, and distractor readouts for every item.</p>
        </div>

        <div class="content">
            <div class="upload-tray">
                <h2>Load test data</h2>
                <div class="sub">Two Excel files are needed to run the analysis.</div>

                <div class="slots">
                    <div class="slot" id="keySlot">
                        <svg class="slot-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M14 3h-4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/><path d="M9 13h6M9 17h6"/></svg>
                        <div class="slot-title">Answer key</div>
                        <div class="slot-desc">Correct option for each question</div>
                        <label class="file-label">
                            Choose file
                            <input type="file" id="keyFile" class="file-input" accept=".xlsx,.xls">
                        </label>
                        <div class="file-name" id="keyName">No file selected</div>
                    </div>

                    <div class="slot" id="dataSlot">
                        <svg class="slot-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                        <div class="slot-title">Student responses</div>
                        <div class="slot-desc">Each student's answers, per question</div>
                        <label class="file-label">
                            Choose file
                            <input type="file" id="dataFile" class="file-input" accept=".xlsx,.xls">
                        </label>
                        <div class="file-name" id="dataName">No file selected</div>
                    </div>
                </div>

                <button class="analyze-btn" id="analyzeBtn">Run analysis</button>
                <div class="status" id="status"></div>
            </div>

            <div class="results" id="results"></div>
        </div>
    </div>

    <script>
        const keyFile = document.getElementById('keyFile');
        const dataFile = document.getElementById('dataFile');
        const analyzeBtn = document.getElementById('analyzeBtn');
        const status = document.getElementById('status');
        const results = document.getElementById('results');

        const ICONS = {
            loading: '<span class="spinner"></span>',
            success: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M20 6 9 17l-5-5"/></svg>',
            error: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><circle cx="12" cy="12" r="9"/><line x1="12" y1="8" x2="12" y2="13"/><line x1="12" y1="16.5" x2="12" y2="16.5"/></svg>'
        };

        keyFile.addEventListener('change', function() {
            const name = this.files[0] ? this.files[0].name : 'No file selected';
            document.getElementById('keyName').textContent = name;
            document.getElementById('keySlot').classList.toggle('filled', !!this.files[0]);
        });

        dataFile.addEventListener('change', function() {
            const name = this.files[0] ? this.files[0].name : 'No file selected';
            document.getElementById('dataName').textContent = name;
            document.getElementById('dataSlot').classList.toggle('filled', !!this.files[0]);
        });

        analyzeBtn.addEventListener('click', async function() {
            if (!keyFile.files[0]) {
                showStatus('Please choose an answer key file', 'error');
                return;
            }

            if (!dataFile.files[0]) {
                showStatus('Please choose a student responses file', 'error');
                return;
            }

            analyzeBtn.disabled = true;
            showStatus('Uploading files…', 'loading');

            const formData = new FormData();
            formData.append('answer_key', keyFile.files[0]);
            formData.append('student_data', dataFile.files[0]);

            try {
                const uploadRes = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });

                if (!uploadRes.ok) {
                    const error = await uploadRes.json();
                    throw new Error(error.error || 'Upload failed');
                }

                const uploadData = await uploadRes.json();
                showStatus('Analyzing…', 'loading');

                const analyzeRes = await fetch(`/api/analyze/${uploadData.session_id}`, {
                    method: 'POST'
                });

                if (!analyzeRes.ok) {
                    const error = await analyzeRes.json();
                    throw new Error(error.error || 'Analysis failed');
                }

                const analyzeData = await analyzeRes.json();
                showStatus('Analysis complete', 'success');
                displayResults(analyzeData.data);

            } catch (error) {
                showStatus(error.message, 'error');
            } finally {
                analyzeBtn.disabled = false;
            }
        });

        function showStatus(msg, type) {
            status.innerHTML = (ICONS[type] || '') + '<span>' + msg + '</span>';
            status.className = 'status show ' + type;
        }

        function effClass(pct) {
            if (pct >= 66) return 'good';
            if (pct >= 33) return 'mid';
            return 'poor';
        }

        function diffFillClass(status) {
            if (status === 'Ideal') return 'good';
            if (status === 'Too Easy') return 'mid';
            return 'poor'; // Very Difficult
        }

        function discFillClass(status) {
            if (status === 'Good') return 'good';
            if (status === 'Poor') return 'mid';
            return 'poor'; // Negative
        }

        function displayResults(data) {
            const s = data.summary;
            const items = data.items || [];

            let html = '';
            html += '<div class="stats">';
            html += `<div class="stat-card"><div class="stat-label">Students</div><div class="stat-value">${s.total_students}</div></div>`;
            html += `<div class="stat-card"><div class="stat-label">Questions</div><div class="stat-value">${s.total_questions}</div></div>`;
            html += '</div>';

            html += '<div class="section-head"><h3>Per-question analysis</h3></div>';
            html += '<div class="section-note">Click a card for the full response breakdown. A distractor picked by fewer than 5% of students is flagged non-functional (NFD).</div>';

            items.forEach((item, idx) => {
                const rec = item.recommendation.toLowerCase();
                const eff = item.distractor_efficiency || 0;
                const nfds = item.non_functional_distractors || [];
                const nfdHtml = nfds.length
                    ? nfds.map(o => `<span class="nfd-badge">${o}</span>`).join('')
                    : '<span class="nfd-none">None</span>';

                const diffPct = Math.max(0, Math.min(1, item.difficulty || 0)) * 100;
                const disc = Math.max(-1, Math.min(1, item.discrimination || 0));
                const discPct = ((disc + 1) / 2) * 100;
                const discFillLeft = disc >= 0 ? 50 : discPct;
                const discFillWidth = Math.abs(discPct - 50);

                html += `<div class="item-card">`;
                html += `<div class="item-row" id="row-${idx}" tabindex="0" onclick="toggleRow(${idx})" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();toggleRow(${idx})}">`;

                html += `<div class="item-row-top">`;
                html += `<span class="toggle-icon">▶</span>`;
                html += `<span class="item-q">${item.question}</span>`;
                html += `<span class="badge ${rec}">${item.recommendation}</span>`;
                html += `</div>`;

                html += `<div class="gauge-group">`;
                html += `<div class="gauge">`;
                html += `<div class="gauge-label">Difficulty <b>${(item.difficulty || 0).toFixed(3)} · ${item.difficulty_status}</b></div>`;
                html += `<div class="gauge-track"><div class="gauge-fill ${diffFillClass(item.difficulty_status)}" style="width:${diffPct}%"></div><div class="gauge-needle" style="left:${diffPct}%"></div></div>`;
                html += `<div class="gauge-scale"><span>0.0</span><span>0.5</span><span>1.0</span></div>`;
                html += `</div>`;

                html += `<div class="gauge">`;
                html += `<div class="gauge-label">Discrimination <b>${(item.discrimination || 0).toFixed(3)} · ${item.discrimination_status}</b></div>`;
                html += `<div class="gauge-track"><div class="gauge-zero"></div><div class="gauge-fill ${discFillClass(item.discrimination_status)}" style="left:${discFillLeft}%;width:${discFillWidth}%"></div><div class="gauge-needle" style="left:${discPct}%"></div></div>`;
                html += `<div class="gauge-scale"><span>-1.0</span><span>0.0</span><span>+1.0</span></div>`;
                html += `</div>`;
                html += `</div>`;

                html += `<div class="item-row-bottom">`;
                html += `<div class="mini-stat"><span class="mini-label">Distractor efficiency</span><span class="mini-value ${effClass(eff)}">${eff.toFixed(0)}%</span></div>`;
                html += `<div class="mini-stat"><span class="mini-label">NFDs</span>${nfdHtml}</div>`;
                html += `</div>`;

                html += `</div>`; // .item-row

                html += `<div class="detail-row" id="detail-${idx}"><div class="detail-wrap">`;
                html += `<h4>Response distribution — ${item.question}</h4>`;

                const breakdown = item.option_breakdown || [];
                html += '<div class="dist-bar">';
                breakdown.forEach(opt => {
                    const cls = opt.is_correct ? 'correct' : (opt.is_functional ? 'ok' : 'nfd');
                    const w = Math.max(opt.percentage, opt.percentage > 0 ? 3 : 0);
                    if (w > 0) {
                        html += `<div class="dist-seg ${cls}" style="flex: ${w} 0 auto;" title="${opt.option}: ${opt.percentage.toFixed(1)}%">${opt.percentage >= 8 ? opt.option : ''}</div>`;
                    }
                });
                if (item.omitted_count > 0) {
                    const w = Math.max(item.omitted_percentage, 3);
                    html += `<div class="dist-seg empty" style="flex: ${w} 0 auto;" title="No response: ${item.omitted_percentage.toFixed(1)}%">${item.omitted_percentage >= 8 ? '—' : ''}</div>`;
                }
                html += '</div>';

                html += '<div class="opt-legend">';
                breakdown.forEach(opt => {
                    let rowClass = '';
                    let tag = '<span class="opt-tag ok">Distractor OK</span>';
                    if (opt.is_correct) {
                        rowClass = 'opt-correct';
                        tag = '<span class="opt-tag correct">Correct answer</span>';
                    } else if (!opt.is_functional) {
                        rowClass = 'opt-nfd';
                        tag = '<span class="opt-tag nfd">Non-functional</span>';
                    }
                    html += `<div class="opt-row ${rowClass}"><span class="opt-letter">${opt.option}</span><span class="opt-meta">${opt.count} · ${opt.percentage.toFixed(1)}%</span>${tag}</div>`;
                });
                if (item.omitted_count > 0) {
                    html += `<div class="opt-row"><span class="opt-letter">—</span><span class="opt-meta">${item.omitted_count} · ${item.omitted_percentage.toFixed(1)}%</span><span class="opt-tag ok">No response</span></div>`;
                }
                html += '</div>'; // .opt-legend

                html += '</div></div>'; // .detail-wrap, .detail-row
                html += '</div>'; // .item-card
            });

            results.innerHTML = html;
            results.classList.add('show');
        }

        function toggleRow(idx) {
            const row = document.getElementById(`row-${idx}`);
            const detail = document.getElementById(`detail-${idx}`);
            row.classList.toggle('expanded');
            detail.classList.toggle('show');
        }
    </script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML)

def handle_nan(obj):
    """Convert NaN, Infinity, and Enums to valid JSON values"""
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, float):
        if math.isnan(obj):
            return 0.0
        if math.isinf(obj):
            return 0.0
        return obj
    if isinstance(obj, dict):
        return {k: handle_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [handle_nan(item) for item in obj]
    return obj

def serialize(obj):
    """Serialize objects to JSON, handling NaN and special types"""
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return 0.0
        return obj
    if is_dataclass(obj) and not isinstance(obj, type):
        data = asdict(obj)
        return handle_nan(data)
    if isinstance(obj, list):
        return [serialize(item) for item in obj]
    if isinstance(obj, dict):
        return handle_nan({k: serialize(v) for k, v in obj.items()})
    return obj

@app.route('/api/upload', methods=['POST'])
def upload():
    try:
        if 'answer_key' not in request.files:
            return jsonify({'error': 'answer_key file missing'}), 400
        if 'student_data' not in request.files:
            return jsonify({'error': 'student_data file missing'}), 400

        answer_key = request.files['answer_key']
        student_data = request.files['student_data']

        if not answer_key.filename or not student_data.filename:
            return jsonify({'error': 'Empty filenames'}), 400

        session_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        session_dir = Path(tempfile.gettempdir()) / f'analysis_{session_id}'
        session_dir.mkdir(exist_ok=True)

        key_path = session_dir / 'key.xlsx'
        data_path = session_dir / 'data.xlsx'

        answer_key.save(str(key_path))
        student_data.save(str(data_path))

        sessions[session_id] = {'key_path': str(key_path), 'data_path': str(data_path)}

        return jsonify({'status': 'success', 'session_id': session_id})
    except Exception as e:
        print(f"Upload error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze/<sid>', methods=['POST'])
def analyze(sid):
    try:
        if sid not in sessions:
            return jsonify({'error': 'Session not found'}), 404

        from item_analyzer import ItemAnalyzer
        s = sessions[sid]

        analyzer = ItemAnalyzer()
        results = analyzer.run_analysis(s['key_path'], s['data_path'])

        serialized = serialize(results)

        return jsonify({'status': 'success', 'data': serialized})
    except Exception as e:
        print(f"Analysis error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("""
╔════════════════════════════════════════════════════════╗
║  📊 Item Analysis Dashboard                           ║
║  🌐 URL: http://localhost:5000                        ║
║  ⏸️  Stop: Press Ctrl+C                               ║
╚════════════════════════════════════════════════════════╝
    """)
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)