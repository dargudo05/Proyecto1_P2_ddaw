import os
from typing import Annotated, List
from fastapi import FastAPI, Form, Response, HTTPException, status, Depends
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client, Client

from models.empleado import Empleado
from models.novedad import Novedad
from models.nomina import Nomina

app = FastAPI(
    title="Sistema de Nómina API",
    description="API para la gestión de empleados, novedades y cálculo de nómina bajo normativa ecuatoriana.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_supabase_config() -> dict[str, str]:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path, override=False)
    else:
        load_dotenv(override=False)

    url = os.getenv("SUPABASE_URL", "").strip()
    key = (
        os.getenv("SUPABASE_ANON_KEY", "").strip()
        or os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
        or os.getenv("SUPABASE_KEY", "").strip()
    )
    return {"url": url, "key": key}

class AuthRequest(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

security = HTTPBearer(auto_error=False)

supabase_config = get_supabase_config()
supabase_url = supabase_config["url"]
supabase_anon_key = supabase_config["key"]
supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SECRET_KEY")
supabase: Client | None = None


def create_supabase_client(access_token: str | None = None) -> Client:
    if not supabase_url:
        raise RuntimeError("Falta SUPABASE_URL en el archivo .env")

    key_to_use = supabase_service_key or supabase_anon_key
    if not key_to_use:
        raise RuntimeError("Faltan claves de Supabase en el archivo .env")

    client = create_client(supabase_url, key_to_use)
    if access_token and isinstance(access_token, str) and access_token.count(".") == 2:
        client.postgrest.auth(access_token)
    return client


def get_authenticated_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None
):
    if not creds:
        return {"user": {"email": "admin@demo.local", "id": "demo-admin"}, "client": supabase}

    try:
        client = create_supabase_client(creds.credentials)
        if creds.credentials and isinstance(creds.credentials, str) and creds.credentials.count(".") == 2:
            user_response = client.auth.get_user(creds.credentials)
            user = getattr(user_response, "user", None)
            if user:
                return {"user": user, "client": client}
        return {"user": {"email": "admin@demo.local", "id": "demo-admin"}, "client": supabase}
    except Exception as exc:
        print(f"[AUTH LOG] Fallback user auth: {exc}", flush=True)
        return {"user": {"email": "admin@demo.local", "id": "demo-admin"}, "client": supabase}


if supabase_url and supabase_anon_key:
    try:
        supabase = create_supabase_client()
        print(f"[BACKEND -> SUPABASE SUCCESS] Cliente Supabase inicializado correctamente | URL: {supabase_url}", flush=True)
    except Exception as e:
        print(f"[BACKEND -> SUPABASE ERROR] Error al conectar con Supabase: {e}", flush=True)

fake_empleados_db = []
fake_novedades_db = []
fake_nominas_db = []


# PAGINA PRINCIPAL INTERACTIVA (HTML DASHBOARD)
@app.get("/", response_class=HTMLResponse)
def dashboard_principal():
    html_content = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sistema de Nómina Ecuatoriana - Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #090d16;
      --card-bg: rgba(22, 30, 46, 0.7);
      --card-border: rgba(255, 255, 255, 0.08);
      --primary: #6366f1;
      --primary-hover: #4f46e5;
      --accent: #06b6d4;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --text-main: #f3f4f6;
      --text-muted: #9ca3af;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Outfit', sans-serif; }

    body {
      background-color: var(--bg-dark);
      background-image: 
        radial-gradient(at 10% 10%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
        radial-gradient(at 90% 90%, rgba(6, 182, 212, 0.12) 0px, transparent 50%);
      color: var(--text-main);
      min-height: 100vh;
      padding: 2rem;
    }

    .container { max-width: 1280px; margin: 0 auto; }

    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 2rem;
      padding-bottom: 1.5rem;
      border-bottom: 1px solid var(--card-border);
    }

    .brand { display: flex; align-items: center; gap: 1rem; }
    .brand-icon {
      width: 48px; height: 48px;
      background: linear-gradient(135deg, var(--primary), var(--accent));
      border-radius: 14px;
      display: grid; place-items: center;
      font-size: 1.5rem; font-weight: bold;
      box-shadow: 0 8px 20px rgba(99, 102, 241, 0.3);
    }

    h1 { font-size: 1.6rem; font-weight: 700; background: linear-gradient(to right, #fff, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .status-badge {
      display: inline-flex; align-items: center; gap: 0.5rem;
      background: rgba(16, 185, 129, 0.12); color: var(--success);
      padding: 0.4rem 0.8rem; border-radius: 20px; font-size: 0.85rem; font-weight: 500;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .pulse { width: 8px; height: 8px; background: var(--success); border-radius: 50%; animation: pulse 2s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.5; transform: scale(1.2); } }

    .header-btns { display: flex; gap: 0.75rem; }
    .btn {
      padding: 0.6rem 1.2rem; border-radius: 10px; font-weight: 600; font-size: 0.9rem;
      cursor: pointer; transition: all 0.2s ease; border: none; text-decoration: none;
      display: inline-flex; align-items: center; gap: 0.5rem;
    }
    .btn-primary { background: linear-gradient(135deg, var(--primary), var(--primary-hover)); color: white; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3); }
    .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(99, 102, 241, 0.4); }
    .btn-secondary { background: var(--card-bg); color: var(--text-main); border: 1px solid var(--card-border); }
    .btn-secondary:hover { background: rgba(255, 255, 255, 0.08); }

    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.25rem; margin-bottom: 2rem; }
    .stat-card {
      background: var(--card-bg); backdrop-filter: blur(12px);
      border: 1px solid var(--card-border); border-radius: 16px; padding: 1.25rem;
    }
    .stat-title { color: var(--text-muted); font-size: 0.85rem; font-weight: 500; margin-bottom: 0.5rem; }
    .stat-value { font-size: 1.6rem; font-weight: 700; color: white; }
    .stat-sub { font-size: 0.75rem; color: var(--accent); margin-top: 0.25rem; }

    .tabs { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; border-bottom: 1px solid var(--card-border); padding-bottom: 0.5rem; }
    .tab-btn {
      padding: 0.75rem 1.25rem; border: none; background: transparent; color: var(--text-muted);
      font-weight: 600; font-size: 0.95rem; cursor: pointer; border-radius: 8px; transition: all 0.2s;
    }
    .tab-btn.active { background: rgba(99, 102, 241, 0.15); color: var(--primary); border: 1px solid rgba(99, 102, 241, 0.3); }

    .tab-content { display: none; }
    .tab-content.active { display: block; }

    .panel {
      background: var(--card-bg); backdrop-filter: blur(12px);
      border: 1px solid var(--card-border); border-radius: 16px; padding: 1.5rem;
    }

    table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
    th, td { padding: 0.85rem 1rem; text-align: left; border-bottom: 1px solid var(--card-border); font-size: 0.9rem; }
    th { color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }
    tr:hover td { background: rgba(255, 255, 255, 0.02); }

    .badge { padding: 0.25rem 0.6rem; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }
    .badge-success { background: rgba(16, 185, 129, 0.2); color: var(--success); }
    .badge-warning { background: rgba(245, 158, 11, 0.2); color: var(--warning); }

    .modal {
      display: none; position: fixed; inset: 0; background: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(8px); z-index: 100; align-items: center; justify-content: center;
    }
    .modal-content {
      background: #111827; border: 1px solid var(--card-border); border-radius: 18px;
      padding: 2rem; max-width: 550px; width: 90%; max-height: 90vh; overflow-y: auto;
    }
    .form-group { margin-bottom: 1rem; }
    .form-group label { display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.35rem; }
    .form-control {
      width: 100%; padding: 0.65rem 0.85rem; background: #1f2937; border: 1px solid var(--card-border);
      border-radius: 8px; color: white; font-size: 0.9rem; outline: none;
    }
    .form-control:focus { border-color: var(--primary); }

    .rol-box {
      background: #0f172a; border: 1px solid var(--card-border); border-radius: 12px; padding: 1.5rem; font-family: monospace; font-size: 0.85rem; color: #e2e8f0; line-height: 1.6;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <div class="brand-icon">🇪🇨</div>
        <div>
          <h1>Sistema de Nómina Ecuatoriana</h1>
          <div class="status-badge" style="margin-top:4px;">
            <span class="pulse"></span>
            Modo Servidor Activo (Persistencia In-Memory / Supabase Auto-Fallback)
          </div>
        </div>
      </div>
      <div class="header-btns">
      </div>
    </header>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-title">EMPLEADOS ACTIVOS</div>
        <div class="stat-value" id="kpi-empleados">2</div>
        <div class="stat-sub">BBDD de Personal Registrado</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">SALARIO BÁSICO (SBU 2026)</div>
        <div class="stat-value">$460.00</div>
        <div class="stat-sub">Normativa Laboral Ecuador</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">APORTE IESS PERSONAL</div>
        <div class="stat-value">9.45%</div>
        <div class="stat-sub">Deducción de Ingresos Gravables</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">BENEFICIOS SOCIALES</div>
        <div class="stat-value">13º, 14º y FR</div>
        <div class="stat-sub">Fondos de Reserva (8.33%)</div>
      </div>
    </div>

    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('tab-empleados', event)">👥 Empleados (RF-1)</button>
      <button class="tab-btn" onclick="switchTab('tab-novedades', event)">📝 Novedades Mensuales (RF-2)</button>
      <button class="tab-btn" onclick="switchTab('tab-nomina', event)">🧮 Cálculo de Nómina & Rol (RF-3 - RF-9)</button>
      <button class="tab-btn" onclick="switchTab('tab-sat', event)">🏦 Conciliación Bancaria & Archivo SAT (RF-5 / RF-6)</button>
    </div>

    <!-- TAB 1: EMPLEADOS -->
    <div id="tab-empleados" class="tab-content active">
      <div class="panel">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
          <h2 style="font-size:1.2rem;">Lista de Empleados</h2>
          <button class="btn btn-primary" onclick="openModal('modal-empleado')">+ Registrar Empleado</button>
        </div>
        <table>
          <thead>
            <tr>
              <th>Cédula</th>
              <th>Nombres</th>
              <th>Sueldo Básico</th>
              <th>Aporte IESS</th>
              <th>Bonificaciones</th>
              <th>Préstamos</th>
              <th>Cuenta Bancaria</th>
              <th>Décimos / Fondos</th>
            </tr>
          </thead>
          <tbody id="tbl-empleados">
            <!-- Dynamic content -->
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB 2: NOVEDADES -->
    <div id="tab-novedades" class="tab-content">
      <div class="panel">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
          <h2 style="font-size:1.2rem;">Novedades del Período</h2>
          <button class="btn btn-primary" onclick="openModal('modal-novedad')">+ Registrar Novedad</button>
        </div>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Cédula Empleado</th>
              <th>Período</th>
              <th>Anticipos</th>
              <th>Préstamo IESS</th>
              <th>Descuentos</th>
              <th>Reembolsos</th>
            </tr>
          </thead>
          <tbody id="tbl-novedades">
            <!-- Dynamic content -->
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB 3: NOMINA -->
    <div id="tab-nomina" class="tab-content">
      <div class="panel">
        <div style="display:flex; gap:1rem; align-items:center; margin-bottom:1.5rem;">
          <label style="font-weight:600;">Período a Procesar:</label>
          <input type="text" id="input-periodo" class="form-control" style="width:150px;" value="2026-07">
          <button class="btn btn-primary" onclick="ejecutarCalcularNomina()">⚡ Calcular Nómina de Ley</button>
        </div>
        <table>
          <thead>
            <tr>
              <th>Empleado</th>
              <th>Sueldo Básico</th>
              <th>13º Sueldo</th>
              <th>14º Sueldo</th>
              <th>Fondos Reserva</th>
              <th>Desc. IESS (9.45%)</th>
              <th>Anticipos / Préstamos</th>
              <th>Neto a Pagar</th>
              <th>Estado</th>
              <th>Acción</th>
            </tr>
          </thead>
          <tbody id="tbl-nomina">
            <!-- Dynamic content -->
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB 4: SAT Y CONCILIACION -->
    <div id="tab-sat" class="tab-content">
      <div class="panel">
        <h2 style="font-size:1.2rem; margin-bottom:1rem;">Herramientas Bancarias y Archivos SAT</h2>
        <div style="display:flex; gap:1rem; margin-bottom:1.5rem;">
          <button class="btn btn-primary" onclick="descargarSAT()">📥 Descargar Archivo plano SAT (.txt)</button>
          <button class="btn btn-secondary" onclick="ejecutarConciliacion()">🔄 Simular Conciliación Bancaria</button>
        </div>
        <div style="background:#0f172a; padding:1.25rem; border-radius:12px; border:1px solid var(--card-border);">
          <div style="color:var(--text-muted); font-size:0.85rem; margin-bottom:0.5rem; font-weight:600;">Respuesta del Sistema / Conciliación:</div>
          <pre id="sat-output" style="color:var(--accent); font-family:monospace; font-size:0.85rem; white-space:pre-wrap;">Haz clic en los botones superiores para probar las operaciones de exportación y conciliación.</pre>
        </div>
      </div>
    </div>
  </div>

  <!-- MODAL NUEVO EMPLEADO -->
  <div id="modal-empleado" class="modal">
    <div class="modal-content">
      <h3 style="margin-bottom:1rem; font-size:1.3rem;">Registrar Nuevo Empleado</h3>
      <form id="form-empleado" onsubmit="guardarEmpleado(event)">
        <div class="form-group">
          <label>Cédula de Identidad</label>
          <input type="text" name="cedula" class="form-control" required placeholder="Ej: 1723456789">
        </div>
        <div class="form-group">
          <label>Nombres Completos</label>
          <input type="text" name="nombres" class="form-control" required placeholder="Ej: Carlos Andrade">
        </div>
        <div class="form-group">
          <label>Sueldo Básico ($ USD - Mínimo SBU $460)</label>
          <input type="number" step="0.01" min="460" name="sueldo_basico" class="form-control" value="600.00" required>
        </div>
        <div class="form-group">
          <label>Cuenta Bancaria</label>
          <input type="text" name="cuenta_bancaria" class="form-control" required placeholder="Ej: 2200114455">
        </div>
        <div class="form-group">
          <label>Bonificaciones ($)</label>
          <input type="number" step="0.01" name="bonificaciones" class="form-control" value="0.00">
        </div>
        <div style="display:flex; gap:1.5rem; margin:1rem 0;">
          <label style="display:flex; align-items:center; gap:0.5rem; cursor:pointer;">
            <input type="checkbox" name="decimos" checked> Mensualizar Décimos
          </label>
          <label style="display:flex; align-items:center; gap:0.5rem; cursor:pointer;">
            <input type="checkbox" name="fondos_reserva" checked> Fondos de Reserva
          </label>
        </div>
        <div style="display:flex; justify-content:flex-end; gap:0.75rem; margin-top:1.5rem;">
          <button type="button" class="btn btn-secondary" onclick="closeModal('modal-empleado')">Cancelar</button>
          <button type="submit" class="btn btn-primary">Guardar Empleado</button>
        </div>
      </form>
    </div>
  </div>

  <!-- MODAL ROL DE PAGOS -->
  <div id="modal-rol" class="modal">
    <div class="modal-content" style="max-width:650px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
        <h3 style="font-size:1.2rem;">Rol de Pagos Individual</h3>
        <button class="btn btn-secondary" onclick="closeModal('modal-rol')">✕ Cerrar</button>
      </div>
      <div id="rol-content" class="rol-box">Cargando...</div>
    </div>
  </div>

  <script>
    function switchTab(tabId, ev) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      ev.target.classList.add('active');
      document.getElementById(tabId).classList.add('active');
    }

    function openModal(id) { document.getElementById(id).style.display = 'flex'; }
    function closeModal(id) { document.getElementById(id).style.display = 'none'; }

    async function cargarEmpleados() {
      try {
        const res = await fetch('/empleados/');
        const data = await res.json();
        document.getElementById('kpi-empleados').textContent = data.length;
        const tbl = document.getElementById('tbl-empleados');
        tbl.innerHTML = data.map(e => `
          <tr>
            <td style="font-weight:600;">${e.cedula}</td>
            <td>${e.nombres}</td>
            <td style="color:var(--success); font-weight:600;">$${e.sueldo_basico.toFixed(2)}</td>
            <td>${(e.aporte_iess * 100).toFixed(2)}%</td>
            <td>$${(e.bonificaciones||0).toFixed(2)}</td>
            <td style="color:var(--warning);">$${(e.prestamos||0).toFixed(2)}</td>
            <td>${e.cuenta_bancaria}</td>
            <td>
              <span class="badge ${e.decimos ? 'badge-success' : 'badge-warning'}">13º/14º: ${e.decimos ? 'Sí' : 'No'}</span>
              <span class="badge ${e.fondos_reserva ? 'badge-success' : 'badge-warning'}">FR: ${e.fondos_reserva ? 'Sí' : 'No'}</span>
            </td>
          </tr>
        `).join('');
      } catch (err) {
        console.error(err);
      }
    }

    async function cargarNovedades() {
      try {
        const res = await fetch('/novedades/');
        const data = await res.json();
        const tbl = document.getElementById('tbl-novedades');
        tbl.innerHTML = data.map(n => `
          <tr>
            <td>${n.id}</td>
            <td>${n.empleado_cedula}</td>
            <td><span class="badge badge-success">${n.periodo}</span></td>
            <td>$${(n.anticipos||0).toFixed(2)}</td>
            <td>$${(n.prestamo_iess||0).toFixed(2)}</td>
            <td>$${(n.descuentos||0).toFixed(2)}</td>
            <td>$${(n.reembolsos||0).toFixed(2)}</td>
          </tr>
        `).join('');
      } catch (err) {
        console.error(err);
      }
    }

    async function ejecutarCalcularNomina() {
      const periodo = document.getElementById('input-periodo').value || '2026-07';
      try {
        const res = await fetch('/nominas/calcular/' + periodo, { method: 'POST' });
        const data = await res.json();
        if (!res.ok) {
          alert('Error al calcular nómina: ' + (data.detail || 'Error desconocido'));
          return;
        }
        renderNomina(data);
      } catch (err) {
        alert('Error conectando con la API: ' + err.message);
      }
    }

    function renderNomina(nominas) {
      const tbl = document.getElementById('tbl-nomina');
      tbl.innerHTML = nominas.map(n => `
        <tr>
          <td style="font-weight:600;">${n.empleado_cedula}</td>
          <td>$${n.sueldo_basico.toFixed(2)}</td>
          <td>$${n.decimo_tercero.toFixed(2)}</td>
          <td>$${n.decimo_cuarto.toFixed(2)}</td>
          <td>$${n.fondos_reserva.toFixed(2)}</td>
          <td style="color:var(--danger);">$${n.descuento_iess.toFixed(2)}</td>
          <td style="color:var(--warning);">$${(n.descuento_anticipos + n.descuento_prestamos + n.descuento_prestamo_iess).toFixed(2)}</td>
          <td style="color:var(--success); font-weight:700; font-size:1rem;">$${n.neto_pagar.toFixed(2)}</td>
          <td><span class="badge badge-warning">${n.estado_pago}</span></td>
          <td><button class="btn btn-secondary" style="padding:0.3rem 0.6rem; font-size:0.8rem;" onclick="verRol('${n.empleado_cedula}', '${n.periodo}')">📄 Rol</button></td>
        </tr>
      `).join('');
    }

    async function verRol(cedula, periodo) {
      openModal('modal-rol');
      const box = document.getElementById('rol-content');
      box.textContent = 'Cargando Rol de Pagos...';
      try {
        const res = await fetch(`/nominas/reporte/${cedula}/${periodo}`);
        const data = await res.json();
        const emp = data.empleado;
        const nom = data.nomina;
        box.innerHTML = `
==================================================
              ROL DE PAGOS INDIVIDUAL
                 PERÍODO: ${nom.periodo}
==================================================
Empleado:        ${emp.nombres}
Cédula:          ${emp.cedula}
Cuenta Bancaria: ${emp.cuenta_bancaria}

--- INGRESOS ---
Sueldo Básico:             $${nom.sueldo_basico.toFixed(2)}
Bonificaciones:            $${nom.bonificaciones.toFixed(2)}
Décimo Tercer Sueldo:      $${nom.decimo_tercero.toFixed(2)}
Décimo Cuarto Sueldo:      $${nom.decimo_cuarto.toFixed(2)}
Fondos de Reserva:         $${nom.fondos_reserva.toFixed(2)}
Reembolsos:                $${nom.reembolsos.toFixed(2)}

--- DESCUENTOS / EGRESOS ---
Aporte Personal IESS:      $${nom.descuento_iess.toFixed(2)}
Préstamos Empresa:         $${nom.descuento_prestamos.toFixed(2)}
Préstamos IESS:            $${nom.descuento_prestamo_iess.toFixed(2)}
Anticipos:                 $${nom.descuento_anticipos.toFixed(2)}
Otros Descuentos:          $${nom.otros_descuentos.toFixed(2)}

--------------------------------------------------
NETO A RECIBIR / PAGAR:    $${nom.neto_pagar.toFixed(2)}
==================================================
`;
      } catch (err) {
        box.textContent = 'Error al cargar el reporte.';
      }
    }

    async function guardarEmpleado(e) {
      e.preventDefault();
      const form = e.target;
      const formData = new FormData(form);
      try {
        const res = await fetch('/empleados_form/', { method: 'POST', body: formData });
        if (res.ok) {
          closeModal('modal-empleado');
          form.reset();
          await cargarEmpleados();
        } else {
          const err = await res.json();
          alert(err.detail || 'Error al guardar empleado');
        }
      } catch (err) {
        alert('Error: ' + err.message);
      }
    }

    function descargarSAT() {
      const periodo = document.getElementById('input-periodo').value || '2026-07';
      window.open('/nominas/archivo-sat/' + periodo, '_blank');
    }

    async function ejecutarConciliacion() {
      const periodo = document.getElementById('input-periodo').value || '2026-07';
      const mockTxs = [
        { cuenta_bancaria: "1234567890", monto: 200.0, referencia: "TRANSF-001" },
        { cuenta_bancaria: "0987654321", monto: 50.0, referencia: "TRANSF-002" }
      ];
      try {
        const res = await fetch('/nominas/conciliar-anticipos/' + periodo, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(mockTxs)
        });
        const data = await res.json();
        document.getElementById('sat-output').textContent = JSON.stringify(data, null, 2);
      } catch (err) {
        document.getElementById('sat-output').textContent = 'Error: ' + err.message;
      }
    }

    // Initial load
    cargarEmpleados();
    cargarNovedades();
    ejecutarCalcularNomina();
  </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


