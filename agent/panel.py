# agent/panel.py — Panel web con CRM para seguimiento de leads
# Generado por AgentKit

import os
from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from agent.memory import async_session, Mensaje
from agent.crm import obtener_todos_leads, obtener_lead, actualizar_lead, ETAPAS
from sqlalchemy import select, func


router = APIRouter(prefix="/panel", tags=["panel"])


STYLES = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f0f2f5; color: #1a1a1a; }
.header { background: #075e54; color: white; padding: 20px 30px; }
.header h1 { font-size: 22px; font-weight: 600; }
.header p { font-size: 14px; opacity: 0.8; margin-top: 4px; }
.nav { background: #128c7e; display: flex; gap: 0; }
.nav a { color: white; text-decoration: none; padding: 14px 24px; font-size: 14px; font-weight: 500; opacity: 0.7; border-bottom: 3px solid transparent; }
.nav a:hover { opacity: 1; }
.nav a.active { opacity: 1; border-bottom: 3px solid #25d366; }
.container { max-width: 1100px; margin: 30px auto; padding: 0 20px; }
.card { background: white; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; margin-bottom: 20px; }
.card-header { padding: 18px 24px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
.card-header h3 { font-size: 16px; color: #333; }
table { width: 100%; border-collapse: collapse; }
th { background: #f8f9fa; text-align: left; padding: 12px 18px; font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
td { padding: 14px 18px; border-top: 1px solid #f0f0f0; font-size: 14px; }
tr:hover td { background: #f8fffe; }
.empty { text-align: center; padding: 50px 20px; color: #999; }
.badge { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; color: white; display: inline-block; }
.stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 24px; }
.stat-card { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; }
.stat-card .num { font-size: 32px; font-weight: 700; color: #075e54; }
.stat-card .label { font-size: 13px; color: #666; margin-top: 4px; }
.pipeline { display: flex; gap: 16px; overflow-x: auto; padding-bottom: 10px; }
.pipeline-col { min-width: 220px; flex: 1; background: #f8f9fa; border-radius: 10px; padding: 12px; }
.pipeline-col h4 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; padding: 6px 10px; border-radius: 6px; color: white; text-align: center; }
.lead-card { background: white; border-radius: 8px; padding: 12px; margin-bottom: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.08); cursor: pointer; transition: transform 0.1s; }
.lead-card:hover { transform: translateY(-1px); box-shadow: 0 2px 6px rgba(0,0,0,0.12); }
.lead-card .name { font-weight: 600; font-size: 14px; color: #1a1a1a; }
.lead-card .phone { font-size: 12px; color: #999; margin-top: 2px; }
.lead-card .biz { font-size: 12px; color: #666; margin-top: 4px; }
.lead-card .time { font-size: 11px; color: #bbb; margin-top: 6px; }
"""


def nav_html(active: str) -> str:
    tabs = [
        ("chats", "Conversaciones", "/panel/"),
        ("crm", "CRM", "/panel/crm"),
        ("config", "Configuracion", "/panel/config"),
    ]
    links = ""
    for tid, label, href in tabs:
        cls = "active" if tid == active else ""
        links += f'<a href="{href}" class="{cls}">{label}</a>'
    return f'<div class="nav">{links}</div>'


@router.get("/", response_class=HTMLResponse)
async def panel_principal(request: Request):
    async with async_session() as session:
        query = (
            select(
                Mensaje.telefono,
                func.count(Mensaje.id).label("total_mensajes"),
                func.max(Mensaje.timestamp).label("ultimo_mensaje")
            )
            .group_by(Mensaje.telefono)
            .order_by(func.max(Mensaje.timestamp).desc())
        )
        result = await session.execute(query)
        conversaciones = result.all()

    filas = ""
    for conv in conversaciones:
        telefono, total, ultimo = conv
        fecha = ultimo.strftime("%d/%m/%Y %H:%M") if ultimo else ""
        lead = None
        try:
            from agent.crm import obtener_lead as _ol
            import asyncio
        except Exception:
            pass
        filas += f"""
        <tr onclick="window.location='/panel/chat/{telefono}'" style="cursor:pointer;">
            <td>{telefono}</td>
            <td>{total}</td>
            <td>{fecha}</td>
        </tr>"""

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Paulo — Conversaciones</title>
        <style>{STYLES}</style>
    </head>
    <body>
        <div class="header">
            <h1>Paulo — Panel de Gestmark</h1>
            <p>Asistente Comercial IA</p>
        </div>
        {nav_html("chats")}
        <div class="container">
            <div class="card">
                {"<table><tr><th>Telefono</th><th>Mensajes</th><th>Ultimo mensaje</th></tr>" + filas + "</table>" if filas else '<div class="empty"><p>No hay conversaciones todavia.</p><p>Cuando los clientes escriban a Paulo, apareceran aqui.</p></div>'}
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/chat/{telefono}", response_class=HTMLResponse)
async def ver_chat(telefono: str):
    async with async_session() as session:
        query = (
            select(Mensaje)
            .where(Mensaje.telefono == telefono)
            .order_by(Mensaje.timestamp.asc())
        )
        result = await session.execute(query)
        mensajes = result.scalars().all()

    lead = await obtener_lead(telefono)

    info_lead = ""
    if lead:
        etapa_info = next((e for e in ETAPAS if e["id"] == lead.etapa), ETAPAS[0])
        info_lead = f"""
        <div style="background:#f0faf8;padding:12px 20px;border-bottom:1px solid #e0e0e0;display:flex;gap:20px;align-items:center;flex-wrap:wrap;font-size:13px;">
            <span><b>Nombre:</b> {lead.nombre or 'Sin nombre'}</span>
            <span><b>Negocio:</b> {lead.negocio[:40] + '...' if lead.negocio and len(lead.negocio) > 40 else lead.negocio or 'Sin dato'}</span>
            <span><b>Etapa:</b> <span class="badge" style="background:{etapa_info['color']}">{etapa_info['nombre']}</span></span>
            <a href="/panel/crm/lead/{telefono}" style="color:#075e54;font-weight:600;">Ver en CRM &rarr;</a>
        </div>"""

    burbujas = ""
    for msg in mensajes:
        es_paulo = msg.role == "assistant"
        clase = "paulo" if es_paulo else "cliente"
        nombre = "Paulo" if es_paulo else telefono
        hora = msg.timestamp.strftime("%H:%M") if msg.timestamp else ""
        texto = msg.content.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        burbujas += f"""
        <div class="msg {clase}">
            <div class="nombre">{nombre}</div>
            <div class="texto">{texto}</div>
            <div class="hora">{hora}</div>
        </div>"""

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Chat con {telefono}</title>
        <style>
            {STYLES}
            .chat-header {{ background: #075e54; color: white; padding: 15px 20px; display: flex; align-items: center; gap: 15px; position: sticky; top: 0; z-index: 10; }}
            .chat-header a {{ color: white; text-decoration: none; font-size: 20px; }}
            .chat-header h2 {{ font-size: 17px; font-weight: 500; }}
            body {{ background: #e5ddd5; }}
            .chat {{ max-width: 700px; margin: 20px auto; padding: 0 15px 30px; }}
            .msg {{ max-width: 75%; margin: 8px 0; padding: 10px 14px; border-radius: 10px; word-wrap: break-word; }}
            .msg.cliente {{ background: white; margin-right: auto; border-top-left-radius: 2px; }}
            .msg.paulo {{ background: #dcf8c6; margin-left: auto; border-top-right-radius: 2px; }}
            .nombre {{ font-size: 12px; font-weight: 600; color: #075e54; margin-bottom: 4px; }}
            .texto {{ font-size: 15px; line-height: 1.4; }}
            .hora {{ font-size: 11px; color: #999; text-align: right; margin-top: 4px; }}
        </style>
    </head>
    <body>
        <div class="chat-header">
            <a href="/panel/">&larr;</a>
            <h2>{lead.nombre if lead and lead.nombre else telefono}</h2>
        </div>
        {info_lead}
        <div class="chat">
            {burbujas if burbujas else '<div class="empty">No hay mensajes.</div>'}
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/crm", response_class=HTMLResponse)
async def panel_crm(request: Request):
    leads = await obtener_todos_leads()

    total = len(leads)
    por_etapa = {}
    for e in ETAPAS:
        por_etapa[e["id"]] = [l for l in leads if l.etapa == e["id"]]

    stats = ""
    for e in ETAPAS:
        cant = len(por_etapa[e["id"]])
        stats += f"""
        <div class="stat-card">
            <div class="num" style="color:{e['color']}">{cant}</div>
            <div class="label">{e['nombre']}</div>
        </div>"""

    columnas = ""
    for e in ETAPAS:
        cards = ""
        for lead in por_etapa[e["id"]]:
            nombre = lead.nombre or "Sin nombre"
            negocio = lead.negocio[:35] + "..." if lead.negocio and len(lead.negocio) > 35 else lead.negocio or ""
            tiempo = lead.actualizado.strftime("%d/%m %H:%M") if lead.actualizado else ""
            cards += f"""
            <div class="lead-card" onclick="window.location='/panel/crm/lead/{lead.telefono}'">
                <div class="name">{nombre}</div>
                <div class="phone">{lead.telefono}</div>
                {"<div class='biz'>" + negocio + "</div>" if negocio else ""}
                <div class="time">{tiempo}</div>
            </div>"""

        columnas += f"""
        <div class="pipeline-col">
            <h4 style="background:{e['color']}">{e['nombre']} ({len(por_etapa[e['id']])})</h4>
            {cards if cards else '<div style="text-align:center;color:#ccc;font-size:13px;padding:20px;">Vacio</div>'}
        </div>"""

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Paulo — CRM</title>
        <style>{STYLES}</style>
    </head>
    <body>
        <div class="header">
            <h1>Paulo — CRM de Leads</h1>
            <p>Gestmark | Seguimiento del proceso comercial</p>
        </div>
        {nav_html("crm")}
        <div class="container">
            <div class="stat-grid">
                <div class="stat-card">
                    <div class="num">{total}</div>
                    <div class="label">Total leads</div>
                </div>
                {stats}
            </div>
            <div class="card" style="padding:20px;overflow-x:auto;">
                <div class="pipeline">
                    {columnas}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/crm/lead/{telefono}", response_class=HTMLResponse)
async def ver_lead(telefono: str):
    lead = await obtener_lead(telefono)

    if not lead:
        return HTMLResponse(content="<h1>Lead no encontrado</h1>", status_code=404)

    etapa_actual = next((e for e in ETAPAS if e["id"] == lead.etapa), ETAPAS[0])

    opciones_etapa = ""
    for e in ETAPAS:
        selected = "selected" if e["id"] == lead.etapa else ""
        opciones_etapa += f'<option value="{e["id"]}" {selected}>{e["nombre"]}</option>'

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{lead.nombre or lead.telefono} — CRM</title>
        <style>
            {STYLES}
            .detail {{ max-width: 700px; margin: 30px auto; padding: 0 20px; }}
            .detail .card {{ padding: 28px; }}
            .field {{ margin-bottom: 18px; }}
            .field label {{ display: block; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: #999; margin-bottom: 6px; }}
            .field .value {{ font-size: 15px; color: #333; }}
            .field input, .field textarea, .field select {{ width: 100%; padding: 10px 14px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; font-family: inherit; }}
            .field textarea {{ min-height: 80px; resize: vertical; }}
            .field select {{ background: white; }}
            .field input:focus, .field textarea:focus, .field select:focus {{ outline: none; border-color: #25d366; }}
            .actions {{ display: flex; gap: 12px; margin-top: 24px; }}
            .btn {{ padding: 12px 28px; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; }}
            .btn-primary {{ background: #25d366; color: white; }}
            .btn-primary:hover {{ background: #128c7e; }}
            .btn-secondary {{ background: #f0f0f0; color: #333; }}
            .btn-chat {{ background: #075e54; color: white; text-decoration: none; display: inline-block; }}
            .status-msg {{ margin-top: 15px; padding: 12px; border-radius: 8px; font-size: 14px; display: none; }}
            .status-msg.ok {{ background: #d4edda; color: #155724; display: block; }}
            .top-bar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Detalle del Lead</h1>
        </div>
        {nav_html("crm")}
        <div class="detail">
            <div class="top-bar">
                <a href="/panel/crm" style="color:#075e54;font-weight:600;text-decoration:none;">&larr; Volver al CRM</a>
                <a href="/panel/chat/{lead.telefono}" class="btn btn-chat">Ver chat</a>
            </div>
            <div class="card">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
                    <h3 style="font-size:20px;">{lead.nombre or 'Sin nombre'}</h3>
                    <span class="badge" style="background:{etapa_actual['color']};font-size:14px;padding:6px 16px;">{etapa_actual['nombre']}</span>
                </div>

                <form id="leadForm">
                    <div class="field">
                        <label>Telefono</label>
                        <div class="value">{lead.telefono}</div>
                    </div>
                    <div class="field">
                        <label>Nombre</label>
                        <input type="text" name="nombre" value="{lead.nombre or ''}">
                    </div>
                    <div class="field">
                        <label>Negocio</label>
                        <input type="text" name="negocio" value="{lead.negocio or ''}">
                    </div>
                    <div class="field">
                        <label>Redes sociales</label>
                        <textarea name="redes">{lead.redes or ''}</textarea>
                    </div>
                    <div class="field">
                        <label>Dificultad / Problema</label>
                        <textarea name="dificultad">{lead.dificultad or ''}</textarea>
                    </div>
                    <div class="field">
                        <label>Etapa</label>
                        <select name="etapa">{opciones_etapa}</select>
                    </div>
                    <div class="field">
                        <label>Notas internas</label>
                        <textarea name="notas" placeholder="Agrega notas sobre este lead...">{lead.notas or ''}</textarea>
                    </div>
                    <div class="field">
                        <label>Creado</label>
                        <div class="value">{lead.creado.strftime('%d/%m/%Y %H:%M') if lead.creado else ''}</div>
                    </div>
                    <div class="actions">
                        <button type="submit" class="btn btn-primary">Guardar cambios</button>
                    </div>
                </form>
                <div id="status" class="status-msg"></div>
            </div>
        </div>

        <script>
            document.getElementById('leadForm').addEventListener('submit', async (e) => {{
                e.preventDefault();
                const form = new FormData(e.target);
                const data = Object.fromEntries(form);
                data.telefono = '{lead.telefono}';
                try {{
                    const r = await fetch('/panel/crm/lead/save', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify(data)
                    }});
                    const el = document.getElementById('status');
                    if (r.ok) {{
                        el.className = 'status-msg ok';
                        el.textContent = 'Lead actualizado correctamente';
                        setTimeout(() => el.style.display = 'none', 3000);
                    }}
                }} catch(err) {{
                    console.error(err);
                }}
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.post("/crm/lead/save")
async def guardar_lead(request: Request):
    data = await request.json()
    telefono = data.pop("telefono")
    await actualizar_lead(telefono, **data)
    return {"status": "ok"}


@router.get("/config", response_class=HTMLResponse)
async def panel_config(request: Request):
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

    valores = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith("#") and "=" in linea:
                    clave, valor = linea.split("=", 1)
                    valores[clave.strip()] = valor.strip()

    phone_id = valores.get("META_PHONE_NUMBER_ID", "")
    verify_token = valores.get("META_VERIFY_TOKEN", "")

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Configuracion — Paulo</title>
        <style>{STYLES}
            .detail {{ max-width: 600px; margin: 30px auto; padding: 0 20px; }}
            .card {{ padding: 30px; }}
            label {{ display: block; font-size: 14px; color: #666; margin-bottom: 6px; margin-top: 16px; }}
            input {{ width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 15px; }}
            input:focus {{ outline: none; border-color: #25d366; }}
            button {{ margin-top: 24px; padding: 12px 30px; background: #25d366; color: white; border: none; border-radius: 8px; font-size: 15px; cursor: pointer; }}
            button:hover {{ background: #128c7e; }}
            .status {{ margin-top: 15px; padding: 12px; border-radius: 8px; font-size: 14px; display: none; }}
            .status.ok {{ background: #d4edda; color: #155724; display: block; }}
            .status.error {{ background: #f8d7da; color: #721c24; display: block; }}
            .info {{ font-size: 13px; color: #999; margin-top: 6px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Configuracion</h1>
            <p>WhatsApp y credenciales</p>
        </div>
        {nav_html("config")}
        <div class="detail">
            <div class="card">
                <h3 style="color:#075e54;margin-bottom:10px;">WhatsApp — Meta Cloud API</h3>
                <form id="configForm">
                    <label>Phone Number ID</label>
                    <input type="text" name="phone_number_id" value="{phone_id}" placeholder="Ej: 1099076106632183">
                    <p class="info">Lo encontras en developers.facebook.com > WhatsApp > API Setup</p>

                    <label>Access Token</label>
                    <input type="password" name="access_token" value="••••••••" placeholder="EAA...">
                    <p class="info">Token de acceso de Meta Cloud API</p>

                    <label>Verify Token</label>
                    <input type="text" name="verify_token" value="{verify_token}" placeholder="Ej: gestmark-paulo-2024">
                    <p class="info">Texto secreto para verificar el webhook</p>

                    <button type="submit">Guardar cambios</button>
                </form>
                <div id="status" class="status"></div>
            </div>
        </div>

        <script>
            document.getElementById('configForm').addEventListener('submit', async (e) => {{
                e.preventDefault();
                const form = new FormData(e.target);
                const data = Object.fromEntries(form);
                try {{
                    const r = await fetch('/panel/config/save', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify(data)
                    }});
                    const el = document.getElementById('status');
                    if (r.ok) {{
                        el.className = 'status ok';
                        el.textContent = 'Guardado. Reinicia el servidor para aplicar cambios.';
                    }} else {{
                        el.className = 'status error';
                        el.textContent = 'Error al guardar';
                    }}
                }} catch(err) {{
                    document.getElementById('status').className = 'status error';
                    document.getElementById('status').textContent = 'Error de conexion';
                }}
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.post("/config/save")
async def guardar_config(request: Request):
    data = await request.json()
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

    lineas = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lineas = f.readlines()

    nuevas_lineas = []
    claves_actualizadas = set()

    mapa = {
        "phone_number_id": "META_PHONE_NUMBER_ID",
        "access_token": "META_ACCESS_TOKEN",
        "verify_token": "META_VERIFY_TOKEN",
    }

    for linea in lineas:
        modificada = False
        for campo, env_key in mapa.items():
            valor = data.get(campo, "")
            if valor and valor != "••••••••" and linea.strip().startswith(f"{env_key}="):
                nuevas_lineas.append(f"{env_key}={valor}\n")
                claves_actualizadas.add(env_key)
                modificada = True
                break
        if not modificada:
            nuevas_lineas.append(linea)

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(nuevas_lineas)

    return {"status": "ok", "updated": list(claves_actualizadas)}
