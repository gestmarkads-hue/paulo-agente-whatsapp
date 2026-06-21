# agent/crm.py — CRM básico para seguimiento de leads
# Generado por AgentKit

import os
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, Integer, select, update
from agent.memory import Base, engine, async_session

ETAPAS = [
    {"id": "nuevo", "nombre": "Nuevo", "color": "#6c757d", "emoji": "1"},
    {"id": "en_conversacion", "nombre": "En conversacion", "color": "#0d6efd", "emoji": "2"},
    {"id": "redes_compartidas", "nombre": "Redes compartidas", "color": "#6610f2", "emoji": "3"},
    {"id": "dificultad_identificada", "nombre": "Dificultad identificada", "color": "#fd7e14", "emoji": "4"},
    {"id": "reunion_agendada", "nombre": "Reunion agendada", "color": "#198754", "emoji": "5"},
    {"id": "no_interesado", "nombre": "No interesado", "color": "#dc3545", "emoji": "X"},
]


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telefono: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(200), default="")
    negocio: Mapped[str] = mapped_column(String(300), default="")
    redes: Mapped[str] = mapped_column(Text, default="")
    dificultad: Mapped[str] = mapped_column(Text, default="")
    etapa: Mapped[str] = mapped_column(String(50), default="nuevo")
    notas: Mapped[str] = mapped_column(Text, default="")
    creado: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actualizado: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


async def inicializar_crm():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def obtener_o_crear_lead(telefono: str) -> Lead:
    async with async_session() as session:
        query = select(Lead).where(Lead.telefono == telefono)
        result = await session.execute(query)
        lead = result.scalar_one_or_none()

        if not lead:
            lead = Lead(telefono=telefono, etapa="nuevo", creado=datetime.utcnow())
            session.add(lead)
            await session.commit()
            await session.refresh(lead)

        return lead


async def actualizar_lead(telefono: str, **campos):
    async with async_session() as session:
        campos["actualizado"] = datetime.utcnow()
        await session.execute(
            update(Lead).where(Lead.telefono == telefono).values(**campos)
        )
        await session.commit()


async def obtener_todos_leads() -> list[Lead]:
    async with async_session() as session:
        query = select(Lead).order_by(Lead.actualizado.desc())
        result = await session.execute(query)
        return result.scalars().all()


async def obtener_lead(telefono: str) -> Lead | None:
    async with async_session() as session:
        query = select(Lead).where(Lead.telefono == telefono)
        result = await session.execute(query)
        return result.scalar_one_or_none()


async def analizar_y_actualizar_lead(telefono: str, mensaje_cliente: str, respuesta_paulo: str):
    lead = await obtener_o_crear_lead(telefono)
    msg = mensaje_cliente.lower()
    resp = respuesta_paulo.lower()

    if lead.etapa == "nuevo" and len(mensaje_cliente) > 3:
        await actualizar_lead(telefono, etapa="en_conversacion")

    palabras_nombre = ["me llamo", "mi nombre es", "soy "]
    for p in palabras_nombre:
        if p in msg:
            idx = msg.index(p) + len(p)
            nombre = mensaje_cliente[idx:].strip().split(",")[0].split(".")[0].split("\n")[0].strip()
            if len(nombre) > 1 and len(nombre) < 50:
                await actualizar_lead(telefono, nombre=nombre)

    indicadores_negocio = ["tengo un", "tengo una", "mi negocio", "mi empresa", "mi tienda", "mi local", "mi restaurante", "vendemos", "ofrecemos"]
    for ind in indicadores_negocio:
        if ind in msg and not lead.negocio:
            inicio = msg.index(ind)
            negocio_texto = mensaje_cliente[inicio:inicio+100].strip()
            await actualizar_lead(telefono, negocio=negocio_texto)
            break

    indicadores_redes = ["@", "instagram.com", "facebook.com", "tiktok.com", ".com/", "mi instagram", "mi face", "mi tiktok", "mi pagina"]
    for ind in indicadores_redes:
        if ind in msg:
            await actualizar_lead(telefono, redes=mensaje_cliente, etapa="redes_compartidas")
            break

    indicadores_dificultad = [
        "mi problema", "mi dificultad", "no me llegan", "no vendo", "no se como",
        "no tengo tiempo", "me cuesta", "no funciona", "no consigo", "necesito ayuda",
        "no se que hacer", "estoy perdido", "sin resultados", "no me resulta",
        "gasto pero no", "invierto pero", "publico pero"
    ]
    for ind in indicadores_dificultad:
        if ind in msg:
            await actualizar_lead(telefono, dificultad=mensaje_cliente, etapa="dificultad_identificada")
            break

    if "calendar.app.google" in resp or "agendar" in resp.lower():
        etapa_actual = (await obtener_lead(telefono))
        if etapa_actual and etapa_actual.etapa in ["dificultad_identificada", "redes_compartidas", "en_conversacion"]:
            await actualizar_lead(telefono, etapa="reunion_agendada")

    indicadores_no = ["no me interesa", "no gracias", "no quiero", "no necesito", "dejalo", "no por ahora"]
    for ind in indicadores_no:
        if ind in msg:
            await actualizar_lead(telefono, etapa="no_interesado")
            break