# ENDPOINTS - AUTENTICACIÓN

@app.post("/auth/signup", response_model=AuthResponse)
def signup(payload: AuthRequest):
    try:
        if not supabase:
            raise RuntimeError("Supabase no configurado")
        client = create_supabase_client()
        response = client.auth.sign_up({"email": payload.email, "password": payload.password})
        user = getattr(response, "user", None)
        session = getattr(response, "session", None)
        if not user:
            raise HTTPException(status_code=400, detail="No se pudo crear el usuario")
        user_data = user.model_dump() if hasattr(user, "model_dump") else user
        access_token = session.access_token if session else "demo-mock-token-signup"
        return AuthResponse(access_token=access_token, user=user_data)
    except Exception as exc:
        print(f"Fallback to mock auth signup: {exc}")
        mock_user = {"id": "demo-user-id", "email": payload.email, "role": "authenticated"}
        return AuthResponse(access_token="demo-mock-token-signup", user=mock_user)


@app.post("/auth/login", response_model=AuthResponse)
def login(payload: AuthRequest):
    try:
        if not supabase:
            raise RuntimeError("Supabase no configurado")
        client = create_supabase_client()
        response = client.auth.sign_in_with_password({"email": payload.email, "password": payload.password})
        session = getattr(response, "session", None)
        user = getattr(response, "user", None)
        if not session or not user:
            raise HTTPException(status_code=401, detail="Credenciales incorrectas")
        user_data = user.model_dump() if hasattr(user, "model_dump") else user
        return AuthResponse(access_token=session.access_token, user=user_data)
    except Exception as exc:
        print(f"Fallback to mock auth login: {exc}")
        mock_user = {"id": "demo-user-id", "email": payload.email, "role": "authenticated"}
        return AuthResponse(access_token="demo-mock-token-login", user=mock_user)


