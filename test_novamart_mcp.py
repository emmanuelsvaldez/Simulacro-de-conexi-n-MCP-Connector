#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Suite de Pruebas Automatizadas: Simulacro MCP Connector NovaMart (Versión 100/100)
Bootcamp SKALA - Inteligencia Artificial & Agentes Enterprise
Instructor: M. C. Fernando Morquecho | Alumno: Emmanuel Sánchez

Valida el 100% de los criterios de la rúbrica y los casos límite identificados:
- Descubrimiento inicial tools/list (JSON-RPC 2.0)
- Consulta sin alucinaciones (tracking: null)
- Flujo de rastreo con dato faltante resuelto en Turno 2
- Cancelación en dos fases con confirmación
- Aborto seguro cuando el usuario no confirma
- Rechazo de cancelación en tránsito (ORD-1002) y entregado (ORD-1003)
- Manejo de formato inválido y pedido inexistente (ORD-9999)
- Resiliencia ante falla técnica/timeout de servidor MCP
"""

import pytest
from simulador_novamart import ServidorMCPNovaMart, AgenteNovaMart


@pytest.fixture
def entorno_novamart():
    servidor = ServidorMCPNovaMart()
    agente = AgenteNovaMart(servidor)
    return servidor, agente


def test_01_descubrimiento_tools_list(entorno_novamart):
    """Paso 0: Valida que el servidor MCP exponga el catálogo oficial de 4 herramientas."""
    servidor, agente = entorno_novamart
    catalogo = servidor.tools_list()
    
    assert catalogo["jsonrpc"] == "2.0"
    nombres_tools = [t["name"] for t in catalogo["result"]["tools"]]
    assert "consultar_pedido" in nombres_tools
    assert "rastrear_envio" in nombres_tools
    assert "validar_cancelacion" in nombres_tools
    assert "cancelar_pedido" in nombres_tools
    assert len(agente.catalogo_herramientas) == 4


def test_02_consulta_ord1001_sin_alucinacion(entorno_novamart):
    """Prueba 1: Consulta de estado con JSON que incluye tracking: null sin alucinar."""
    _, agente = entorno_novamart
    tool, res, resp = agente.procesar_mensaje("Quiero saber el estado de mi pedido ORD-1001.")
    
    assert "consultar_pedido" in tool
    assert res["order_id"] == "ORD-1001"
    assert res["status"] == "En preparación"
    assert res["tracking"] is None
    assert "preparación" in resp.lower()
    assert "todavía no tiene guía de envío" in resp.lower()


def test_03_rastreo_dato_faltante_y_resolucion_turno2(entorno_novamart):
    """Prueba 2: Manejo de dato faltante en Turno 1 y resolución con rastrear_envio en Turno 2."""
    _, agente = entorno_novamart
    
    # Turno 1: Usuario pide rastrear sin ID
    tool_t1, res_t1, resp_t1 = agente.procesar_mensaje("Quiero rastrear mi pedido.")
    assert tool_t1 == "Ninguna todavía"
    assert res_t1 is None
    assert "formato ord-####" in resp_t1.lower()
    assert agente.contexto_rastreo_pendiente is True
    
    # Turno 2: Usuario proporciona ID -> Invoca rastrear_envio
    tool_t2, res_t2, resp_t2 = agente.procesar_mensaje("Es ORD-1002.")
    assert "rastrear_envio" in tool_t2
    assert res_t2["order_id"] == "ORD-1002"
    assert "Tijuana" in res_t2["ubicacion_actual"]
    assert "tijuana" in resp_t2.lower()
    assert agente.contexto_rastreo_pendiente is False


def test_04_cancelacion_confirmada_ord1004(entorno_novamart):
    """Prueba 3: Cancelación en 2 fases con confirmación explícita (Human-in-the-Loop)."""
    _, agente = entorno_novamart
    
    # Fase 1: Validación
    tool_f1, res_f1, resp_f1 = agente.procesar_mensaje("Quiero cancelar el pedido ORD-1004.")
    assert "validar_cancelacion" in tool_f1
    assert res_f1["can_cancel"] is True
    assert "¿confirmas que deseas cancelar ord-1004?" in resp_f1.lower()
    assert agente.contexto_cancelacion_pendiente == "ORD-1004"
    
    # Fase 2: Confirmación afirmativa
    tool_f2, res_f2, resp_f2 = agente.procesar_mensaje("Sí, confirmo.")
    assert "cancelar_pedido" in tool_f2
    assert res_f2["cancelled"] is True
    assert "cancelado correctamente" in resp_f2.lower()
    assert agente.contexto_cancelacion_pendiente is None


def test_05_cancelacion_aborto_usuario_dice_no(entorno_novamart):
    """Prueba 3b: Aborto seguro cuando el usuario no confirma la cancelación."""
    servidor, agente = entorno_novamart
    
    # Fase 1: Validación
    agente.procesar_mensaje("Quiero cancelar el pedido ORD-1001.")
    assert agente.contexto_cancelacion_pendiente == "ORD-1001"
    
    # Fase 2: Rechazo del usuario
    tool_f2, res_f2, resp_f2 = agente.procesar_mensaje("Mmm, mejor no.")
    assert tool_f2 == "Ninguna"
    assert res_f2 is None
    assert "no cancelé ord-1001; sigue activo" in resp_f2.lower()
    assert servidor.pedidos["ORD-1001"]["status"] == "En preparación"
    assert agente.contexto_cancelacion_pendiente is None


def test_06_error_controlado_en_transito_ord1002(entorno_novamart):
    """Caso no permitido: Pedido en tránsito no puede cancelarse."""
    servidor, agente = entorno_novamart
    tool, res, resp = agente.procesar_mensaje("Cancela mi pedido ORD-1002.")
    
    assert "validar_cancelacion" in tool
    assert res["can_cancel"] is False
    assert "no es posible cancelar ord-1002 porque ya está en tránsito" in resp.lower()
    assert "¿quieres que lo rastree?" in resp.lower()
    assert servidor.pedidos["ORD-1002"]["status"] == "En tránsito"


def test_07_error_controlado_entregado_ord1003(entorno_novamart):
    """Caso no permitido: Pedido entregado no puede cancelarse y ofrece atención a clientes."""
    servidor, agente = entorno_novamart
    tool, res, resp = agente.procesar_mensaje("Cancela mi pedido ORD-1003.")
    
    assert "validar_cancelacion" in tool
    assert res["can_cancel"] is False
    assert "ya fue entregado al cliente, por lo que no puede cancelarse" in resp.lower()
    assert "devoluciones" in resp.lower()
    assert servidor.pedidos["ORD-1003"]["status"] == "Entregado"


def test_08_control_formato_invalido(entorno_novamart):
    """Caso límite: Formato inválido ('pedido 55') es rechazado por regex."""
    _, agente = entorno_novamart
    tool, res, resp = agente.procesar_mensaje("Quiero ver mi pedido 55.")
    
    assert tool == "Ninguna"
    assert res is None
    assert "formato ord-####" in resp.lower()


def test_09_id_inexistente_ord9999(entorno_novamart):
    """Caso de error de negocio: Pedido inexistente ORD-9999."""
    _, agente = entorno_novamart
    tool, res, resp = agente.procesar_mensaje("Consulta el pedido ORD-9999.")
    
    assert "consultar_pedido" in tool
    assert res["error"] == "ORDER_NOT_FOUND"
    assert "no encontré el pedido ord-9999" in resp.lower()


def test_10_resiliencia_servidor_mcp_caido():
    """Caso de falla técnica: Servidor MCP no responde (timeout 503)."""
    servidor_caido = ServidorMCPNovaMart(simular_timeout=True)
    agente = AgenteNovaMart(servidor_caido)
    
    tool, res, resp = agente.procesar_mensaje("Consulta el pedido ORD-1001.")
    assert res["error"] == "MCP_TIMEOUT"
    assert "no pude consultar el sistema" in resp.lower()
    assert "no tomé ninguna acción" in resp.lower()
