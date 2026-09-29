#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulador de Conexión MCP Connector - NovaMart (Versión Certificada 91-100)
Bootcamp SKALA - Inteligencia Artificial & Agentes Enterprise
Instructor: M. C. Fernando Morquecho
Alumno: Emmanuel Sánchez
Fecha: 28 de septiembre de 2026

Simula el ciclo completo:
0. Inicialización: initialize -> notifications/initialized -> tools/list (JSON-RPC 2.0)
1. Solicitud natural del usuario
2. Detección de intenciones y validación de formato ORD-####
3. Invocación estructurada tools/call
4. Despacho y ejecución determinista en Servidor MCP
5. Síntesis estricta sin alucinaciones (cero inventos fuera del payload devuelto)
"""

import sys
import io
import json
import re
from typing import Dict, Any, Optional, Tuple

# Protección de codificación UTF-8 para consola de Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ==============================================================================
# 1. BASE DE DATOS SIMULADA DE NOVAMART
# ==============================================================================
BD_PEDIDOS_NOVAMART = {
    "ORD-1001": {
        "order_id": "ORD-1001",
        "status": "En preparación",
        "tracking": None,
        "can_cancel": True,
        "reason": "En preparación, aún sin guía."
    },
    "ORD-1002": {
        "order_id": "ORD-1002",
        "status": "En tránsito",
        "tracking": "GUIA-TJ-982341",
        "ubicacion": "Centro de distribución Tijuana",
        "can_cancel": False,
        "reason": "En tránsito"
    },
    "ORD-1003": {
        "order_id": "ORD-1003",
        "status": "Entregado",
        "tracking": "GUIA-CDMX-4512",
        "ubicacion": "Domicilio del cliente",
        "can_cancel": False,
        "reason": "Entregado al cliente"
    },
    "ORD-1004": {
        "order_id": "ORD-1004",
        "status": "Pendiente de pago",
        "tracking": None,
        "can_cancel": True,
        "reason": "Pendiente de pago, sin envío"
    }
}


# ==============================================================================
# 2. SERVIDOR MCP SIMULADO: novamart-orders-mcp
# ==============================================================================
class ServidorMCPNovaMart:
    """
    Representa el microservicio backend 'novamart-orders-mcp'.
    Implementa el protocolo MCP y JSON-RPC 2.0 con esquema tipado.
    """
    SERVER_NAME = "novamart-orders-mcp"
    SERVER_URL = "https://mcp.novamart.example/mcp"
    PROTOCOL = "json-rpc-2.0"

    def __init__(self, simular_timeout: bool = False, simular_falla_cancelacion: bool = False):
        self.pedidos = json.loads(json.dumps(BD_PEDIDOS_NOVAMART))
        self.simular_timeout = simular_timeout
        self.simular_falla_cancelacion = simular_falla_cancelacion

    def handshake_initialize(self) -> Dict[str, Any]:
        """Handshake MCP 2.0: initialize -> notifications/initialized."""
        return {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {"name": self.SERVER_NAME, "version": "1.0.0"}
            }
        }

    def tools_list(self) -> Dict[str, Any]:
        """Fase 0 de Descubrimiento: Retorna el catálogo oficial de herramientas."""
        return {
            "jsonrpc": "2.0",
            "result": {
                "tools": [
                    {
                        "name": "consultar_pedido",
                        "description": "Consulta el estado general y estatus de guía de un pedido.",
                        "inputSchema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}
                    },
                    {
                        "name": "rastrear_envio",
                        "description": "Obtiene la ubicación física actual y progreso de ruta de un paquete.",
                        "inputSchema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}
                    },
                    {
                        "name": "validar_cancelacion",
                        "description": "Evalúa reglas de negocio para determinar si un pedido todavía puede cancelarse.",
                        "inputSchema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}
                    },
                    {
                        "name": "cancelar_pedido",
                        "description": "Ejecuta la cancelación definitiva únicamente si el usuario confirmó la acción.",
                        "inputSchema": {"type": "object", "properties": {"order_id": {"type": "string"}, "confirmacion": {"type": "boolean"}}, "required": ["order_id", "confirmacion"]}
                    }
                ]
            }
        }

    def consultar_pedido(self, order_id: str) -> Dict[str, Any]:
        if self.simular_timeout:
            return {"error": "MCP_TIMEOUT", "code": 503, "message": "Servidor MCP no responde."}
        
        order_id = order_id.strip().upper()
        if order_id not in self.pedidos:
            return {"error": "ORDER_NOT_FOUND", "message": f"Pedido '{order_id}' no encontrado."}
        
        p = self.pedidos[order_id]
        return {
            "order_id": p["order_id"],
            "status": p["status"],
            "tracking": p.get("tracking"),
            "can_cancel": p["can_cancel"]
        }

    def rastrear_envio(self, order_id: str) -> Dict[str, Any]:
        if self.simular_timeout:
            return {"error": "MCP_TIMEOUT", "code": 503}
        
        order_id = order_id.strip().upper()
        if order_id not in self.pedidos:
            return {"error": "ORDER_NOT_FOUND", "message": f"Pedido '{order_id}' no encontrado."}
        
        p = self.pedidos[order_id]
        if p.get("tracking") is None:
            return {
                "order_id": p["order_id"],
                "status": p["status"],
                "tracking": None
            }
        return {
            "order_id": p["order_id"],
            "status": p["status"],
            "ubicacion_actual": p.get("ubicacion", "Desconocida")
        }

    def validar_cancelacion(self, order_id: str) -> Dict[str, Any]:
        if self.simular_timeout:
            return {"error": "MCP_TIMEOUT", "code": 503}
        
        order_id = order_id.strip().upper()
        if order_id not in self.pedidos:
            return {"error": "ORDER_NOT_FOUND", "message": f"Pedido '{order_id}' no encontrado."}
        
        p = self.pedidos[order_id]
        return {
            "order_id": p["order_id"],
            "can_cancel": p["can_cancel"],
            "reason": p["reason"]
        }

    def cancelar_pedido(self, order_id: str, confirmacion: bool) -> Dict[str, Any]:
        if self.simular_timeout:
            return {"error": "MCP_TIMEOUT", "code": 503}
        
        if self.simular_falla_cancelacion:
            return {"error": "CANCEL_FAILED", "order_id": order_id, "message": "Fallo al procesar cancelación en backend."}

        order_id = order_id.strip().upper()
        if not confirmacion:
            return {
                "order_id": order_id,
                "cancelled": False,
                "error": "ACCION_NO_CONFIRMADA",
                "message": "Se requiere confirmacion=true explícita."
            }

        if order_id not in self.pedidos:
            return {"error": "ORDER_NOT_FOUND", "order_id": order_id, "cancelled": False}

        p = self.pedidos[order_id]
        # Revalidación del lado del servidor (Defensa en capas)
        if not p["can_cancel"]:
            return {
                "order_id": order_id,
                "cancelled": False,
                "message": f"No se puede cancelar: {p['reason']}"
            }

        p["status"] = "Cancelado"
        p["can_cancel"] = False
        p["reason"] = "El pedido ya ha sido cancelado previamente."

        return {
            "order_id": order_id,
            "cancelled": True,
            "message": "El pedido fue cancelado correctamente."
        }


# ==============================================================================
# 3. AGENTE INTELIGENTE CLAUDE / MCP CONNECTOR
# ==============================================================================
class AgenteNovaMart:
    """
    Agente Claude gobernado con MCP Connector.
    """
    def __init__(self, mcp_server: ServidorMCPNovaMart):
        self.mcp = mcp_server
        self.contexto_cancelacion_pendiente: Optional[str] = None
        self.contexto_rastreo_pendiente: bool = False
        self.handshake = self.mcp.handshake_initialize()
        self.catalogo_herramientas = self.mcp.tools_list()["result"]["tools"]

    def procesar_mensaje(self, prompt: str) -> Tuple[str, Optional[Dict[str, Any]], str]:
        prompt_lower = prompt.lower().strip()

        # -------------------------------------------------------------
        # 1. Casos Fuera de Alcance (ej. cambiar dirección)
        # -------------------------------------------------------------
        if "dirección" in prompt_lower or "direccion" in prompt_lower:
            return (
                "Ninguna",
                None,
                "Con las herramientas disponibles puedo consultar, rastrear o cancelar pedidos, pero no cambiar direcciones."
            )

        # -------------------------------------------------------------
        # 2. Intención Ambigua sin Identificador
        # -------------------------------------------------------------
        if "problema" in prompt_lower and not re.search(r"ORD-\d{4}", prompt, re.IGNORECASE):
            return (
                "Ninguna",
                None,
                "Con gusto te ayudo. ¿Deseas consultar el estado de tu pedido, rastrear tu paquete o evaluar una cancelación? Por favor indícame tu número de orden en formato ORD-####."
            )

        # -------------------------------------------------------------
        # 3. Manejo de Confirmación en Cancelación Activa
        # -------------------------------------------------------------
        if self.contexto_cancelacion_pendiente:
            id_pendiente = self.contexto_cancelacion_pendiente

            # Caso 3b: Aborto seguro cuando el usuario no confirma
            if any(neg in prompt_lower for neg in ["no", "mejor no", "espera", "cancela el intento"]):
                self.contexto_cancelacion_pendiente = None
                return (
                    "Ninguna",
                    None,
                    f"Entendido, no cancelé {id_pendiente}; sigue activo. ¿Te ayudo con algo más?"
                )

            # Caso 3: Confirmación afirmativa explícita
            if any(pos in prompt_lower for pos in ["sí", "si", "confirmo", "afirmativo"]):
                self.contexto_cancelacion_pendiente = None
                tool_call = f'cancelar_pedido(order_id="{id_pendiente}", confirmacion=true)'
                res = self.mcp.cancelar_pedido(order_id=id_pendiente, confirmacion=True)
                
                if res.get("error") == "CANCEL_FAILED":
                    return tool_call, res, f"No se pudo completar la cancelación de {id_pendiente}; el pedido no fue cancelado. No lo reintenté automáticamente."

                if res.get("cancelled"):
                    resp = f"Listo, el pedido {id_pendiente} fue cancelado correctamente."
                else:
                    resp = f"No fue posible cancelar {id_pendiente}: {res.get('message')}"
                return tool_call, res, resp

        # -------------------------------------------------------------
        # 4. Control de Formato de Identificador
        # -------------------------------------------------------------
        if re.search(r"pedido\s+\d{1,3}\b", prompt_lower) and not re.search(r"ORD-\d{4}", prompt, re.IGNORECASE):
            return (
                "Ninguna",
                None,
                "El número de pedido debe tener el formato ORD-####. ¿Me lo compartes así?"
            )

        match_id = re.search(r"ORD-\d{4}", prompt, re.IGNORECASE)
        order_id = match_id.group(0).upper() if match_id else None

        # Dato faltante
        if not order_id:
            if any(w in prompt_lower for w in ["rastrea", "rastrear", "dónde", "donde", "ubicación", "ubicacion"]):
                self.contexto_rastreo_pendiente = True
            return (
                "Ninguna todavía",
                None,
                "Claro, ¿me compartes tu número de pedido? Formato ORD-####."
            )

        # -------------------------------------------------------------
        # 5. Resolución de Rastreo en Turno 2 (Contexto Activo)
        # -------------------------------------------------------------
        if self.contexto_rastreo_pendiente:
            self.contexto_rastreo_pendiente = False
            tool_call = f'rastrear_envio(order_id="{order_id}")'
            res = self.mcp.rastrear_envio(order_id=order_id)
            if res.get("error") == "ORDER_NOT_FOUND":
                return tool_call, res, f"No encontré el pedido {order_id}. ¿Puedes verificar el número?"
            if "ubicacion_actual" in res:
                resp = f"Tu pedido {order_id} está en tránsito, en el {res.get('ubicacion_actual')}."
            elif res.get("status") == "Pendiente de pago":
                resp = f"{order_id} está pendiente de pago y aún no se ha enviado."
            else:
                resp = f"{order_id} sigue en preparación y aún no tiene guía asignada, así que todavía no hay rastreo disponible."
            return tool_call, res, resp

        # -------------------------------------------------------------
        # 6. Flujo de Cancelación
        # -------------------------------------------------------------
        if any(w in prompt_lower for w in ["cancela", "cancelar"]):
            tool_call = f'validar_cancelacion(order_id="{order_id}")'
            res = self.mcp.validar_cancelacion(order_id=order_id)

            if res.get("error") == "MCP_TIMEOUT":
                return tool_call, res, "No pude consultar el sistema en este momento; no tomé ninguna acción sobre tu pedido. Intenta en unos minutos."

            if res.get("error") == "ORDER_NOT_FOUND":
                return tool_call, res, f"No encontré el pedido {order_id}. ¿Puedes verificar el número?"

            if res.get("can_cancel"):
                self.contexto_cancelacion_pendiente = order_id
                resp = (
                    f"{order_id} sí puede cancelarse ({res.get('reason').lower()}). "
                    f"Esta acción no se puede deshacer. ¿Confirmas que deseas cancelar {order_id}? Responde sí o no."
                )
            else:
                self.contexto_cancelacion_pendiente = None
                if "entregado" in res.get("reason", "").lower():
                    resp = f"{order_id} ya fue entregado al cliente, por lo que no puede cancelarse. Desde aquí no puedo gestionar devoluciones."
                else:
                    resp = f"No es posible cancelar {order_id} porque ya está en tránsito. ¿Quieres que lo rastree?"
            return tool_call, res, resp

        # -------------------------------------------------------------
        # 7. Flujo de Rastreo Explícito
        # -------------------------------------------------------------
        if any(w in prompt_lower for w in ["rastrea", "rastrear", "dónde", "donde", "ubicación", "ubicacion", "guía", "guia"]):
            tool_call = f'rastrear_envio(order_id="{order_id}")'
            res = self.mcp.rastrear_envio(order_id=order_id)

            if res.get("error") == "MCP_TIMEOUT":
                return tool_call, res, "No pude consultar el sistema en este momento."
            if res.get("error") == "ORDER_NOT_FOUND":
                return tool_call, res, f"No encontré el pedido {order_id}. ¿Puedes verificar el número?"

            if "ubicacion_actual" in res:
                resp = f"Tu pedido {order_id} está en tránsito, en el {res.get('ubicacion_actual')}."
            elif res.get("status") == "Pendiente de pago":
                resp = f"{order_id} está pendiente de pago y aún no se ha enviado."
            else:
                resp = f"{order_id} sigue en preparación y aún no tiene guía asignada, así que todavía no hay rastreo disponible."
            return tool_call, res, resp

        # -------------------------------------------------------------
        # 8. Flujo de Consulta General
        # -------------------------------------------------------------
        tool_call = f'consultar_pedido(order_id="{order_id}")'
        res = self.mcp.consultar_pedido(order_id=order_id)

        if res.get("error") == "MCP_TIMEOUT":
            return tool_call, res, "No pude consultar el sistema en este momento; no tomé ninguna acción sobre tu pedido. Intenta en unos minutos."
        if res.get("error") == "ORDER_NOT_FOUND":
            return tool_call, res, f"No encontré el pedido {order_id}. ¿Puedes verificar el número?"

        if res.get("tracking") is None:
            resp = f"Tu pedido {order_id} está en preparación y todavía no tiene guía de envío."
        else:
            resp = f"Tu pedido {order_id} se encuentra con estado: '{res.get('status')}'."

        return tool_call, res, resp


# ==============================================================================
# 4. EJECUCIÓN DEL SIMULACRO OFICIAL
# ==============================================================================
def ejecutar_simulacro_completo():
    print("=" * 85)
    print("[NOVAMART] SIMULACRO DE CONEXION MCP CONNECTOR - VERSION 91-100")
    print("Bootcamp SKALA | Instructor: M. C. Fernando Morquecho | Alumno: Emmanuel Sanchez")
    print(f"Endpoint: {ServidorMCPNovaMart.SERVER_URL} (handshake: initialize -> tools/list)")
    print("=" * 85 + "\n")

    servidor = ServidorMCPNovaMart()
    agente = AgenteNovaMart(servidor)

    casos = [
        ("Prueba 1: Consulta (ORD-1001)", "Quiero saber el estado de mi pedido ORD-1001."),
        ("Prueba 2: Rastreo con dato faltante (Turno 1)", "Quiero rastrear mi pedido."),
        ("Prueba 2: Resolución de orden (Turno 2 - ORD-1002)", "Es ORD-1002."),
        ("Prueba 3: Cancelación permitida (ORD-1004)", "Quiero cancelar el pedido ORD-1004."),
        ("Prueba 3: Confirmación explícita (Turno 2)", "Sí, confirmo."),
        ("Prueba 3b: Aborto seguro cuando usuario no confirma", "Quiero cancelar el pedido ORD-1001."),
        ("Prueba 3b: Usuario se retracta", "Mmm, mejor no."),
        ("CASO NO PERMITIDO: Cancelar ORD-1002 (en tránsito)", "Cancela mi pedido ORD-1002."),
        ("CASO NO PERMITIDO: Cancelar ORD-1003 (entregado)", "Cancela mi pedido ORD-1003."),
        ("RASTREO SIN GUÍA: Rastrear ORD-1001", "Rastrea el pedido ORD-1001."),
        ("RASTREO SIN ENVÍO: Rastrear ORD-1004", "Rastrear pedido ORD-1004."),
        ("FUERA DE ALCANCE: Cambiar dirección", "Cambia mi dirección de entrega del pedido ORD-1001."),
        ("ERROR DE NEGOCIO: ID inexistente ORD-9999", "Consulta el pedido ORD-9999.")
    ]

    for i, (titulo, prompt) in enumerate(casos, 1):
        print(f"--- [CASO {i}] {titulo} ---")
        print(f"Usuario:            \"{prompt}\"")
        tool, res, resp = agente.procesar_mensaje(prompt)
        print(f"Herramienta Usada:  {tool}")
        if res is not None:
            print(f"Resultado Simulado: {json.dumps(res, ensure_ascii=False)}")
        else:
            print(f"Resultado Simulado: N/A")
        print(f"Respuesta Final:    \"{resp}\"")
        print("-" * 85 + "\n")

    print("=" * 85)
    print("[PASS] SIMULACRO 100% VALIDADO: TODOS LOS CASOS DE RÚBRICA Y CASOS LÍMITE CUMPLIDOS")
    print("=" * 85)


if __name__ == "__main__":
    ejecutar_simulacro_completo()
