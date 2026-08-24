# Last-Mile Delivery Tracker Platform

A logistics operations platform with dynamic rate calculation, automatic zone detection, intelligent delivery agent auto-assignment, immutable tracking history, failed delivery rescheduling workflows, and role-based access control (Admin, Customer, Delivery Agent).

---

## 🌟 Key Features

1. **Role-Based Access Control (RBAC)**:
   - **Customer**: Create orders, view real-time itemized price estimates, track live delivery timeline, and reschedule failed delivery attempts.
   - **Delivery Agent**: View assigned tasks, toggle availability/location, and update delivery status (`Picked Up`, `In Transit`, `Out for Delivery`, `Delivered`, `Failed` with mandatory failure reason).
   - **Admin**: Configure zones, assign area pincodes, edit B2B/B2C rate cards and COD surcharges, view all orders with multi-filters, manually assign or trigger auto-assignment, override order statuses, and audit notification logs.

2. **Dynamic Rate Calculation Engine**:
   - **Volumetric Weight Calculation**: $\text{Volumetric Weight} = (L \times W \times H) / 5000$ (in cm and kg).
   - **Billable Weight**: Bills on $\max(\text{Actual Weight}, \text{Volumetric Weight})$.
   - **Zone & Route Resolution**: Detects `Pickup Zone` and `Drop Zone`. Classifies route as `INTRA-ZONE` if origin equals destination zone, else `INTER-ZONE`.
   - **Dynamic Rate Cards**: Lookups non-hardcoded DB rate cards for B2B/B2C and Intra/Inter routes.
   - **COD Surcharges**: Adds dynamic fixed fee and percentage surcharge for Cash-on-Delivery orders.

