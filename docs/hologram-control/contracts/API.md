# Contrato API

## Unidades

```text
GET  /api/hologram/units
PUT  /api/hologram/units/{role}
POST /api/hologram/units/{role}/connect
POST /api/hologram/units/{role}/disconnect
POST /api/hologram/units/{role}/identify
POST /api/hologram/units/{role}/test
```

## Identidades

```text
GET    /api/hologram/identities
POST   /api/hologram/identities
PUT    /api/hologram/identities/{id}
DELETE /api/hologram/identities/{id}
POST   /api/hologram/identities/{id}/test
```

## Promociones

```text
GET    /api/hologram/promotions
POST   /api/hologram/promotions
PUT    /api/hologram/promotions/{id}
DELETE /api/hologram/promotions/{id}
POST   /api/hologram/promotions/{id}/test
POST   /api/hologram/promotions/test-category
```

## Rotación

```text
POST /api/hologram/rotation/start
POST /api/hologram/rotation/pause
POST /api/hologram/rotation/resume
GET  /api/hologram/rotation/status
```

## Compatibilidad

Los endpoints heredados continúan delegando a `top`.
