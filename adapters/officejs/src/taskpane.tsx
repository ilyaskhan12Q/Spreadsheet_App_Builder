import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { parseBlueprintJson } from './blueprint';
import { ExcelRenderer } from './renderer';

type Stage = 'idle' | 'scanning' | 'translating' | 'validating' | 'rendering' | 'completed' | 'error';

interface StageConfig {
  label: string;
  desc: string;
}

const STAGES: Record<Exclude<Stage, 'idle' | 'completed' | 'error'>, StageConfig> = {
  scanning: { label: 'Scanning Context', desc: 'Analyzing workbook sheets, structure and named ranges...' },
  translating: { label: 'Translating Prompt', desc: 'Consulting LLM models to formulate layout strategy...' },
  validating: { label: 'Validating Blueprint', desc: 'Checking spatial merges and logical cell constraints...' },
  rendering: { label: 'Rendering Grid', desc: 'Applying cells, formatting patterns, rules, and events...' }
};

export const TaskPane: React.FC = () => {
  const [prompt, setPrompt] = useState('');
  const [stage, setStage] = useState<Stage>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  const buildApp = async () => {
    if (!prompt.trim()) return;
    setErrorMsg('');
    setStage('scanning');

    try {
      // 1. Scan workbook context using Office.js
      let workbookContext: any = null;
      try {
        await Excel.run(async (context) => {
          const sheets = context.workbook.worksheets;
          sheets.load("items/name");
          await context.sync();
          const sheetNames = sheets.items.map((s) => s.name);

          const activeSheet = sheets.getActiveWorksheet();
          const usedRange = activeSheet.getUsedRange(true); // only cells with values
          usedRange.load("address,values");
          await context.sync();

          const values = usedRange.values;
          const headers = values.length > 0 ? values[0].map((v: any) => String(v)) : [];
          const dataSample = values.slice(1, 5).map((row: any) => {
            const dict: any = {};
            headers.forEach((h, idx) => {
              if (h) {
                dict[h] = row[idx];
              } else {
                dict[`Column_${idx + 1}`] = row[idx];
              }
            });
            return dict;
          });

          workbookContext = {
            used_range: usedRange.address,
            sheet_names: sheetNames,
            headers: headers,
            data_sample: dataSample,
            existing_styles: {},
            named_ranges: {}
          };
        });
      } catch (scanErr) {
        console.warn("Could not scan workbook context, continuing with empty context:", scanErr);
      }

      // 2. Fetch API with context
      const scanResponse = await fetch('http://localhost:8000/api/build', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          prompt,
          context: workbookContext
        })
      });

      if (!scanResponse.ok) {
        const errorData = await scanResponse.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server returned status ${scanResponse.status}`);
      }

      setStage('translating');
      const responseData = await scanResponse.json();
      
      setStage('validating');
      const blueprint = parseBlueprintJson(JSON.stringify(responseData.blueprint));

      setStage('rendering');
      // Run Excel.run to perform rendering steps
      await Excel.run(async (context) => {
        const renderer = new ExcelRenderer();
        await renderer.render(blueprint, context);
        await context.sync();
      });

      setStage('completed');
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || 'An unexpected error occurred during building.');
      setStage('error');
    }
  };

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <div style={styles.logoCircle}>S</div>
        <div>
          <h1 style={styles.title}>SAB Engine</h1>
          <p style={styles.subtitle}>Spreadsheet App Builder</p>
        </div>
      </header>

      <main style={styles.main}>
        {stage === 'idle' && (
          <div style={styles.fadeContainer}>
            <label style={styles.label}>What would you like to build?</label>
            <textarea
              style={styles.textarea}
              placeholder="Describe your spreadsheet application (e.g., 'A Point of Sale terminal with quantity inputs, unit price, total calculations, and a green submit button...')"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
            <button
              style={{
                ...styles.button,
                ...(prompt.trim() ? styles.buttonActive : styles.buttonDisabled)
              }}
              onClick={buildApp}
              disabled={!prompt.trim()}
            >
              Build App
            </button>
          </div>
        )}

        {(stage === 'scanning' || stage === 'translating' || stage === 'validating' || stage === 'rendering') && (
          <div style={styles.stepperContainer}>
            <div style={styles.loaderLine}>
              <div style={styles.loaderProgress}></div>
            </div>
            
            <h2 style={styles.stageTitle}>{STAGES[stage].label}</h2>
            <p style={styles.stageDesc}>{STAGES[stage].desc}</p>

            <div style={styles.stepsWrapper}>
              {(['scanning', 'translating', 'validating', 'rendering'] as const).map((s, idx) => {
                const isDone = (['scanning', 'translating', 'validating', 'rendering'].indexOf(stage) > idx);
                const isActive = stage === s;
                return (
                  <div key={s} style={styles.stepRow}>
                    <div style={{
                      ...styles.stepDot,
                      ...(isDone ? styles.stepDotDone : isActive ? styles.stepDotActive : {})
                    }}>
                      {isDone ? '✓' : idx + 1}
                    </div>
                    <span style={{
                      ...styles.stepText,
                      ...(isActive ? styles.stepTextActive : isDone ? styles.stepTextDone : {})
                    }}>
                      {s.toUpperCase()}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {stage === 'completed' && (
          <div style={styles.successCard}>
            <div style={styles.successIcon}>✓</div>
            <h2 style={styles.successTitle}>App Rendered!</h2>
            <p style={styles.successDesc}>Your spreadsheet application has been successfully constructed in the active worksheet.</p>
            <button style={styles.buttonSecondary} onClick={() => { setPrompt(''); setStage('idle'); }}>
              Create Another
            </button>
          </div>
        )}

        {stage === 'error' && (
          <div style={styles.errorCard}>
            <div style={styles.errorIcon}>⚠</div>
            <h2 style={styles.errorTitle}>Build Failed</h2>
            <p style={styles.errorDesc}>{errorMsg}</p>
            <div style={styles.errorActions}>
              <button style={styles.button} onClick={buildApp}>
                Retry Build
              </button>
              <button style={styles.buttonSecondary} onClick={() => setStage('idle')}>
                Go Back
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

// Premium Styles
const styles = {
  container: {
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    backgroundColor: '#0F172A', // slate-900
    color: '#F8FAFC', // slate-50
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column' as const,
    boxSizing: 'border-box' as const,
    padding: '20px'
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    borderBottom: '1px solid #1E293B',
    paddingBottom: '16px',
    marginBottom: '20px'
  },
  logoCircle: {
    width: '40px',
    height: '40px',
    borderRadius: '10px',
    background: 'linear-gradient(135deg, #6366F1 0%, #4F46E5 100%)', // indigo
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontWeight: 'bold',
    fontSize: '20px',
    color: '#FFF',
    boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)'
  },
  title: {
    fontSize: '16px',
    fontWeight: 700,
    margin: 0,
    letterSpacing: '0.5px'
  },
  subtitle: {
    fontSize: '11px',
    color: '#94A3B8', // slate-400
    margin: 0
  },
  main: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column' as const
  },
  fadeContainer: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '12px'
  },
  label: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#CBD5E1', // slate-300
    marginBottom: '4px'
  },
  textarea: {
    height: '160px',
    backgroundColor: '#1E293B', // slate-800
    border: '1px solid #334155', // slate-700
    borderRadius: '8px',
    color: '#F8FAFC',
    padding: '12px',
    fontSize: '13px',
    resize: 'none' as const,
    outline: 'none',
    transition: 'border-color 0.2s, box-shadow 0.2s',
    fontFamily: 'inherit',
    lineHeight: '1.5'
  },
  button: {
    background: 'linear-gradient(135deg, #6366F1 0%, #4F46E5 100%)',
    color: '#FFF',
    border: 'none',
    borderRadius: '8px',
    padding: '12px',
    fontWeight: 600,
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'transform 0.1s, opacity 0.2s',
    boxShadow: '0 4px 14px rgba(79, 70, 229, 0.4)'
  },
  buttonActive: {
    opacity: 1
  },
  buttonDisabled: {
    background: '#1E293B',
    color: '#64748B',
    cursor: 'not-allowed',
    boxShadow: 'none'
  },
  buttonSecondary: {
    background: '#1E293B',
    color: '#CBD5E1',
    border: '1px solid #334155',
    borderRadius: '8px',
    padding: '12px',
    fontWeight: 600,
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'background 0.2s'
  },
  stepperContainer: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    padding: '10px 0'
  },
  loaderLine: {
    width: '100%',
    height: '4px',
    backgroundColor: '#1E293B',
    borderRadius: '2px',
    overflow: 'hidden',
    marginBottom: '20px'
  },
  loaderProgress: {
    width: '40%',
    height: '100%',
    background: 'linear-gradient(90deg, #6366F1, #EC4899)',
    borderRadius: '2px',
    animation: 'sabLoader 1.5s infinite ease-in-out'
  },
  stageTitle: {
    fontSize: '16px',
    fontWeight: 700,
    margin: '0 0 6px 0',
    color: '#FFF'
  },
  stageDesc: {
    fontSize: '12px',
    color: '#94A3B8',
    textAlign: 'center' as const,
    margin: '0 0 24px 0',
    lineHeight: '1.5'
  },
  stepsWrapper: {
    width: '100%',
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '12px',
    backgroundColor: '#1E293B',
    borderRadius: '12px',
    padding: '16px',
    boxSizing: 'border-box' as const
  },
  stepRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px'
  },
  stepDot: {
    width: '24px',
    height: '24px',
    borderRadius: '50%',
    backgroundColor: '#0F172A',
    border: '1px solid #334155',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '11px',
    color: '#64748B',
    fontWeight: 600
  },
  stepDotActive: {
    borderColor: '#6366F1',
    color: '#6366F1',
    boxShadow: '0 0 8px rgba(99, 102, 241, 0.4)'
  },
  stepDotDone: {
    backgroundColor: '#6366F1',
    borderColor: '#6366F1',
    color: '#FFF'
  },
  stepText: {
    fontSize: '11px',
    fontWeight: 700,
    color: '#64748B',
    letterSpacing: '0.5px'
  },
  stepTextActive: {
    color: '#6366F1'
  },
  stepTextDone: {
    color: '#CBD5E1'
  },
  successCard: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    backgroundColor: '#064E3B', // dark green
    border: '1px solid #065F46',
    borderRadius: '12px',
    padding: '24px',
    textAlign: 'center' as const,
    gap: '16px'
  },
  successIcon: {
    width: '48px',
    height: '48px',
    borderRadius: '50%',
    backgroundColor: '#059669',
    color: '#FFF',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '24px',
    fontWeight: 'bold'
  },
  successTitle: {
    fontSize: '18px',
    fontWeight: 700,
    margin: 0
  },
  successDesc: {
    fontSize: '12px',
    color: '#A7F3D0',
    margin: 0,
    lineHeight: '1.6'
  },
  errorCard: {
    display: 'flex',
    flexDirection: 'column' as const,
    backgroundColor: '#7F1D1D', // dark red
    border: '1px solid #991B1B',
    borderRadius: '12px',
    padding: '20px',
    gap: '14px'
  },
  errorIcon: {
    fontSize: '32px',
    margin: 0
  },
  errorTitle: {
    fontSize: '16px',
    fontWeight: 700,
    margin: 0
  },
  errorDesc: {
    fontSize: '12px',
    color: '#FCA5A5',
    margin: 0,
    lineHeight: '1.5',
    wordBreak: 'break-word' as const
  },
  errorActions: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '8px',
    marginTop: '6px'
  }
};

// Add standard keyframe style to the document head
if (typeof document !== 'undefined') {
  const styleEl = document.createElement('style');
  styleEl.innerHTML = `
    @keyframes sabLoader {
      0% { transform: translateX(-150%); }
      50% { transform: translateX(150%); }
      100% { transform: translateX(-150%); }
    }
  `;
  document.head.appendChild(styleEl);
}

// Initialise React Root inside Office.onReady callback
Office.onReady(() => {
  const container = document.getElementById('root');
  if (container) {
    const root = createRoot(container);
    root.render(<TaskPane />);
  }
});
