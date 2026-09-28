#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Suite de Pruebas Automatizadas: Simulacro MCP Connector NovaMart
Bootcamp SKALA - Inteligencia Artificial & Agentes Enterprise
Valida los 6 criterios de la rúbrica oficial (100 puntos).
"""

import pytest
from simulador_novamart import ServidorMCPNovaMart, AgenteNovaMart


@pytest.fixture
def entorno_novamart():
    servidor = ServidorMCPNovaMart()
    agente = AgenteNovaMart(servidor)
    return servidor, agente


def test_caso_1_consultar_pedido_ord1001(entorno_novamart):
    """Prueba 1: Consulta de estado de pedido ORD-1001."""
    _, agente = entorno_novamart
    tool_name, resultado, respuesta = agente.procesar_mensaje("Quiero saber el estado de mi pedido ORD-1001.")
    
    assert "consultar_pedido" in tool_name
    assert resultado is not None
    assert resultado["order_id"] == "ORD-1001"
    assert resultado["status"] == "En preparación"
    assert "preparación" in respuesta


def test_caso_2_dato_faltante_sin_herramientas(entorno_novamart):
    """Prueba 2: Manejo de dato faltante sin inventar información."""
    _, agente = entorno_novamart
    tool_name, resultado, respuesta = agente.procesar_mensaje("Quiero rastrear mi pedido.")
    
    # No debe llamar ninguna herramienta al carecer de identificador
    assert tool_name == "Ninguna todavía"
    assert resultado is None
    assert "¿Me compartes tu número de pedido?" in respuesta


def test_caso_3_cancelacion_en_dos_fases_ord1004(entorno_novamart):
    """Prueba 3: Cancelación en 2 fases con confirmación explícita (Human-in-the-Loop)."""
    _, agente = entorno_novamart
    
    # Fase 1: Solicitud inicial
    tool_fase1, res_fase1, resp_fase1 = agente.procesar_mensaje("Quiero cancelar el pedido ORD-1004.")
    assert "validar_cancelacion" in tool_fase1
    assert res_fase1["can_cancel"] is True
    assert "¿Confirmas que deseas cancelarlo?" in resp_fase1
    
    # Fase 2: Confirmación explícita
    tool_fase2, res_fase2, resp_fase2 = agente.procesar_mensaje("Sí, confirmo.")
    assert "cancelar_pedido" in tool_fase2
    assert res_fase2["cancelled"] is True
    assert "cancelado correctamente" in resp_fase2


def test_caso_4_error_controlado_en_transito_ord1002(entorno_novamart):
    """Prueba 4: Control de caso no permitido (pedido en tránsito no cancelable)."""
    servidor, agente = entorno_novamart
    tool_name, resultado, respuesta = agente.procesar_mensaje("Cancela mi pedido ORD-1002.")
    
    assert "validar_cancelacion" in tool_name
    assert resultado["can_cancel"] is False
    assert "en tránsito" in resultado["reason"].lower()
    # Verifica que el agente NO llamó a cancelar_pedido y comunicó el rechazo
    assert "No puedo cancelar el pedido ORD-1002 porque ya está en tránsito" in respuesta
    assert servidor.pedidos["ORD-1002"]["status"] == "En tránsito"


def test_rastreo_envio_ubicacion(entorno_novamart):
    """Prueba complementaria: Rastrear envío de pedido ORD-1002."""
    _, agente = entorno_novamart
    tool_name, resultado, respuesta = agente.procesar_mensaje("¿Dónde está mi paquete ORD-1002?")
    
    assert "rastrear_envio" in tool_name
    assert "Tijuana" in resultado["ubicacion_actual"]
    assert "Tijuana" in respuesta
