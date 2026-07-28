# Riesgos

| ID | Riesgo | Impacto | Mitigación |
|---|---|---:|---|
| HC-RISK-001 | IP cambia por DHCP | Alto | Reserva DHCP + UI editable |
| HC-RISK-002 | Índice no coincide con playlist | Alto | Botones de prueba e identificación |
| HC-RISK-003 | Dos threads escriben al socket | Alto | Un worker por unidad |
| HC-RISK-004 | Rotación queda detenida | Alto | `finally`, estado idempotente y pruebas |
| HC-RISK-005 | Submodelo tarda | Medio | Timeout + fallback |
| HC-RISK-006 | JSON corrupto | Alto | Validación, backup y reemplazo atómico |
| HC-RISK-007 | Metadata llega al TTS | Alto | Side-channel separado |
| HC-RISK-008 | Logos cambian demasiado | Medio | Hold y límite por turno |
| HC-RISK-009 | Unidad caída bloquea IA | Alto | Fail-soft |
| HC-RISK-010 | Modelos débiles duplican arquitectura | Alto | Waves pequeñas y contratos |
| HC-RISK-011 | UI prueba pero no automatiza | Medio | E2E contra endpoints reales |
| HC-RISK-012 | Sleep causa tests inestables | Medio | Reloj virtual |