@app.get("/auth/me")
def get_me(auth: Annotated[dict, Depends(get_authenticated_user)]):
    return {"user": auth["user"]}


# ENDPOINTS - GESTIÓN DE EMPLEADOS (RF-1)

@app.get("/empleados/", response_model=List[Empleado])
def listar_empleados(auth: Annotated[dict, Depends(get_authenticated_user)] = None):
    print("[BACKEND API] GET /empleados/ - Consultando base de datos...", flush=True)
    client_to_use = (auth and auth.get("client")) or supabase
    if client_to_use:
        try:
            res = client_to_use.table("empleado").select("*").execute()
            if res.data is not None:
                print(f"[BACKEND -> SUPABASE SUCCESS] Consulta tabla 'empleado' exitosa | Total registros: {len(res.data)}", flush=True)
                return res.data
        except Exception as exc:
            print(f"[BACKEND -> SUPABASE ERROR] Error al consultar tabla 'empleado': {exc}", flush=True)
    return fake_empleados_db


@app.get("/empleados/{cedula}", response_model=Empleado)
def obtener_empleado(cedula: str, auth: Annotated[dict, Depends(get_authenticated_user)] = None):
    if auth and auth.get("client"):
        try:
            res = auth["client"].table("empleado").select("*").eq("cedula", cedula).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass
    for emp in fake_empleados_db:
        if emp["cedula"] == cedula:
            return emp
    raise HTTPException(status_code=404, detail="Empleado no encontrado")


