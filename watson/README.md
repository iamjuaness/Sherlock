# ⚽ SofaScore Stats Extractor

Extensión de Chrome para extraer estadísticas de equipos de fútbol desde [SofaScore](https://www.sofascore.com) y enviarlas a un endpoint personalizado.

## 📋 Características

- **Extracción automática de IDs**: Detecta el `eventId` desde la URL del partido (`#id:12345678`)
- **Múltiples endpoints**: Consulta datos de eventos, alineaciones, rachas y estadísticas de equipos
- **Envío configurable**: Envía los datos en formato JSON a cualquier endpoint REST
- **Panel de settings**: Configura tu URL de destino, token de autenticación y qué datos extraer
- **Interfaz moderna**: Diseño dark mode con indicadores visuales de progreso

## 🚀 Instalación

1. Descarga este repositorio y descomprímelo
2. Abre Chrome y ve a `chrome://extensions/`
3. Activa el **Modo desarrollador** (arriba a la derecha)
4. Haz clic en **"Cargar descomprimida"**
5. Selecciona la carpeta de la extensión

## ⚙️ Configuración

1. Haz clic en el icono de la extensión y selecciona **"Configurar Endpoint"**
2. Ingresa la URL de tu endpoint (debe aceptar `POST` con `Content-Type: application/json`)
3. (Opcional) Agrega un token de autorización
4. Selecciona qué datos quieres extraer
5. Guarda la configuración

## 🎯 Uso

1. Navega a cualquier partido de fútbol en [SofaScore](https://www.sofascore.com)
   - Ejemplo: `https://www.sofascore.com/football/match/morocco-france/GObsDVb#id:12813016`
2. Haz clic en el icono de la extensión
3. La extensión detectará automáticamente:
   - **Event ID**: Extraído del hash `#id:12813016`
   - **Team IDs**: Obtenidos de la API del evento
4. Presiona **"Extraer Estadísticas Completas"**
5. Presiona **"Enviar a Endpoint"** (o configura envío automático)

## 📡 Endpoints de SofaScore Utilizados

| Endpoint | Descripción |
|----------|-------------|
| `/api/v1/event/{id}` | Información principal del partido |
| `/api/v1/event/{id}/lineups` | Alineaciones de ambos equipos |
| `/api/v1/event/{id}/team-streaks` | Rachas y estadísticas recientes |
| `/api/v1/team/{id}/unique-tournament/{tourId}/season/{seasonId}/statistics/overall` | Estadísticas completas del equipo |

## 📦 Estructura de Datos Enviados

```json
{
  "metadata": {
    "extractedAt": "2026-07-08T10:19:00.000Z",
    "source": "sofascore.com",
    "eventId": "12813009",
    "url": "https://www.sofascore.com/..."
  },
  "match": { /* Datos del evento */ },
  "lineups": { /* Alineaciones */ },
  "teamStreaks": { /* Rachas */ },
  "homeTeamStats": { /* Stats equipo local */ },
  "awayTeamStats": { /* Stats equipo visitante */ }
}
```

## 🔧 Headers Enviados

```
Content-Type: application/json
X-Source: sofascore-extractor
X-Extractor-Version: 1.0.0
X-Event-Id: {eventId}
Authorization: Bearer {token}  // Si está configurado
```

## 🛠️ Tecnologías

- Manifest V3
- Chrome Storage API (sync/local)
- Fetch API para llamadas a SofaScore
- Diseño responsive con CSS puro

## 📄 Licencia

MIT