3. **Intelligent Auto-Assignment Engine**:
   - Scores available delivery agents based on **Haversine geo-distance** from agent coordinates to pickup location, **Zone Match Bonus** (-50km virtual distance reduction if agent's active zone matches pickup zone), and **Workload Penalty** (+5 score per active order).
   - Automatically assigns the lowest composite score agent upon order placement or rescheduling.

4. **Failed Delivery Lifecycle & Reschedule Mechanism**:
   - Captures mandatory failure reason when marked `FAILED`.
   - Notifies customer via Email and SMS log.
   - Customer can pick a new target delivery date & time slot.
   - Rescheduling sets status to `RESCHEDULED` and automatically re-triggers intelligent agent auto-reassignment.

5. **Immutable Tracking Timeline**:
   - Every status change generates an immutable record with timestamp, actor ID, actor role, location coordinates, and operational notes.

---

## 🚀 Quick Setup & Execution Guide

### Prerequisites
- Python 3.9+ (Python 3.13 fully supported)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Application
```bash
python run.py
```
The application will automatically initialize the database, seed initial demo data, and start the web server at:
👉 **`http://127.0.0.1:8000`**

### 3. Run Automated Integration Tests
```bash
python test_system.py
```

---

## 🔑 Demo Login Credentials

The application comes pre-seeded with sample accounts for instant evaluation:

| Role | Email | Password | Description |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@delivery.com` | `Admin@123` | Full access to zones, rate cards, order overrides, agent assignment, & audit logs |
| **Customer** | `customer@example.com` | `Customer@123` | Placed sample orders, test price calculator & reschedule failed delivery |
| **Agent** | `agent1@delivery.com` | `Agent@123` | Assigned to North Zone, test order status updates (`Picked Up`, `Delivered`, `Failed`) |

*(Quick 1-click login buttons are also available directly on the top header bar in the UI!)*

---

## 📂 Project Structure

```
├── app/
│   ├── config.py              # Environment configuration loader
│   ├── database.py            # SQLAlchemy session factory (SQLite / PostgreSQL)
│   ├── models.py              # DB Models: User, Zone, AreaMapping, RateCard, CODSurcharge, AgentProfile, Order, History, Notifications
│   ├── schemas.py             # Pydantic request & response schemas
│   ├── rate_engine.py         # Dynamic Rate Calculation Engine
│   ├── assignment_engine.py   # Intelligent Agent Auto-Assignment Algorithm
│   ├── notification_engine.py # Email / SMS notification dispatcher & logging
│   ├── seed.py                # Initial database seeder
│   ├── main.py                # FastAPI app initialization, routes, & middleware
│   └── routers/               # API Routers (auth, zones, rates, orders, agents)
├── templates/
│   └── index.html             # Responsive Single-Page Application (Tailwind CSS + Lucide Icons)
├── static/
│   ├── app.js                 # Reactive JavaScript frontend engine
│   └── style.css              # Custom status badges & timeline CSS
├── test_system.py             # Automated end-to-end unit and integration test suite
├── run.py                     # Local server launcher
├── SYSTEM_DESIGN.md           # 800-word System Design write-up
├── README.md                  # Comprehensive setup and API documentation
├── Procfile                   # Render / Railway deployment runner
├── render.yaml                # Render service definition
├── vercel.json                # Vercel deployment spec
└── Dockerfile                 # Containerized deployment spec
```

---

## 📊 Database Schema (ERD Overview)

```
+-------------------+       +-------------------+       +--------------------+
|       User        |       |       Zone        |       |    AreaMapping     |
+-------------------+       +-------------------+       +--------------------+
| id (PK)           |<-----\| id (PK)           |<-----\| id (PK)            |
| name              |       | name              |       | zone_id (FK)       |
| email (Unique)    |       | code (Unique)     |       | pincode            |
| password_hash     |       | description       |       | area_name          |
| role (ADMIN/...)  |       +-------------------+       +--------------------+
| phone             |                 ^
+-------------------+                 |
      ^       ^                       |
      |       |             +-------------------+
      |       +------------\|   AgentProfile    |
      |                     +-------------------+
      |                     | id (PK)           |
      |                     | user_id (FK)      |
      |                     | current_lat/lng   |
      |                     | active_zone_id(FK)|
      |                     | status/workload   |
      |                     +-------------------+
      |
+-----------------------------------------------+
|                    Order                      |
+-----------------------------------------------+
| id (PK)                                       |
| tracking_number (Unique)                      |
| customer_id (FK -> User)                      |
| agent_id (FK -> User)                         |
| pickup_address / pickup_pincode / zone_id(FK) |
| drop_address / drop_pincode / zone_id(FK)     |
| dimensions (length, width, height)            |
| actual_weight / volumetric_weight / billable  |
| order_type (B2B/B2C) / payment_type(COD/PRE)  |
| base_charge / weight_charge / cod_surcharge   |
| total_charge                                  |
| status (CREATED/ASSIGNED/DELIVERED/FAILED...) |
+-----------------------------------------------+
      |
      v
+-----------------------------------------------+
|             OrderTrackingHistory              |
+-----------------------------------------------+
| id (PK)                                       |
| order_id (FK -> Order)                        |
| status / actor_name / actor_role / notes      |
| location_lat / location_lng / timestamp       |
+-----------------------------------------------+
```

---

## 🧮 Rate Calculation Logic Explanation

1. **Volumetric Weight**:
   $$\text{Volumetric Weight (kg)} = \frac{\text{Length (cm)} \times \text{Width (cm)} \times \text{Height (cm)}}{5000}$$
2. **Billable Weight**:
   $$\text{Billable Weight} = \max(\text{Actual Weight}, \text{Volumetric Weight})$$
3. **Route Type**:
   - `INTRA-ZONE`: If `Pickup Zone ID == Drop Zone ID`.
   - `INTER-ZONE`: If `Pickup Zone ID != Drop Zone ID`.
4. **Freight Charge**:
   $$\text{Subtotal} = \max(\text{Base Rate} + \text{Billable Weight} \times \text{Per-Kg Rate}, \text{Min Charge})$$
5. **COD Surcharge**:
   $$\text{COD Fee} = \text{Fixed Fee} + \left(\text{Subtotal} \times \frac{\text{Percentage}}{100}\right) \quad \text{if COD else } 0$$
6. **Total Charge**:
   $$\text{Total Charge} = \text{Subtotal} + \text{COD Fee}$$

---

## 🌐 API Endpoint Summary

### Authentication (`/api/auth`)
- `POST /api/auth/register`: Register new account (Customer/Agent/Admin).
- `POST /api/auth/login`: Login & receive JWT access token.
- `GET /api/auth/me`: Get currently logged in user profile.

### Rate Calculation & Config (`/api/rates`)
- `POST /api/rates/calculate`: Public real-time price estimation endpoint.
- `GET /api/rates/cards`: List all active rate cards.
- `POST /api/rates/cards`: Create/update B2B or B2C rate cards (Admin).
- `GET /api/rates/cod`: List COD surcharges.
- `POST /api/rates/cod`: Create/update COD surcharges (Admin).

### Zone Management (`/api/zones`)
- `GET /api/zones`: List all zones with mapped pincodes/areas.
- `POST /api/zones`: Create new zone (Admin).
- `POST /api/zones/{zone_id}/areas`: Add pincode/area mapping (Admin).
- `DELETE /api/zones/areas/{area_id}`: Remove area mapping (Admin).

### Orders & Tracking (`/api/orders`)
- `POST /api/orders`: Place order with auto-pricing and auto-agent assignment.
- `GET /api/orders`: List orders with role access control & filters (`status`, `zone_id`, `agent_id`, `search`).
- `GET /api/orders/{id_or_tracking}`: Get detailed order status and full tracking history.
- `PUT /api/orders/{id}/status`: Update order status (Agent update: `Picked Up`, `In Transit`, `Out for Delivery`, `Delivered`, `Failed`).
- `POST /api/orders/{id}/reschedule`: Customer reschedules failed delivery for new date & auto-reassigns agent.
- `PUT /api/orders/{id}/override`: Admin manual status override.
- `GET /api/orders/notifications/logs`: View dispatched email and SMS notification logs (Admin).

### Delivery Agents (`/api/agents`)
- `GET /api/agents`: List agent roster with availability, zone, location, and workload.
- `PUT /api/agents/me`: Agent updates availability status and location coordinates.
- `POST /api/agents/assign-manual/{order_id}`: Admin manually assigns agent.
- `POST /api/agents/auto-assign/{order_id}`: Admin/System triggers auto-assignment.

---

## 🌐 Hosted Application URL & Deployment Guide

This application is ready for 1-click deployment on Render, Railway, or Vercel:

### Deploying on Render / Railway:
1. Push repository to GitHub.
2. Create a new **Web Service** on [Render](https://render.com) or [Railway](https://railway.app).
3. Connect repository. Render will automatically detect `render.yaml` or build command `pip install -r requirements.txt` and start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

### Deploying on Vercel:
1. Import repository on [Vercel](https://vercel.com).
2. Vercel automatically uses `vercel.json` and `@vercel/python` builder.

---

## 📄 System Design Write-Up
For the full 800-word System Design covering rate engine design, zone detection strategy, auto-assignment scoring formula, and failed delivery handling, refer to [`SYSTEM_DESIGN.md`](file:///c:/Users/khush/OneDrive/Desktop/Unthinkable%20Project/SYSTEM_DESIGN.md).
#   L a s t - M i l e - d e l i v e r y  
 