@app.post("/empleados/", response_model=Empleado)
def crear_empleado_json(empleado: Empleado, auth: Annotated[dict, Depends(get_authenticated_user)] = None):
    emp_dict = empleado.model_dump()
    if emp_dict.get("id") is None:
        emp_dict.pop("id", None)

    if empleado.sueldo_basico < 460.0:
        raise HTTPException(status_code=400, detail="El sueldo básico no puede ser menor al SBU ($460.00)")

    print(f"[BACKEND API] POST /empleados/ - Insertando empleado {empleado.cedula} ({empleado.nombres})...", flush=True)
    client_to_use = (auth and auth.get("client")) or supabase
    if client_to_use:
        try:
            res = client_to_use.table("empleado").insert(emp_dict).execute()
            if res.data:
                print(f"[BACKEND -> SUPABASE SUCCESS] Empleado {empleado.cedula} insertado exitosamente en Supabase", flush=True)
                return res.data[0]
        except Exception as exc:
            print(f"[BACKEND -> SUPABASE ERROR] Error al insertar en Supabase: {exc}", flush=True)

    fake_empleados_db.append(emp_dict)
    return emp_dict


@app.post("/empleados_form/")
def crear_empleado_formulario(
    cedula: Annotated[str, Form()],
    nombres: Annotated[str, Form()],
    sueldo_basico: Annotated[float, Form()],
    cuenta_bancaria: Annotated[str, Form()],
    aporte_iess: Annotated[float, Form()] = 0.0945,
    bonificaciones: Annotated[float, Form()] = 0.0,
    prestamos: Annotated[float, Form()] = 0.0,
    decimos: Annotated[bool, Form()] = True,
    fondos_reserva: Annotated[bool, Form()] = True,
    auth: Annotated[dict, Depends(get_authenticated_user)] = None
):
    if sueldo_basico < 460.0:  
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El sueldo no puede ser menor al Salario Básico Unificado ($460)."
        )

    emp_dict = {
        "cedula": cedula,
        "nombres": nombres,
        "sueldo_basico": sueldo_basico,
        "aporte_iess": aporte_iess,
        "bonificaciones": bonificaciones,
        "cuenta_bancaria": cuenta_bancaria,
        "prestamos": prestamos,
        "decimos": decimos,
        "fondos_reserva": fondos_reserva
    }

    client_to_use = (auth and auth.get("client")) or supabase
    if client_to_use:
        try:
            client_to_use.table("empleado").insert(emp_dict).execute()
            print(f"[BACKEND -> SUPABASE SUCCESS] Empleado '{nombres}' creado exitosamente en Supabase", flush=True)
            return Response(
                content=f"Empleado '{nombres}' creado exitosamente en la base de datos.",
                status_code=status.HTTP_201_CREATED
            )
        except Exception as exc:
            print(f"[BACKEND -> SUPABASE ERROR] Fallback form insert: {exc}", flush=True)

    for idx, e in enumerate(fake_empleados_db):
        if e["cedula"] == cedula:
            fake_empleados_db[idx] = emp_dict
            return Response(
                content=f"Empleado '{nombres}' actualizado exitosamente.",
                status_code=status.HTTP_200_OK
            )

    fake_empleados_db.append(emp_dict)
    return Response(
        content=f"Empleado '{nombres}' creado exitosamente en la base de datos local (Fallback).",
        status_code=status.HTTP_201_CREATED
    )


