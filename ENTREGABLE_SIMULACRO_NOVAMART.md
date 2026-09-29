# Actividad Práctica: Simulacro de Conexión MCP Connector (NovaMart)

**Bootcamp SKALA - Inteligencia Artificial & Agentes Enterprise**  
**Instructor:** M. C. Fernando Morquecho  
**Fecha:** 28 de septiembre de 2026  
**Alumno:** Emmanuel Sánchez  
**Materia / Módulo:** Semana 2 - Conexión de Herramientas MCP y Model Context Protocol  
**Evaluación Oficial Obtenida:** 91 / 100 (Aprobado con Distinción Técnica)  

---

```text
Nombre: Emmanuel Sánchez
Servidor MCP simulado: novamart-orders-mcp
Endpoint simulado: https://mcp.novamart.example/mcp (dominio reservado RFC 2606; no hay conexión real)

1. FLUJO DE CONEXIÓN (9 pasos)
 0. Inicialización  → MCP Connector ⇄ Servidor MCP: initialize → notifications/initialized
                      → tools/list (JSON-RPC 2.0). Claude recibe nombres, descripciones y esquemas.
 1. Usuario         → escribe su solicitud en lenguaje natural.
 2. Claude/Agente   → interpreta la intención, valida el formato ORD-#### y elige la herramienta
                      (o pide el dato faltante sin llamar a ninguna).
 3. MCP Connector   → traduce la decisión en una llamada tipada tools/call y la envía al servidor.
 4. Servidor MCP    → valida el esquema de entrada y despacha a la función correspondiente.
 5. Herramienta sim.→ consulta o modifica los datos simulados de NovaMart.
 6. Resultado       → JSON estructurado (éxito o error) de regreso por la misma ruta.
 7. Claude/Agente   → redacta la respuesta usando solo los campos devueltos.
 8. Respuesta final → entregada al usuario en español.

2. MAPEO DE INTENCIONES A HERRAMIENTAS
| Intención (ejemplo)                        | Herramienta          | Parámetros                          |
|--------------------------------------------|----------------------|-------------------------------------|
| "¿Cómo va mi pedido?"                      | consultar_pedido     | order_id                            |
| "¿Dónde está mi paquete?" / "Dame la guía" | rastrear_envio       | order_id                            |
| "Quiero cancelar" / "Ya no lo quiero"      | validar_cancelacion  | order_id                            |
| "Sí, confirmo cancelar ORD-XXXX"           | cancelar_pedido      | order_id, confirmacion=true         |
| "Tengo un problema con mi pedido" (ambiguo)| ninguna → aclarar    | Pregunta: ¿estado, rastreo o cancelación? |

Reglas del agente:
- Nunca inventa ni adivina un order_id; si falta, lo pide en formato ORD-####.
- Solo usa los campos que devuelve la herramienta; si un dato no viene, dice que no lo tiene.
- No ofrece acciones para las que no existe herramienta.
- La confirmación es válida solo para el order_id validado en el turno inmediato anterior.
- "No", "mejor no" o una respuesta ambigua = no cancelar.

3. MANEJO DE DATOS FALTANTES
- Sin order_id → "¿Me compartes tu número de pedido? Tiene el formato ORD-####."
- Formato inválido ("pedido 55") → no llama a ninguna herramienta; pide el formato correcto.
- ID inexistente (ORD-9999) → el servidor devuelve ORDER_NOT_FOUND; el agente pide verificarlo.
- Varios IDs en un mensaje → los procesa uno por uno; si hay una cancelación, confirma cada ID por separado.

4. CONFIRMACIÓN ANTES DE CANCELAR
 a) validar_cancelacion(order_id).
 b) Si can_cancel = false → explica el motivo devuelto y NO continúa.
 c) Si can_cancel = true → avisa que la acción es irreversible y pide un "sí" explícito para ese ID.
 d) Solo con un "sí" claro en el turno siguiente → cancelar_pedido(order_id, confirmacion=true).
    (El servidor revalida el estado; si cambió, devuelve un error y el agente lo informa.)
 e) Jamás se llama cancelar_pedido con confirmacion=false ni sin la validación previa.

5. ERRORES Y CASOS NO PERMITIDOS
| Caso                               | Herramienta         | Resultado simulado                                  | Respuesta del agente |
|------------------------------------|---------------------|-----------------------------------------------------|----------------------|
| Cancelar ORD-1002                  | validar_cancelacion | {"can_cancel": false, "reason": "En tránsito"}      | "No es posible cancelar ORD-1002 porque ya está en tránsito. ¿Quieres que lo rastree?" |
| Cancelar ORD-1003                  | validar_cancelacion | {"can_cancel": false, "reason": "Entregado al cliente"} | "ORD-1003 ya fue entregado al cliente, por lo que no puede cancelarse. Desde aquí no puedo gestionar devoluciones." |
| Rastrear ORD-1001 (sin guía)       | rastrear_envio      | {"status": "En preparación", "tracking": null}      | "ORD-1001 sigue en preparación y aún no tiene guía asignada, así que todavía no hay rastreo disponible." |
| Rastrear ORD-1004 (sin envío)      | rastrear_envio      | {"status": "Pendiente de pago", "tracking": null}   | "ORD-1004 está pendiente de pago y aún no se ha enviado." |
| ID inexistente ORD-9999            | consultar_pedido    | {"error": "ORDER_NOT_FOUND"}                        | "No encontré el pedido ORD-9999. ¿Puedes verificar el número?" |
| Servidor MCP no responde           | cualquiera          | {"error": "MCP_TIMEOUT", "code": 503}               | "No pude consultar el sistema en este momento; no tomé ninguna acción sobre tu pedido. Intenta en unos minutos." |
| Falla cancelar_pedido tras confirmar | cancelar_pedido   | {"error": "CANCEL_FAILED"}                          | "No se pudo completar la cancelación de ORD-1004; el pedido no fue cancelado. No lo reintenté automáticamente." |
| Fuera de alcance ("cambia mi dirección") | ninguna       | N/A                                                 | "Con las herramientas disponibles puedo consultar, rastrear o cancelar pedidos, pero no cambiar direcciones." |

Política de reintentos: las lecturas (consultar, rastrear, validar) pueden reintentarse una vez.
cancelar_pedido NUNCA se reintenta automáticamente: primero se consulta el estado y se informa al usuario.

6. EJEMPLOS DE CONVERSACIÓN SIMULADA

Prueba 1: Consulta (ORD-1001)
 Usuario: "Quiero saber el estado de mi pedido ORD-1001."
 Agente → consultar_pedido(order_id="ORD-1001")
 Servidor → {"order_id":"ORD-1001","status":"En preparación","tracking":null,"can_cancel":true}
 Agente: "Tu pedido ORD-1001 está en preparación y todavía no tiene guía de envío."

Prueba 2: Rastreo con dato faltante (ORD-1002)
 Usuario: "Quiero rastrear mi pedido."
 Agente: (sin herramienta) "Claro, ¿me compartes tu número de pedido? Formato ORD-####."
 Usuario: "Es ORD-1002."
 Agente → rastrear_envio(order_id="ORD-1002")
 Servidor → {"order_id":"ORD-1002","status":"En tránsito","ubicacion_actual":"Centro de distribución Tijuana"}
 Agente: "Tu pedido ORD-1002 está en tránsito, en el Centro de distribución Tijuana."

Prueba 3: Cancelación permitida (ORD-1004)
 Usuario: "Quiero cancelar el pedido ORD-1004."
 Agente → validar_cancelacion(order_id="ORD-1004")
 Servidor → {"order_id":"ORD-1004","can_cancel":true,"reason":"Pendiente de pago, sin envío"}
 Agente: "ORD-1004 sí puede cancelarse (pendiente de pago, sin envío). Esta acción no se puede
          deshacer. ¿Confirmas que deseas cancelar ORD-1004? Responde sí o no."
 Usuario: "Sí, confirmo."
 Agente → cancelar_pedido(order_id="ORD-1004", confirmacion=true)
 Servidor → {"order_id":"ORD-1004","cancelled":true,"message":"El pedido fue cancelado correctamente."}
 Agente: "Listo, el pedido ORD-1004 fue cancelado correctamente."

Prueba 3b: El usuario no confirma
 Usuario: "Mmm, mejor no."
 Agente: (sin herramienta) "Entendido, no cancelé ORD-1004; sigue activo. ¿Te ayudo con algo más?"

CONCLUSIÓN
MCP separa el razonamiento (Claude interpreta la intención y decide qué herramienta usar) de la
ejecución (el servidor valida y despacha funciones con contratos tipados). La confiabilidad del
agente descansa en tres prácticas:
 1. Herramientas autodescriptivas, descubiertas con tools/list.
 2. Respuestas basadas solo en los datos devueltos, para minimizar alucinaciones.
 3. Gobernanza de acciones destructivas: validar, obtener confirmación explícita ligada al pedido,
    revalidar en el servidor y no reintentar a ciegas.
```

---

## 📊 Calificación Oficial de Claude

```
Calificación Final: 91 / 100 (Aprobado con Excelencia Técnica)
- Flujo Claude → MCP Connector → Servidor → Herramienta: 19 / 20
- Intenciones → Herramientas correctas: 18 / 20
- Datos faltantes sin inventar: 13 / 15
- Confirmación antes de cancelar: 14 / 15
- Errores y casos no permitidos: 13 / 15
- Entrega clara y ordenada: 14 / 15
```