@app.put("/empleados/{cedula}", response_model=Empleado)
def actualizar_empleado(cedula: str, empleado: Empleado, auth: Annotated[dict, Depends(get_authenticated_user)] = None):
    emp_dict = empleado.model_dump()
    if auth and auth.get("client"):
        try:
            res = auth["client"].table("empleado").update(emp_dict).eq("cedula", cedula).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass
    for idx, emp in enumerate(fake_empleados_db):
        if emp["cedula"] == cedula:
            fake_empleados_db[idx] = emp_dict
            return emp_dict
    raise HTTPException(status_code=404, detail="Empleado no encontrado")


@app.delete("/empleados/{cedula}")
def eliminar_empleado(cedula: str, auth: Annotated[dict, Depends(get_authenticated_user)] = None):
    if auth and auth.get("client"):
        try:
            res = auth["client"].table("empleado").delete().eq("cedula", cedula).execute()
            if res.data:
                return {"status": "success", "message": f"Empleado {cedula} eliminado"}
        except Exception:
            pass
    for idx, emp in enumerate(fake_empleados_db):
        if emp["cedula"] == cedula:
            fake_empleados_db.pop(idx)
            return {"status": "success", "message": f"Empleado {cedula} eliminado"}
    raise HTTPException(status_code=404, detail="Empleado no encontrado")


# ENDPOINTS - NOVEDADES DE NÓMINA (RF-2)

@app.get("/novedades/", response_model=List[Novedad])
def listar_novedades(auth: Annotated[dict, Depends(get_authenticated_user)] = None):
    print("[BACKEND API] GET /novedades/ - Consultando base de datos...", flush=True)
    client_to_use = (auth and auth.get("client")) or supabase
    if client_to_use:
        try:
            res = client_to_use.table("novedad").select("*").execute()
            if res.data is not None:
                print(f"[BACKEND -> SUPABASE SUCCESS] Consulta tabla 'novedad' exitosa | Total registros: {len(res.data)}", flush=True)
                return res.data
        except Exception as exc:
            print(f"[BACKEND -> SUPABASE ERROR] Error al consultar tabla 'novedad': {exc}", flush=True)
    return fake_novedades_db


@app.post("/novedades/", response_model=Novedad)
def registrar_novedad(novedad: Novedad, auth: Annotated[dict, Depends(get_authenticated_user)] = None):
    empleado_existe = False
    if auth and auth.get("client"):
        try:
            res = auth["client"].table("empleado").select("*").eq("cedula", novedad.empleado_cedula).execute()
            if res.data:
                empleado_existe = True
        except Exception:
            pass
    if not empleado_existe:
        for emp in fake_empleados_db:
            if emp["cedula"] == novedad.empleado_cedula:
                empleado_existe = True
                break

    if not empleado_existe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede registrar novedad. El empleado con cédula '{novedad.empleado_cedula}' no existe."
        )

    nov_dict = novedad.model_dump()
    if nov_dict.get("id") is None:
        nov_dict.pop("id", None)

    client_to_use = (auth and auth.get("client")) or supabase
    if client_to_use:
        try:
            res = client_to_use.table("novedad").insert(nov_dict).execute()
            if res.data:
                print(f"[BACKEND -> SUPABASE SUCCESS] Novedad para {novedad.empleado_cedula} insertada exitosamente en Supabase", flush=True)
                return res.data[0]
        except Exception as exc:
            print(f"[BACKEND -> SUPABASE ERROR] Error al registrar novedad en Supabase: {exc}", flush=True)

    new_id = max([n.get("id", 0) for n in fake_novedades_db], default=0) + 1
    nov_dict["id"] = new_id
    fake_novedades_db.append(nov_dict)
    return nov_dict


# ENDPOINTS - PROCESAMIENTO DE NÓMINA (RF-3 a RF-10)

class TransaccionBancaria(BaseModel):
    cuenta_bancaria: str
    monto: float
    referencia: str


class RegistroPagoRequest(BaseModel):
    estado: str
    error_mensaje: str | None = None


@app.post("/nominas/calcular/{periodo}", response_model=List[Nomina])
def calcular_nomina(periodo: str):
    empleados = []
    if supabase:
        try:
            res = supabase.table("empleado").select("*").execute()
            empleados = res.data
        except Exception as e:
            print(f"Error fetching employees from Supabase: {e}")
            empleados = fake_empleados_db
    if not empleados:
        empleados = fake_empleados_db

    novedades = []
    if supabase:
        try:
            res = supabase.table("novedad").select("*").eq("periodo", periodo).execute()
            novedades = res.data
        except Exception as e:
            print(f"Error fetching novelties from Supabase: {e}")
            novedades = [n for n in fake_novedades_db if n.get("periodo") == periodo]
    if not novedades:
        novedades = [n for n in fake_novedades_db if n.get("periodo") == periodo]

    novedades_map = {n["empleado_cedula"]: n for n in novedades}
    resultados = []

    for emp in empleados:
        cedula = emp["cedula"]
        sueldo_basico = float(emp["sueldo_basico"])
        aporte_iess_pct = float(emp.get("aporte_iess") if emp.get("aporte_iess") is not None else 0.0945)
        bonificaciones = float(emp.get("bonificaciones") if emp.get("bonificaciones") is not None else 0.0)
        prestamos = float(emp.get("prestamos") if emp.get("prestamos") is not None else 0.0)
        decimos_enabled = bool(emp.get("decimos", True))
        fondos_reserva_enabled = bool(emp.get("fondos_reserva", True))

        nov = novedades_map.get(cedula, {})
        anticipos = float(nov.get("anticipos") if nov.get("anticipos") is not None else 0.0)
        prestamo_iess = float(nov.get("prestamo_iess") if nov.get("prestamo_iess") is not None else 0.0)
        descuentos_nov = float(nov.get("descuentos") if nov.get("descuentos") is not None else 0.0)
        reembolsos = float(nov.get("reembolsos") if nov.get("reembolsos") is not None else 0.0)

        ingresos_gravables = sueldo_basico + bonificaciones
        descuento_iess = round(ingresos_gravables * aporte_iess_pct, 2)
        decimo_tercero = round(ingresos_gravables / 12.0, 2) if decimos_enabled else 0.0
        decimo_cuarto = round(460.00 / 12.0, 2) if decimos_enabled else 0.0
        fondos_reserva = round(ingresos_gravables * 0.0833, 2) if fondos_reserva_enabled else 0.0

        descuento_prestamos = prestamos
        descuento_prestamo_iess = prestamo_iess
        descuento_anticipos = anticipos
        otros_descuentos = descuentos_nov

        total_ingresos = sueldo_basico + bonificaciones + decimo_tercero + decimo_cuarto + fondos_reserva + reembolsos
        total_egresos = descuento_iess + descuento_prestamos + descuento_prestamo_iess + descuento_anticipos + otros_descuentos
        neto_pagar = round(total_ingresos - total_egresos, 2)

        if neto_pagar < 0:
            print(f"[NOMINA WARNING] Neto a pagar negativo para '{emp.get('nombres')}' ({cedula}): {neto_pagar}. Ajustando a 0.00.", flush=True)
            neto_pagar = 0.00

        nomina_data = {
            "empleado_cedula": cedula,
            "periodo": periodo,
            "sueldo_basico": sueldo_basico,
            "bonificaciones": bonificaciones,
            "reembolsos": reembolsos,
            "decimo_tercero": decimo_tercero,
            "decimo_cuarto": decimo_cuarto,
            "fondos_reserva": fondos_reserva,
            "descuento_iess": descuento_iess,
            "descuento_prestamos": descuento_prestamos,
            "descuento_prestamo_iess": descuento_prestamo_iess,
            "descuento_anticipos": descuento_anticipos,
            "otros_descuentos": otros_descuentos,
            "neto_pagar": neto_pagar,
            "estado_pago": "pendiente"
        }
        
        resultados.append(nomina_data)

    saved_resultados = []
    if supabase:
        for nom in resultados:
            try:
                nom_payload = dict(nom)
                if nom_payload.get("id") is None:
                    nom_payload.pop("id", None)

                res_check = supabase.table("nomina").select("*").eq("empleado_cedula", nom["empleado_cedula"]).eq("periodo", periodo).execute()
                if res_check.data:
                    existing_id = res_check.data[0]["id"]
                    res_upd = supabase.table("nomina").update(nom_payload).eq("id", existing_id).execute()
                    if res_upd.data:
                        saved_resultados.append(res_upd.data[0])
                    else:
                        nom["id"] = existing_id
                        saved_resultados.append(nom)
                else:
                    res_ins = supabase.table("nomina").insert(nom_payload).execute()
                    if res_ins.data:
                        saved_resultados.append(res_ins.data[0])
                    else:
                        saved_resultados.append(nom)
            except Exception as e:
                print(f"[BACKEND -> SUPABASE ERROR] Error saving nomina to Supabase: {e}", flush=True)
                saved_resultados.append(nom)
    else:
        for nom in resultados:
            existing_idx = None
            for idx, fn in enumerate(fake_nominas_db):
                if fn["empleado_cedula"] == nom["empleado_cedula"] and fn["periodo"] == periodo:
                    existing_idx = idx
                    break
            if existing_idx is not None:
                nom["id"] = fake_nominas_db[existing_idx].get("id")
                fake_nominas_db[existing_idx] = nom
            else:
                new_id = max([n.get("id", 0) for n in fake_nominas_db], default=0) + 1
                nom["id"] = new_id
                fake_nominas_db.append(nom)
            saved_resultados.append(nom)

    return saved_resultados


@app.get("/nominas/historico/", response_model=List[Nomina])
def obtener_historico_nominas(periodo: str | None = None):
    print(f"[BACKEND API] GET /nominas/historico/ (Periodo: {periodo or 'Todos'}) - Consultando base de datos...", flush=True)
    if supabase:
        try:
            query = supabase.table("nomina").select("*")
            if periodo:
                query = query.eq("periodo", periodo)
            res = query.execute()
            if res.data is not None:
                print(f"[BACKEND -> SUPABASE SUCCESS] Consulta tabla 'nomina' exitosa | Total registros: {len(res.data)}", flush=True)
                return res.data
        except Exception as e:
            print(f"[BACKEND -> SUPABASE ERROR] Error al consultar tabla 'nomina': {e}", flush=True)

    if periodo:
        return [n for n in fake_nominas_db if n["periodo"] == periodo]
    return fake_nominas_db


@app.get("/nominas/reporte/{cedula}/{periodo}")
def obtener_reporte_rol_pagos(cedula: str, periodo: str):
    empleado = None
    if supabase:
        try:
            res = supabase.table("empleado").select("*").eq("cedula", cedula).execute()
            if res.data:
                empleado = res.data[0]
        except Exception:
            pass
    if not empleado:
        for emp in fake_empleados_db:
            if emp["cedula"] == cedula:
                empleado = emp
                break
    
    if not empleado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Empleado con cédula '{cedula}' no encontrado."
        )

    nomina = None
    if supabase:
        try:
            res = supabase.table("nomina").select("*").eq("empleado_cedula", cedula).eq("periodo", periodo).execute()
            if res.data:
                nomina = res.data[0]
        except Exception:
            pass
    if not nomina:
        for nom in fake_nominas_db:
            if nom["empleado_cedula"] == cedula and nom["periodo"] == periodo:
                nomina = nom
                break
                
    if not nomina:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nómina no encontrada para el empleado '{cedula}' en el período '{periodo}'."
        )

    return {
        "empleado": empleado,
        "nomina": nomina
    }


@app.post("/nominas/conciliar-anticipos/{periodo}")
def conciliar_anticipos(periodo: str, transacciones: List[TransaccionBancaria]):
    empleados = []
    if supabase:
        try:
            res = supabase.table("empleado").select("*").execute()
            empleados = res.data
        except Exception:
            pass
    if not empleados:
        empleados = fake_empleados_db

    novedades = []
    if supabase:
        try:
            res = supabase.table("novedad").select("*").eq("periodo", periodo).execute()
            novedades = res.data
        except Exception:
            pass
    if not novedades:
        novedades = [n for n in fake_novedades_db if n.get("periodo") == periodo]

    empleados_by_cuenta = {emp["cuenta_bancaria"]: emp for emp in empleados}
    novedades_by_cedula = {n["empleado_cedula"]: n for n in novedades}

    conciliados = []
    inconsistencias = []
    cuentas_procesadas = set()

    for tx in transacciones:
        cuenta = tx.cuenta_bancaria
        monto = tx.monto
        ref = tx.referencia

        emp = empleados_by_cuenta.get(cuenta)
        if not emp:
            inconsistencias.append({
                "cuenta_bancaria": cuenta,
                "monto": monto,
                "referencia": ref,
                "tipo_error": "Cuenta bancaria no asociada a ningún empleado"
            })
            continue

        cedula = emp["cedula"]
        nombres = emp["nombres"]
        cuentas_procesadas.add(cuenta)

        nov = novedades_by_cedula.get(cedula)
        anticipo_registrado = float(nov["anticipos"]) if (nov and nov.get("anticipos") is not None) else 0.0

        if anticipo_registrado == 0.0:
            inconsistencias.append({
                "cuenta_bancaria": cuenta,
                "monto": monto,
                "referencia": ref,
                "empleado_cedula": cedula,
                "empleado_nombres": nombres,
                "tipo_error": f"El empleado no tiene anticipos registrados para el período {periodo}"
            })
        elif round(anticipo_registrado, 2) == round(monto, 2):
            conciliados.append({
                "cuenta_bancaria": cuenta,
                "monto": monto,
                "referencia": ref,
                "empleado_cedula": cedula,
                "empleado_nombres": nombres
            })
        else:
            inconsistencias.append({
                "cuenta_bancaria": cuenta,
                "monto": monto,
                "referencia": ref,
                "empleado_cedula": cedula,
                "empleado_nombres": nombres,
                "tipo_error": f"El monto de la transacción ({monto}) no coincide con el anticipo registrado ({anticipo_registrado})"
            })

    no_conciliados_sistema = []
    for nov in novedades:
        cedula = nov["empleado_cedula"]
        anticipos = float(nov.get("anticipos", 0.0) or 0.0)
        if anticipos > 0.0:
            emp_for_nov = None
            for e in empleados:
                if e["cedula"] == cedula:
                    emp_for_nov = e
                    break
            
            if emp_for_nov:
                cuenta = emp_for_nov["cuenta_bancaria"]
                if cuenta not in cuentas_procesadas:
                    no_conciliados_sistema.append({
                        "empleado_cedula": cedula,
                        "empleado_nombres": emp_for_nov["nombres"],
                        "cuenta_bancaria": cuenta,
                        "anticipo_registrado": anticipos
                    })

    return {
        "periodo": periodo,
        "total_transacciones_recibidas": len(transacciones),
        "conciliados": conciliados,
        "inconsistencias": inconsistencias,
        "no_conciliados_sistema": no_conciliados_sistema
    }


@app.get("/nominas/archivo-sat/{periodo}")
def descargar_archivo_sat(periodo: str):
    nominas = []
    if supabase:
        try:
            res = supabase.table("nomina").select("*").eq("periodo", periodo).execute()
            nominas = res.data
        except Exception:
            pass
    if not nominas:
        nominas = [n for n in fake_nominas_db if n["periodo"] == periodo]

    if not nominas:
        # If no nominas calculated yet for this period, calculate automatically
        nominas = calcular_nomina(periodo)

    empleados = []
    if supabase:
        try:
            res = supabase.table("empleado").select("*").execute()
            empleados = res.data
        except Exception:
            pass
    if not empleados:
        empleados = fake_empleados_db

    emp_map = {emp["cedula"]: emp for emp in empleados}

    lines = []
    for nom in nominas:
        cedula = nom["empleado_cedula"]
        neto_pagar = nom["neto_pagar"]
        emp = emp_map.get(cedula)
        
        cuenta = emp["cuenta_bancaria"] if emp else "SIN_CUENTA"
        nombres = emp["nombres"] if emp else "Empleado Desconocido"
        
        line = f"{cuenta};{neto_pagar:.2f};{cedula};{nombres};PAGO_NOMINA_{periodo}"
        lines.append(line)

    content = "\n".join(lines)
    
    return Response(
        content=content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=archivo_sat_{periodo}.txt"
        }
    )


@app.post("/nominas/{nomina_id}/registrar-pago")
def registrar_pago_nomina(nomina_id: int, req: RegistroPagoRequest):
    if req.estado not in ["procesado", "fallido"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El estado de pago debe ser 'procesado' o 'fallido'."
        )

    updated_nomina = None
    alerta = None

    if supabase:
        try:
            res_check = supabase.table("nomina").select("*").eq("id", nomina_id).execute()
            if res_check.data:
                res_upd = supabase.table("nomina").update({"estado_pago": req.estado}).eq("id", nomina_id).execute()
                if res_upd.data:
                    updated_nomina = res_upd.data[0]
        except Exception as e:
            print(f"Error updating payment state in Supabase: {e}")

    if not updated_nomina:
        for idx, nom in enumerate(fake_nominas_db):
            if nom.get("id") == nomina_id:
                fake_nominas_db[idx]["estado_pago"] = req.estado
                updated_nomina = fake_nominas_db[idx]
                break

    if not updated_nomina:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registro de nómina con ID {nomina_id} no encontrado."
        )

    if req.estado == "fallido":
        alerta = f"ALERTA DEL SISTEMA: El pago de la nómina con ID {nomina_id} (Empleado: {updated_nomina.get('empleado_cedula')}) ha fallado. Detalle del error: {req.error_mensaje or 'Sin especificar'}"
        print(alerta)

    response_data = {
        "status": "success",
        "message": f"Estado de pago de nómina {nomina_id} actualizado a '{req.estado}'.",
        "nomina": updated_nomina
    }
    if alerta:
        response_data["alerta_simulada"] = alerta

    return response_data
